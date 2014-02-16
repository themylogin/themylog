# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import operator
from Queue import Queue
from threading import Thread
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response
from zope.interface import implements

import themyutils.json

from themylog.disorder.manager import IDisorderManagerObserver
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

    return web_application


class WebApplication(object):
    implements(IHandler, IDisorderManagerObserver)

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
            Rule("/disorders", endpoint="disorders"),
        ])

        self.gevent = None
        self.WebSocketError = None
        self.queues = set()

        self.disorders = {}
        self.disorder_queues = set()

    def serve_forever(self):
        import gevent
        from geventwebsocket import WebSocketError
        from geventwebsocket.handler import WebSocketHandler

        self.gevent = gevent
        self.WebSocketError = WebSocketError
        return gevent.pywsgi.WSGIServer((self.configuration["host"], self.configuration["port"]),
                                        self.wsgi_app, handler_class=WebSocketHandler).serve_forever()

    def handle(self, record):
        for queue, async in self.queues.copy():
            queue.put(record)
            async.send()

    def update_disorders(self, disorders):
        self.disorders = disorders
        for queue, async in self.disorder_queues.copy():
            queue.put(disorders)
            async.send()

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        try:
            response = self.dispatch_request(request)
            response.headers.add(b"Access-Control-Allow-Origin", "*")
        except HTTPException as e:
            response = e
        return response(environ, start_response)

    def dispatch_request(self, request):
        endpoint, values = self.url_map.bind_to_environ(request.environ).match()
        return getattr(self, "execute_%s" % endpoint)(request, **values)

    def execute_feed(self, request, name=None):
        if name in self.feeds:
            rules_tree = self.feeds[name].rules_tree
        else:
            rules_tree = None

        limit = request.args.get("limit", 50, int)

        return self.serve_records(request, rules_tree, limit)

    def execute_timeline(self, request, application, logger=None):
        rules_tree = (operator.eq, lambda k: k("application"), application)

        if logger is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("logger"), logger))

        limit = request.args.get("limit", 1, int)

        return self.serve_records(request, rules_tree, limit,
                                  serialize_one=lambda record: themyutils.json.dumps(record.args),
                                  serialize_collection=lambda records: themyutils.json.dumps([record.args
                                                                                              for record in records]))

    def execute_timeseries(self, request, application, logger=None, msg=None):
        rules_tree = (operator.eq, lambda k: k("application"), application)

        if logger is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("logger"), logger))

        if msg is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("msg"), msg))

        return self.serve_records(request, rules_tree, 1,
                                  serialize_one=lambda record: themyutils.json.dumps(record.args),
                                  serialize_collection=lambda records: themyutils.json.dumps(records[0].args if records
                                                                                             else None))

    def serve_records(self, request, rules_tree, limit,
                      serialize_one=serialize_json,
                      serialize_collection=lambda records: "[" + ",".join(map(serialize_json, records)) + "]"):
        if "wsgi.websocket" in request.environ:
            queue = Queue()
            async = self.gevent.get_hub().loop.async()
            self.queues.add((queue, async))

            ws = request.environ["wsgi.websocket"]

            try:
                records = self.retriever.retrieve(rules_tree, limit)

                for record in reversed(records):
                    ws.send(serialize_one(record))

                while True:
                    self.gevent.get_hub().wait(async)

                    while not queue.empty():
                        record = queue.get()
                        if rules_tree is None or match_record(rules_tree, record):
                            ws.send(serialize_one(record))
            except self.WebSocketError:
                pass
            finally:
                self.queues.remove((queue, async))

                if not ws.closed:
                    ws.close()

            return Response()
        else:
            records = self.retriever.retrieve(rules_tree, limit)
            return Response(serialize_collection(records), mimetype="application/json")

    def execute_disorders(self, request):
        if "wsgi.websocket" in request.environ:
            queue = Queue()
            async = self.gevent.get_hub().loop.async()
            self.disorder_queues.add((queue, async))

            ws = request.environ["wsgi.websocket"]

            try:
                ws.send(self.serialize_disorders(self.disorders))

                while True:
                    self.gevent.get_hub().wait(async)

                    while not queue.empty():
                        ws.send(queue.get())
            except self.WebSocketError:
                pass
            finally:
                self.disorder_queues.remove((queue, async))

                if not ws.closed:
                    ws.close()

            return Response()
        else:
            return Response(self.serialize_disorders(self.disorders), mimetype="application/json")

    def serialize_disorders(self, disorders):
        return themyutils.json.dumps([(title, has_disorder, disorder._asdict())
                                      for title, (has_disorder, disorder) in disorders.iteritems()])
