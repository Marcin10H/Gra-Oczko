import socket


def get_local_ip():
    # zeby wyciagnac swoje IP w sieci lokalnej
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def parse_address(text: str) -> tuple[bool, str | None, int | None, str]:
    text = text.strip()
    if not text:
        return False, None, None, "Enter address as IP:PORT."
    if ":" not in text:
        return False, None, None, "Use format IP:PORT (e.g. 192.168.1.5:54321)."
    host, port_str = text.rsplit(":", 1)
    host = host.strip()
    port_str = port_str.strip()
    if not host or not port_str:
        return False, None, None, "Use format IP:PORT (e.g. 192.168.1.5:54321)."
    try:
        port = int(port_str)
    except ValueError:
        return False, None, None, "Port must be a number."
    if port < 1 or port > 65535:
        return False, None, None, "Port must be between 1 and 65535."
    if host.lower() == "localhost":
        return True, host, port, ""
    try:
        socket.inet_aton(host)
    except OSError:
        return False, None, None, "Invalid IP address."
    return True, host, port, ""


def friendly_connect_error(exc: OSError) -> str:
    err = exc.errno
    if err in (11001, -2, -5):
        return "Invalid host. Check the address and try again."
    if err in (10061, 111):
        return "Could not connect. Is the host game running? Check IP:PORT and try again."
    if err in (10060, 110, 113):
        return "Connection timed out. Check the IP:PORT and network, then try again."
    return "Could not connect. Check the IP:PORT and try again."
