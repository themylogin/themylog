from __future__ import absolute_import

import os
from Queue import Queue
import SocketServer
from threading import Thread
from zope.interface import implements

from themylog.receiver.interface import IReceiver
from themylog.record.parser import parse_json, parse_plaintext

__all__ = ["TCPServer"]
if hasattr(SocketServer, "UnixStreamServer"):
    __all__.extend(["UnixServer"])


class StreamSocketServerHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        address = self.client_address
        if isinstance(address, tuple):
            address = address[0]

        recv = ""
        while True:
            data = self.request.recv(1024)
            if not data:
                break

            recv += data

        self.server.queue.put((address, recv))


class StreamSocketServer(object):
    implements(IReceiver)

    def __init__(self, server_factory, server_address):
        self.server = server_factory(server_address, StreamSocketServerHandler)
        self.server.queue = Queue()

        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def receive(self):
        while True:
            address, text = self.server.queue.get()
            try:
                yield parse_json(text)
            except (TypeError, ValueError):
                yield parse_plaintext(text, default_source=address)


class TCPServer(StreamSocketServer):
    def __init__(self, host, port):
        super(TCPServer, self).__init__(SocketServer.ThreadingTCPServer, (host, port))


if hasattr(SocketServer, "ThreadingUnixStreamServer"):
    class UnixServer(StreamSocketServer):
        def __init__(self, path):
            if os.path.exists(path):
                os.unlink(path)

            super(UnixServer, self).__init__(SocketServer.ThreadingUnixStreamServer, path)
