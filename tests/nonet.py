"""No-network guard. Import and call install() at the top of a test: any attempt to open a
socket or look up a host from then on raises, so the test fails."""
import socket


class NetworkAttempt(AssertionError):
    pass


def _blocked(*args, **kwargs):
    raise NetworkAttempt("an importer tried to use the network")


def install():
    socket.socket = _blocked
    socket.create_connection = _blocked
    socket.getaddrinfo = _blocked
    socket.gethostbyname = _blocked
