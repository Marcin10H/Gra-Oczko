import queue

import customtkinter as ctk

from client.network import NetworkClient
from gui.theme import (
    ACCENT_GLOW,
    BTN_DANGER,
    BTN_DANGER_HOVER,
    BTN_HOVER,
    BTN_PRIMARY,
    BTN_STAY,
    BTN_STAY_HOVER,
    CARD_BG,
    CARD_BORDER,
    GOLD,
    GOLD_SOFT,
    PANEL_BG,
    PANEL_BORDER,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    TABLE_GREEN,
    TEXT_DIM,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from server import GameServer
from utils.net_helpers import friendly_connect_error, get_local_ip, parse_address

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class OczkoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Oczko - Network Game")
        self.geometry("900x620")
        self.minsize(800, 560)

        self.game_server = None
        self.net = NetworkClient()
        self.phase = "menu"
        self.host_address_display = None
        self._leaving = False

        self._build_menu()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_network)

    def _build_menu(self):
        self._clear_root()
        self.phase = "menu"
        self.configure(fg_color=TABLE_GREEN)

        card = ctk.CTkFrame(
            self,
            fg_color=PANEL_BG,
            bg_color=TABLE_GREEN,
            corner_radius=RADIUS_LG,
            border_width=2,
            border_color=ACCENT_GLOW,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card,
            text="OCZKO",
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color=ACCENT_GLOW,
        ).pack(padx=48, pady=(40, 32))

        ctk.CTkButton(
            card,
            text="Create Game",
            width=240,
            height=48,
            corner_radius=RADIUS_MD,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_HOVER,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._create_game,
        ).pack(padx=40, pady=8)

        ctk.CTkButton(
            card,
            text="Join Game",
            width=240,
            height=48,
            corner_radius=RADIUS_MD,
            fg_color=BTN_STAY,
            hover_color=BTN_STAY_HOVER,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._show_join,
        ).pack(padx=40, pady=(8, 36))

    def _show_join(self):
        self._clear_root()
        self.phase = "join"
        self.configure(fg_color=TABLE_GREEN)

        card = ctk.CTkFrame(
            self,
            fg_color=PANEL_BG,
            bg_color=TABLE_GREEN,
            corner_radius=RADIUS_LG,
            border_width=2,
            border_color=PANEL_BORDER,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card,
            text="Join Game",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(padx=40, pady=(32, 12))
        ctk.CTkLabel(card, text="Host address (IP:PORT):", text_color=TEXT_MUTED).pack(
            padx=36
        )
        self.entry_ip = ctk.CTkEntry(
            card,
            width=240,
            height=40,
            corner_radius=RADIUS_SM,
            border_color=ACCENT_GLOW,
            placeholder_text="e.g. 192.168.1.5:54321",
        )
        self.entry_ip.pack(pady=12, padx=40)

        ctk.CTkButton(
            card,
            text="Connect",
            width=176,
            height=44,
            corner_radius=RADIUS_MD,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._join_game,
        ).pack(pady=8)

        ctk.CTkButton(
            card,
            text="Back",
            width=120,
            height=36,
            corner_radius=RADIUS_SM,
            fg_color="#3d4f5f",
            hover_color="#5a6d7d",
            command=self._build_menu,
        ).pack(pady=(4, 24))

        self.join_status = ctk.CTkLabel(card, text="", text_color=GOLD)
        self.join_status.pack(pady=(0, 28))

    def _create_game(self):
        self.game_server = GameServer()
        self.game_server.start()
        ip = get_local_ip()
        port = self.game_server.port
        address = f"{ip}:{port}"
        self.host_address_display = address
        self._connect_client("127.0.0.1", port, host_mode=True, display_address=address)

    def _join_game(self):
        raw = self.entry_ip.get().strip()
        ok, host, port, err = parse_address(raw)
        if not ok:
            self.join_status.configure(text=err)
            return
        self._connect_client(host, port, host_mode=False)

    def _connect_client(self, host, port, host_mode=False, display_address=None):
        self.net.disconnect()
        self._leaving = False
        try:
            self.net = NetworkClient()
            self.net.connect(host, port)
        except OSError as e:
            msg = friendly_connect_error(e)
            if host_mode and self.game_server:
                self.game_server.stop()
                self.game_server = None
                self.host_address_display = None
            if host_mode:
                self._build_menu()
                self._show_transient_error(msg)
            else:
                self._show_join()
                self.join_status.configure(text=msg)
            return

        self._build_lobby(host_mode, display_address)

    def _show_transient_error(self, text):
        if hasattr(self, "_error_label") and self._error_label.winfo_exists():
            self._error_label.destroy()
        self._error_label = ctk.CTkLabel(
            self,
            text=text,
            text_color=GOLD,
            wraplength=400,
            font=ctk.CTkFont(size=13),
        )
        self._error_label.place(relx=0.5, rely=0.92, anchor="s")

    def _build_lobby(self, host_mode, display_address=None):
        self._clear_root()
        self.phase = "lobby"
        self.configure(fg_color=TABLE_GREEN)

        card = ctk.CTkFrame(
            self,
            fg_color=PANEL_BG,
            bg_color=TABLE_GREEN,
            corner_radius=RADIUS_LG,
            border_width=2,
            border_color=ACCENT_GLOW,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        if host_mode and display_address:
            ctk.CTkLabel(
                card,
                text="Share this address with the other player:",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_MUTED,
            ).pack(padx=40, pady=(32, 4))
            ctk.CTkLabel(
                card,
                text=display_address,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=ACCENT_GLOW,
            ).pack(pady=(0, 16))

        self.lobby_label = ctk.CTkLabel(
            card,
            text="Waiting for the second player...",
            font=ctk.CTkFont(size=17),
            text_color=GOLD_SOFT,
        )
        self.lobby_label.pack(padx=48, pady=(16, 40))

    def _build_game_ui(self):
        self._clear_root()
        self.phase = "game"

        self.configure(fg_color=TABLE_GREEN)

        if self.host_address_display:
            ctk.CTkLabel(
                self,
                text=f"Host: {self.host_address_display}",
                font=ctk.CTkFont(size=12),
                text_color=TEXT_MUTED,
            ).place(x=20, y=12, anchor="nw")

        ctk.CTkButton(
            self,
            text="End Game",
            width=110,
            height=34,
            corner_radius=RADIUS_SM,
            fg_color=BTN_DANGER,
            hover_color=BTN_DANGER_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._leave_game,
        ).place(relx=1.0, x=-20, y=12, anchor="ne")

        self.opponent_frame = ctk.CTkFrame(
            self,
            width=360,
            height=52,
            fg_color=PANEL_BG,
            bg_color=TABLE_GREEN,
            corner_radius=RADIUS_MD,
            border_width=2,
            border_color=PANEL_BORDER,
        )
        self.opponent_frame.place(relx=0.5, y=28, anchor="n")
        self.lbl_opponent = ctk.CTkLabel(
            self.opponent_frame,
            text="Opponent: waiting...",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_PRIMARY,
        )
        self.lbl_opponent.pack(padx=20, pady=14)

        self.lbl_pot_center = ctk.CTkLabel(
            self,
            text="Coins in the game: 0",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=GOLD,
        )
        self.lbl_pot_center.place(relx=0.5, y=92, anchor="n")

        self.btn_hit = ctk.CTkButton(
            self,
            text="Hit",
            width=130,
            height=52,
            corner_radius=RADIUS_MD,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_HOVER,
            font=ctk.CTkFont(size=20, weight="bold"),
            command=self._on_hit,
        )
        self.btn_hit.place(relx=0.07, rely=0.5, anchor="w")

        self.btn_stay = ctk.CTkButton(
            self,
            text="Stay",
            width=130,
            height=52,
            corner_radius=RADIUS_MD,
            fg_color=BTN_STAY,
            hover_color=BTN_STAY_HOVER,
            font=ctk.CTkFont(size=20, weight="bold"),
            command=self._on_stay,
        )
        self.btn_stay.place(relx=0.93, rely=0.5, anchor="e")

        score_w, score_h = 500, 268
        self.game_square = ctk.CTkFrame(
            self,
            width=score_w,
            height=score_h,
            fg_color=CARD_BG,
            bg_color=TABLE_GREEN,
            corner_radius=RADIUS_LG,
            border_width=3,
            border_color=CARD_BORDER,
        )
        self.game_square.place(relx=0.5, rely=0.48, anchor="center")
        self.game_square.pack_propagate(False)

        score_inner = ctk.CTkFrame(
            self.game_square,
            fg_color=CARD_BG,
            bg_color=CARD_BG,
            corner_radius=0,
        )
        score_inner.pack(expand=True, fill="both", padx=28, pady=20)

        ctk.CTkLabel(
            score_inner,
            text="TOTAL SCORE",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT_GLOW,
            fg_color=CARD_BG,
        ).pack(fill="x", pady=(4, 0))

        self.lbl_sum = ctk.CTkLabel(
            score_inner,
            text="0",
            width=420,
            font=ctk.CTkFont(size=72, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=CARD_BG,
        )
        self.lbl_sum.pack(fill="x", pady=(4, 4))

        self.lbl_cards = ctk.CTkLabel(
            score_inner,
            text="Your cards: -",
            width=420,
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
            fg_color=CARD_BG,
        )
        self.lbl_cards.pack(fill="x", pady=(8, 0))

        self.lbl_last = ctk.CTkLabel(
            score_inner,
            text="Last card: -",
            width=420,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_DIM,
            fg_color=CARD_BG,
        )
        self.lbl_last.pack(fill="x", pady=(6, 4))

        econ = ctk.CTkFrame(
            self,
            fg_color=PANEL_BG,
            bg_color=TABLE_GREEN,
            corner_radius=RADIUS_MD,
            border_width=2,
            border_color=GOLD,
        )
        econ.place(x=24, rely=1.0, y=-24, anchor="sw")
        self.lbl_coins = ctk.CTkLabel(
            econ,
            text="Your coins: 1000",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=GOLD,
            anchor="w",
        )
        self.lbl_coins.pack(padx=20, pady=(14, 4))
        self.lbl_pot = ctk.CTkLabel(
            econ,
            text="Coins in the game: 0",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.lbl_pot.pack(padx=20, pady=(0, 14))

        self.lbl_status = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
            wraplength=520,
        )
        self.lbl_status.place(relx=0.5, rely=0.79, anchor="n")

        self.bet_frame = ctk.CTkFrame(
            self.game_square,
            width=248,
            height=198,
            fg_color=PANEL_BG,
            bg_color=CARD_BG,
            corner_radius=RADIUS_LG,
            border_width=2,
            border_color=GOLD,
        )
        self.bet_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.bet_frame.pack_propagate(False)
        ctk.CTkLabel(
            self.bet_frame,
            text="Place your bet",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=GOLD,
            fg_color=PANEL_BG,
        ).pack(padx=24, pady=(20, 10))
        self.entry_bet = ctk.CTkEntry(
            self.bet_frame,
            width=148,
            height=40,
            corner_radius=RADIUS_SM,
            border_color=ACCENT_GLOW,
            placeholder_text="Amount",
        )
        self.entry_bet.pack(pady=6)
        self.btn_bet = ctk.CTkButton(
            self.bet_frame,
            text="Bet",
            width=132,
            height=40,
            corner_radius=RADIUS_MD,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_HOVER,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_bet,
        )
        self.btn_bet.pack(pady=(10, 18))
        self.bet_frame.place_forget()

        self._set_game_controls_enabled(False, hit_ok=False)
        self.bet_placed = False

    def _clear_root(self):
        for w in self.winfo_children():
            w.destroy()

    def _set_game_controls_enabled(self, can_play: bool, hit_ok: bool = True):
        hit_state = "normal" if can_play and hit_ok else "disabled"
        stay_state = "normal" if can_play else "disabled"
        self.btn_hit.configure(state=hit_state)
        self.btn_stay.configure(state=stay_state)

    def _on_bet(self):
        raw = self.entry_bet.get().strip()
        try:
            kwota = int(raw)
        except ValueError:
            self.lbl_status.configure(text="Enter a valid bet amount.")
            return
        self.net.send({"akcja": "bet", "kwota": kwota})

    def _on_hit(self):
        self.net.send({"akcja": "dobierz"})

    def _on_stay(self):
        self.net.send({"akcja": "zostan"})

    def _leave_game(self):
        self._leaving = True  # inaczej wyskakuje connection lost
        if self.net.sock:
            try:
                self.net.send({"akcja": "wyjdz"})
            except OSError:
                pass
        self.after(250, self._return_to_menu)

    def _return_to_menu(self):
        self._leaving = True
        self.net.disconnect()
        if self.game_server:
            self.game_server.stop()
            self.game_server = None
        self.host_address_display = None
        self.bet_placed = False
        self._leaving = False
        self._build_menu()

    def _poll_network(self):
        # recv jest w innym watku, tu tylko odbieramy z kolejki
        try:
            while True:
                msg = self.net.incoming.get_nowait()
                try:
                    self._handle_message(msg)
                except Exception as exc:
                    print(f"Message handling error {msg}: {exc}")
        except queue.Empty:
            pass
        self.after(100, self._poll_network)

    def _ensure_game_screen(self):
        if self.phase != "game" or not hasattr(self, "bet_frame"):
            self._build_game_ui()

    def _handle_message(self, msg):
        typ = msg.get("typ")

        if typ == "polaczono":
            coins = msg.get("coins", 1000)
            self._ensure_game_screen()
            self._update_coins(coins, msg.get("pot", 0))

        elif typ == "czeka_na_gracza":
            if self.phase == "lobby" and hasattr(self, "lobby_label") and self.lobby_label.winfo_exists():
                self.lobby_label.configure(text="Waiting for the second player...")
            elif self.phase == "game" and hasattr(self, "lbl_status"):
                self.lbl_status.configure(text="Waiting for the second player...")

        elif typ == "faza" and msg.get("faza") == "betting":
            self.after(0, lambda m=dict(msg): self._on_betting_phase(m))

        elif typ == "zaklad_przyjety":
            self.bet_placed = True
            self.bet_frame.place_forget()
            self._update_coins(msg.get("coins", 0), msg.get("pot", 0))
            self.lbl_status.configure(text="Bet placed. Waiting for opponent...")

        elif typ == "czeka_na_zaklad":
            self.lbl_status.configure(text="Waiting for opponent to place a bet...")

        elif typ == "stan":
            self._hide_betting()
            self._apply_play_state(msg)

        elif typ == "przeciwnik_status":
            if hasattr(self, "lbl_opponent"):
                self.lbl_opponent.configure(text=msg.get("status", "Opponent thinks..."))

        elif typ == "koniec_rundy":
            self._show_round_end(msg)

        elif typ == "nastepna_runda":
            self.lbl_status.configure(
                text=msg.get("info", "Next round - place your bet.")
            )

        elif typ == "przeciwnik_wyszedl":
            self.after(0, lambda m=dict(msg): self._on_opponent_left(m))

        elif typ == "rozlaczono":
            if not self._leaving:
                self.after(0, self._on_connection_lost)

        elif typ == "koniec_sesji":
            self.after(0, lambda m=dict(msg): self._on_session_end(m))

        elif typ == "blad":
            self.lbl_status.configure(text=msg.get("msg", "Error"))

    def _on_betting_phase(self, msg=None):
        msg = msg or {}
        self._ensure_game_screen()
        pot = msg.get("pot", 0)
        if pot == 0:
            self.bet_placed = False
        if "coins" in msg:
            self._update_coins(msg["coins"], msg.get("pot", 0))
            if msg["coins"] <= 0:
                self.lbl_status.configure(
                    text="Out of coins. Click End Game to return to the menu."
                )
                self.bet_frame.place_forget()
                return
        if not self.bet_placed:
            self._show_betting()
        info = msg.get("info")
        if info:
            self.lbl_status.configure(text=info)

    def _on_opponent_left(self, msg=None):
        msg = msg or {}
        self._leaving = True
        if hasattr(self, "lbl_status"):
            self.lbl_status.configure(
                text=msg.get("msg", "Opponent left the game. Returning to menu...")
            )
        if hasattr(self, "lbl_opponent"):
            self.lbl_opponent.configure(text="Opponent disconnected")
        self.after(400, self._return_to_menu)

    def _on_connection_lost(self):
        if self._leaving:
            return
        self._leaving = True
        if self.phase in ("game", "lobby") and hasattr(self, "lbl_status"):
            self.lbl_status.configure(
                text="Connection lost. The other player may have left. Returning to menu..."
            )
            if hasattr(self, "lbl_opponent"):
                self.lbl_opponent.configure(text="Disconnected")
        self.after(400, self._return_to_menu)

    def _on_session_end(self, msg):
        self._set_game_controls_enabled(False, hit_ok=False)
        self.bet_frame.place_forget()
        self._update_coins(msg.get("coins", 0), 0)
        self.lbl_status.configure(
            text=msg.get("msg", "Session over - not enough coins to play.")
        )

    def _show_betting(self):
        if not hasattr(self, "bet_frame"):
            return
        self.bet_placed = False
        self.bet_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.bet_frame.lift()
        self.entry_bet.delete(0, "end")
        self.btn_bet.configure(state="normal")
        self.lbl_sum.configure(text="-")
        self.lbl_cards.configure(text="Your cards: -")
        self.lbl_last.configure(text="Last card: -")
        self.lbl_opponent.configure(text="Opponent: placing bet...")
        self._set_game_controls_enabled(False, hit_ok=False)
        self.lbl_status.configure(
            text="Place your bet. You start with 1 card - draw more with Hit."
        )

    def _hide_betting(self):
        self.bet_frame.place_forget()

    def _apply_play_state(self, msg):
        suma = msg.get("suma", 0)
        ostatnia = msg.get("ostatnia")
        karty = msg.get("karty", [])
        self.lbl_sum.configure(text=str(suma))
        if karty:
            self.lbl_cards.configure(text=f"Your cards: {', '.join(str(k) for k in karty)}")
        if ostatnia is not None:
            self.lbl_last.configure(text=f"Last card: {ostatnia}")
        self._update_coins(msg.get("coins", 0), msg.get("pot", 0))

        can_play = msg.get("kolej", False)
        finished = msg.get("finished", not can_play)
        hit_disabled = msg.get("hit_disabled", suma >= 18)
        self._set_game_controls_enabled(can_play, hit_ok=not hit_disabled)

        if can_play:
            self.lbl_status.configure(text="Hit or Stay - both players play at the same time.")
            self.lbl_opponent.configure(text="Opponent is playing...")
        elif finished:
            self.lbl_status.configure(text="You are done - waiting for opponent to finish...")
        else:
            self.lbl_status.configure(text="Waiting for opponent...")

    def _show_round_end(self, msg):
        self._set_game_controls_enabled(False, hit_ok=False)
        wynik = msg.get("wynik", "tie")
        s_moja = msg.get("suma", 0)
        s_opp = msg.get("suma_przeciwnika", 0)
        karty = msg.get("karty", [])
        karty_opp = msg.get("karty_przeciwnika", [])
        self.lbl_sum.configure(text=str(s_moja))
        if karty:
            self.lbl_cards.configure(text=f"Your cards: {', '.join(str(k) for k in karty)}")
        self.lbl_last.configure(
            text=f"Opponent - cards: {', '.join(str(k) for k in karty_opp) if karty_opp else '?'}, total: {s_opp}"
        )

        if wynik == "win":
            txt = f"You win! Your total: {s_moja}, opponent: {s_opp}."
        elif wynik == "lose":
            txt = f"You lose. Your total: {s_moja}, opponent: {s_opp}."
        else:
            txt = f"Tie! Both totals: {s_moja} / {s_opp}. Bets returned."

        self.lbl_opponent.configure(text=f"Opponent final score: {s_opp}")
        self._update_coins(msg.get("coins", 0), 0)
        self.bet_placed = False
        self.lbl_status.configure(
            text=f"{txt}  |  Coins: {msg.get('coins', 0)}  →  Next round starting soon."
        )

    def _update_coins(self, coins, pot):
        if not hasattr(self, "lbl_coins"):
            return
        self.lbl_coins.configure(text=f"Your coins: {coins}")
        self.lbl_pot.configure(text=f"Coins in the game: {pot}")
        self.lbl_pot_center.configure(text=f"Coins in the game: {pot}")

    def _on_close(self):
        if self.net.sock and self.phase in ("game", "lobby"):
            try:
                self.net.send({"akcja": "wyjdz"})
            except OSError:
                pass
        self.net.disconnect()
        if self.game_server:
            self.game_server.stop()
        self.destroy()
