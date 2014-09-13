# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import requests
import threading
import websocket

import themyutils.json

from .. import IntegrationTestCase


class WebserverTestCase(IntegrationTestCase):
    config = {"web_server": {"host": "127.0.0.1",
                             "port": 46406}}

    def assertRequest(self, request, result):
        r = requests.get("http://%s:%s%s" % (self.config["web_server"]["host"], self.config["web_server"]["port"],
                                             request))
        self.assertEqual(r.json(), result)

    def websocketReader(self, request):
        result = []

        def reader():
            ws = websocket.create_connection("ws://%s:%s%s" % (self.config["web_server"]["host"],
                                                               self.config["web_server"]["port"],
                                                               request))
            while True:
                try:
                    result.append(themyutils.json.loads(ws.recv()))
                except Exception as e:
                    result.append(e)
                    break

        thread = threading.Thread(target=reader)
        thread.daemon = True
        thread.start()

        return result
