import json
import queue
import socket
import threading

from config import CONNECT_TIMEOUT


class NetworkClient:
    def __init__(self):
        self.sock = None
        self.incoming = queue.Queue()
        self._connected = False

    def connect(self, host, port, timeout=CONNECT_TIMEOUT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self.sock.settimeout(None)
        self._connected = True
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def disconnect(self):
        was_connected = self._connected
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        if was_connected:
            self.incoming.put({"typ": "rozlaczono"})

    def send(self, msg: dict):
        if not self.sock:
            return
        line = json.dumps(msg, ensure_ascii=False) + "\n"
        try:
            self.sock.sendall(line.encode("utf-8"))
        except OSError:
            pass

    def _recv_loop(self):
        buf = b""
        while self._connected and self.sock:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    self.incoming.put(json.loads(line.decode("utf-8")))
                except json.JSONDecodeError:
                    pass
        if self._connected:
            self._connected = False
            self.incoming.put({"typ": "rozlaczono"})
