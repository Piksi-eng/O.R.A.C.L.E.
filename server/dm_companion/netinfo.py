import socket


def lan_ip() -> str:
    """The address phones on the same Wi-Fi use to reach this PC.

    Connecting a UDP socket sends no packets; it only makes the OS pick the outgoing interface.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
