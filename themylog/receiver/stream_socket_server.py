from __future__ import absolute_import

import logging
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

    def __init__(self, format, server_factory, server_address):
        self.format = format
        try:
            self.parse = {
                "json": lambda address, text: parse_json(text),
                "text": lambda address, text: parse_plaintext(text, default_application=address, default_logger="root"),
            }[self.format]
        except KeyError:
            raise Exception("Unknown format: '%s'" % format)

        self.server = server_factory(server_address, StreamSocketServerHandler)
        self.server.queue = Queue()

        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def receive(self):
        while True:
            address, text = self.server.queue.get()

            try:
                yield self.parse(address, text)
            except (TypeError, ValueError):
                logging.exception("Unable to parse following message from %r: %s", address, text)


class TCPServer(StreamSocketServer):
    def __init__(self, host, port, format="json"):
        super(TCPServer, self).__init__(format, SocketServer.ThreadingTCPServer, (host, port))


if hasattr(SocketServer, "ThreadingUnixStreamServer"):
    class UnixServer(StreamSocketServer):
        def __init__(self, path, format="json"):
            if os.path.exists(path):
                os.unlink(path)

            super(UnixServer, self).__init__(format, SocketServer.ThreadingUnixStreamServer, path)
