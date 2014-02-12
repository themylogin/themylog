# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import operator
from Queue import Queue
from threading import Thread
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from zope.interface import implements

import themyutils.json

from themylog.handler.interface import IHandler, IRetrieveCapable
from themylog.record.serializer import serialize_json
from themylog.rules_tree import match_record


def setup_web_server(configuration, handlers, feeds):
    for handler in handlers:
        if IRetrieveCapable.providedBy(handler):
            retriever = handler
            break
    else:
        raise Exception("You should have at least one handler that is IRetrieveCapable to use web server")

    web_application = WebApplication(configuration, retriever, feeds)

    thread = Thread(target=web_application.serve_forever)
    thread.daemon = True
    thread.start()

    handlers.append(web_application)


class WebApplication(object):
    implements(IHandler)

    def __init__(self, configuration, retriever, feeds):
        self.configuration = configuration
        self.retriever = retriever
        self.feeds = feeds

        self.url_map = Map([
            Rule("/", endpoint="feed"),
            Rule("/feed/<name>", endpoint="feed"),
            Rule("/timeline/<application>", endpoint="timeline"),
            Rule("/timeline/<application>/<logger>", endpoint="timeline"),
            Rule("/timeseries/<application>", endpoint="timeseries"),
            Rule("/timeseries/<application>/<logger>", endpoint="timeseries"),
            Rule("/timeseries/<application>/<logger>/<msg>", endpoint="timeseries"),
        ])

        self.gevent = None
        self.async = None

        self.queues = set()

    def serve_forever(self):
        import gevent
        from geventwebsocket.handler import WebSocketHandler

        self.gevent = gevent
        self.async = gevent.get_hub().loop.async()

        return gevent.pywsgi.WSGIServer((self.configuration["host"], self.configuration["port"]),
                                        self.wsgi_app, handler_class=WebSocketHandler).serve_forever()

    def handle(self, record):
        for queue in self.queues:
            queue.put(record)

        if self.async:
            self.async.send()

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        response.headers.add(b"Access-Control-Allow-Origin", "*")
        return response(environ, start_response)

    def dispatch_request(self, request):
        endpoint, values = self.url_map.bind_to_environ(request.environ).match()
        return getattr(self, "execute_%s" % endpoint)(request, **values)

    def execute_feed(self, request, name=None):
        if name in self.feeds:
            feed = self.feeds[name]
        else:
            feed = None

        if feed:
            rules_tree = feed.rules_tree
        else:
            rules_tree = None

        limit = request.args.get("limit", 50, int)

        if "wsgi.websocket" in request.environ:
            queue = Queue()
            self.queues.add(queue)

            try:
                ws = request.environ["wsgi.websocket"]

                records = self.retriever.retrieve(rules_tree, limit)

                for record in reversed(records):
                    ws.send(serialize_json(record))

                while True:
                    self.gevent.get_hub().wait(self.async)

                    while not queue.empty():
                        record = queue.get()
                        if feed is None or feed.contains(record):
                            ws.send(serialize_json(record))
            finally:
                self.queues.remove(queue)
        else:
            records = self.retriever.retrieve(rules_tree, limit)
            return Response("[" + ",".join(map(serialize_json, records)) + "]", mimetype="application/json")

    def execute_timeline(self, request, application, logger=None):
        rules_tree = (operator.eq, lambda k: k("application"), application)

        if logger is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("logger"), logger))

        limit = request.args.get("limit", 1, int)

        if "wsgi.websocket" in request.environ:
            queue = Queue()
            self.queues.add(queue)

            try:
                ws = request.environ["wsgi.websocket"]

                records = self.retriever.retrieve(rules_tree, limit)

                for record in reversed(records):
                    ws.send(themyutils.json.dumps(record.args))

                while True:
                    self.gevent.get_hub().wait(self.async)

                    while not queue.empty():
                        record = queue.get()
                        if match_record(rules_tree, record):
                            ws.send(themyutils.json.dumps(records.args))
            finally:
                self.queues.remove(queue)
        else:
            records = self.retriever.retrieve(rules_tree, limit)
            return Response(themyutils.json.dumps([record.args for record in records]), mimetype="application/json")

    def execute_timeseries(self, request, application, logger=None, msg=None):
        rules_tree = (operator.eq, lambda k: k("application"), application)

        if logger is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("logger"), logger))

        if msg is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("msg"), msg))

        if "wsgi.websocket" in request.environ:
            queue = Queue()
            self.queues.add(queue)

            try:
                ws = request.environ["wsgi.websocket"]

                records = self.retriever.retrieve(rules_tree, 1)

                if records:
                    ws.send(themyutils.json.dumps(records[0].args))

                while True:
                    self.gevent.get_hub().wait(self.async)

                    while not queue.empty():
                        record = queue.get()
                        if match_record(rules_tree, record):
                            ws.send(themyutils.json.dumps(records.args))
            finally:
                self.queues.remove(queue)
        else:
            records = self.retriever.retrieve(rules_tree, 1)
            return Response(themyutils.json.dumps(records[0].args if records else None), mimetype="application/json")
