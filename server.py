# serwer - logika gry, TCP, JSON

import json
import random
import socket
import threading

# pula kart z zadania (4x dziesiatka)
CARD_POOL = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
STARTING_COINS = 1000
ROUND_RESULT_DELAY = 4.0


class GameServer:
    def __init__(self, port=0):
        self.port = port
        self._lock = threading.RLock()  # timer tez uzywa locka
        self._running = False
        self._server_sock = None
        self._thread = None

        self.clients = {}
        self.coins = [STARTING_COINS, STARTING_COINS]
        self.bets = [None, None]
        self.pot = 0
        self.hands = [[], []]
        self.sums = [0, 0]
        self.last_drawn = [None, None]
        self.stayed = [False, False]
        self.busted = [False, False]
        self.phase = "waiting"
        self._round_timer = None

    def start(self):
        # bind tutaj zeby od razu znac port (host go pokazuje)
        if self._running:
            return
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("0.0.0.0", self.port))
        self.port = self._server_sock.getsockname()[1]
        self._server_sock.listen(2)
        self._server_sock.settimeout(1.0)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._cancel_round_timer()
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
        for sock in list(self.clients.values()):
            try:
                sock.close()
            except OSError:
                pass
        self.clients.clear()

    def _accept_loop(self):
        while self._running:
            try:
                conn, _addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=self._handle_client,
                args=(conn,),
                daemon=True,
            ).start()

    def _handle_client(self, conn):
        player_id = None
        try:
            with self._lock:
                if len(self.clients) >= 2:
                    self._send(conn, {"typ": "blad", "msg": "Server is full."})
                    conn.close()
                    return
                player_id = len(self.clients)
                self.clients[player_id] = conn

            self._send(
                conn,
                {
                    "typ": "polaczono",
                    "gracz": player_id + 1,
                    "coins": self.coins[player_id],
                },
            )

            with self._lock:
                count = len(self.clients)
            if count == 1:
                self._send(conn, {"typ": "czeka_na_gracza"})
            elif count == 2:
                self._begin_betting_phase()

            while self._running:
                data = self._recv_line(conn)
                if data is None:
                    break
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    self._send(conn, {"typ": "blad", "msg": "Invalid JSON."})
                    continue
                with self._lock:
                    self._process_message(player_id, msg)

        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            if player_id is not None:
                self._remove_client(player_id, notify_opponent=True)
            try:
                conn.close()
            except OSError:
                pass

    def _process_message(self, player_id, msg):
        action = msg.get("akcja")
        if action == "bet":
            self._handle_bet(player_id, msg.get("kwota"))
        elif action == "dobierz":
            self._handle_hit(player_id)
        elif action == "zostan":
            self._handle_stay(player_id)
        elif action == "wyjdz":
            self._handle_quit(player_id)
        else:
            self._send_to(player_id, {"typ": "blad", "msg": "Unknown action."})

    def _begin_betting_phase(self):
        with self._lock:
            self.phase = "betting"
            self.bets = [None, None]
            self.pot = 0
            for pid in list(self.clients.keys()):
                self._send_to(
                    pid,
                    {
                        "typ": "nastepna_runda",
                        "info": "Next round - place your bet.",
                    },
                )
                self._send_to(
                    pid,
                    {
                        "typ": "faza",
                        "faza": "betting",
                        "pot": 0,
                        "coins": self.coins[pid],
                    },
                )

    def _handle_bet(self, player_id, amount):
        if self.phase != "betting":
            self._send_to(player_id, {"typ": "blad", "msg": "You cannot bet right now."})
            return
        if self.bets[player_id] is not None:
            self._send_to(player_id, {"typ": "blad", "msg": "You already placed a bet."})
            return
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            self._send_to(player_id, {"typ": "blad", "msg": "Invalid bet amount."})
            return
        if amount <= 0:
            self._send_to(player_id, {"typ": "blad", "msg": "Bet must be greater than 0."})
            return
        if amount > self.coins[player_id]:
            self._send_to(
                player_id,
                {"typ": "blad", "msg": "Not enough coins."},
            )
            return

        self.bets[player_id] = amount
        self.coins[player_id] -= amount
        self.pot += amount

        self._send_to(
            player_id,
            {
                "typ": "zaklad_przyjety",
                "coins": self.coins[player_id],
                "pot": self.pot,
            },
        )
        other = 1 - player_id
        if self.bets[other] is None:
            self._send_to(player_id, {"typ": "czeka_na_zaklad"})
            self._send_to(
                other,
                {
                    "typ": "faza",
                    "faza": "betting",
                    "pot": self.pot,
                    "coins": self.coins[other],
                    "info": "Opponent placed a bet - your turn to bet.",
                },
            )
        else:
            self._start_playing_phase()

    def _start_playing_phase(self):
        # 1 karta na start
        self.phase = "playing"
        self.hands = [[], []]
        self.sums = [0, 0]
        self.last_drawn = [None, None]
        self.stayed = [False, False]
        self.busted = [False, False]

        for pid in (0, 1):
            card = self._draw_card()
            self.hands[pid].append(card)
            self.sums[pid] = sum(self.hands[pid])
            self.last_drawn[pid] = self.hands[pid][-1]

        self._broadcast_state()

    def _draw_card(self):
        return random.choice(CARD_POOL)

    def _handle_hit(self, player_id):
        if self.phase != "playing":
            self._send_to(player_id, {"typ": "blad", "msg": "The round is not in progress."})
            return
        if self._player_finished(player_id):
            self._send_to(player_id, {"typ": "blad", "msg": "You already finished this round."})
            return
        if self.sums[player_id] >= 18:
            self._send_to(
                player_id,
                {"typ": "blad", "msg": "You have 18+ points - Stay only."},
            )
            return

        card = self._draw_card()
        self.hands[player_id].append(card)
        self.last_drawn[player_id] = card
        self.sums[player_id] = sum(self.hands[player_id])

        if self.sums[player_id] > 21:
            self.busted[player_id] = True

        other = 1 - player_id
        self._send_to(other, {"typ": "przeciwnik_status", "status": "Opponent hit"})

        if self._both_finished():
            self._resolve_round()
        else:
            self._broadcast_state()

    def _handle_stay(self, player_id):
        if self.phase != "playing":
            self._send_to(player_id, {"typ": "blad", "msg": "The round is not in progress."})
            return
        if self._player_finished(player_id):
            self._send_to(player_id, {"typ": "blad", "msg": "You already finished this round."})
            return

        self.stayed[player_id] = True
        other = 1 - player_id
        self._send_to(other, {"typ": "przeciwnik_status", "status": "Opponent stayed"})

        if self._both_finished():
            self._resolve_round()
        else:
            self._broadcast_state()

    def _player_finished(self, pid):
        return self.stayed[pid] or self.busted[pid]

    def _both_finished(self):
        return self._player_finished(0) and self._player_finished(1)

    def _resolve_round(self):
        self.phase = "round_end"
        s0, s1 = self.sums[0], self.sums[1]

        def score_valid(pid):
            return not self.busted[pid]

        winner = None
        if score_valid(0) and score_valid(1):
            if s0 > s1:
                winner = 0
            elif s1 > s0:
                winner = 1
        elif score_valid(0):
            winner = 0
        elif score_valid(1):
            winner = 1

        if winner is None:
            self.coins[0] += self.bets[0] or 0
            self.coins[1] += self.bets[1] or 0
            wynik = ["tie", "tie"]
        else:
            self.coins[winner] += self.pot
            wynik = ["win", "lose"] if winner == 0 else ["lose", "win"]

        self.pot = 0

        for pid in (0, 1):
            opp = 1 - pid
            self._send_to(
                pid,
                {
                    "typ": "koniec_rundy",
                    "wynik": wynik[pid],
                    "suma": s0 if pid == 0 else s1,
                    "suma_przeciwnika": s1 if pid == 0 else s0,
                    "karty": list(self.hands[pid]),
                    "karty_przeciwnika": list(self.hands[opp]),
                    "coins": self.coins[pid],
                },
            )

        self._schedule_next_round()

    def _cancel_round_timer(self):
        if self._round_timer is not None:
            self._round_timer.cancel()
            self._round_timer = None

    def _schedule_next_round(self):
        self._cancel_round_timer()
        self._round_timer = threading.Timer(ROUND_RESULT_DELAY, self._auto_next_round)
        self._round_timer.daemon = True
        self._round_timer.start()

    def _auto_next_round(self):
        # bez tego byl deadlock z timerem
        start_betting = False
        with self._lock:
            if self.phase != "round_end" or len(self.clients) < 2:
                return
            if self.coins[0] <= 0 or self.coins[1] <= 0:
                for pid in list(self.clients.keys()):
                    if self.coins[pid] <= 0:
                        txt = "You are out of coins. Session over."
                    else:
                        txt = "Opponent is out of coins. Session over."
                    self._send_to(
                        pid,
                        {
                            "typ": "koniec_sesji",
                            "msg": txt,
                            "coins": self.coins[pid],
                        },
                    )
                return
            self.bets = [None, None]
            start_betting = True
        if start_betting:
            self._begin_betting_phase()

    def _handle_quit(self, player_id):
        self._cancel_round_timer()
        self._remove_client(
            player_id,
            notify_opponent=True,
            message="Opponent left the game.",
        )

    def _remove_client(self, player_id, notify_opponent=False, message=None):
        other_sock = None
        with self._lock:
            if player_id not in self.clients:
                return
            other = 1 - player_id
            self.clients.pop(player_id, None)
            if notify_opponent and other in self.clients:
                other_sock = self.clients[other]
        if other_sock is not None:
            self._send(
                other_sock,
                {
                    "typ": "przeciwnik_wyszedl",
                    "msg": message or "Opponent left the game.",
                },
            )

    def _state_for(self, player_id):
        return {
            "typ": "stan",
            "suma": self.sums[player_id],
            "ostatnia": self.last_drawn[player_id],
            "karty": list(self.hands[player_id]),
            "coins": self.coins[player_id],
            "pot": self.pot,
            "kolej": self.phase == "playing" and not self._player_finished(player_id),
            "finished": self._player_finished(player_id),
            "hit_disabled": self.sums[player_id] >= 18,
        }

    def _broadcast_state(self):
        for pid in self.clients:
            self._send_to(pid, self._state_for(pid))

    def _send_to(self, player_id, msg):
        sock = self.clients.get(player_id)
        if sock:
            self._send(sock, msg)

    @staticmethod
    def _send(sock, msg):
        try:
            line = json.dumps(msg, ensure_ascii=False) + "\n"
            sock.sendall(line.encode("utf-8"))
        except OSError:
            pass

    @staticmethod
    def _recv_line(sock):
        buf = b""
        while True:
            try:
                chunk = sock.recv(1)
            except OSError:
                return None
            if not chunk:
                return None if not buf else buf.decode("utf-8")
            if chunk == b"\n":
                return buf.decode("utf-8")
            buf += chunk
            if len(buf) > 65536:
                return None
