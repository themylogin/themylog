# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import os
from Queue import Queue
import SocketServer
import time
from zope.interface import implements

from themyutils.threading import start_daemon_thread

from themylog.receiver.interface import IReceiver
from themylog.record.parser import parse_json, parse_plaintext

__all__ = [b"TCPServer", b"UDPServer"]
if hasattr(SocketServer, b"UnixStreamServer"):
    __all__.extend([b"UnixServer"])

logger = logging.getLogger(__name__)


class StreamSocketServerHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        address = self.client_address
        if isinstance(address, tuple):
            address = address[0]

        request = self.request
        if isinstance(request, tuple):
            recv = request[0]
        else:
            recv = b""
            while True:
                data = request.recv(1024)
                if not data:
                    break

                recv += data

        self.server.queue.put((address, recv))


class StreamSocketServer(object):
    implements(IReceiver)

    def __init__(self, format, server_factory, server_address):
        self.logger = logger.getChild("%r" % (server_address,))

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

        start_daemon_thread(self.server.serve_forever)

    def receive(self):
        while True:
            address, text = self.server.queue.get()

            try:
                yield self.parse(address, text)
            except (TypeError, ValueError):
                self.logger.exception("Unable to parse following message from %r: %s", address, text)


class TCPServer(StreamSocketServer):
    def __init__(self, host, port, format="json"):
        super(TCPServer, self).__init__(format, SocketServer.ThreadingTCPServer, (host, port))


class UDPServer(StreamSocketServer):
    def __init__(self, host, port, format="json"):
        super(UDPServer, self).__init__(format, SocketServer.ThreadingUDPServer, (host, port))


if hasattr(SocketServer, b"ThreadingUnixStreamServer"):
    class UnixServer(StreamSocketServer):
        def __init__(self, path, fallback=None, format="json"):
            if os.path.exists(path):
                os.unlink(path)

            if fallback:
                start_daemon_thread(self.run_fallback_thread, fallback)

            super(UnixServer, self).__init__(format, SocketServer.ThreadingUnixStreamServer, path)

        def run_fallback_thread(self, fallback):
            while True:
                for message_file in os.listdir(fallback):
                    path = os.path.join(fallback, message_file)
                    if os.path.getmtime(path) < time.time() - 1:
                        self.server.queue.put(("", open(path, "r").read()))
                        os.unlink(path)

                time.sleep(1)
