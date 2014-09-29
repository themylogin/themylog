# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
import operator
from Queue import Queue
from threading import Thread
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response
from zope.interface import implements

import themyutils.json

from themylog.analytics import *
from themylog.disorder.manager import IDisorderManagerObserver
from themylog.handler.interface import IHandler, IRetrieveCapable, IRequiresHeartbeat
from themylog.record.serializer import serialize_json
from themylog.rules_tree import match_record, substitute_parameters


def setup_web_server(configuration, handlers, heartbeats, feeds, analytics):
    for handler in handlers:
        if IRetrieveCapable.providedBy(handler):
            retriever = handler
            break
    else:
        raise Exception("You should have at least one handler that is IRetrieveCapable to use web server")

    web_application = WebApplication(configuration, retriever, feeds, analytics)

    thread = Thread(target=web_application.serve_forever)
    thread.daemon = True
    thread.start()

    handlers.append(web_application)
    heartbeats.append(web_application)

    return web_application


class WebApplication(object):
    implements(IHandler, IRequiresHeartbeat, IDisorderManagerObserver)

    def __init__(self, configuration, retriever, feeds, analytics):
        self.configuration = configuration
        self.retriever = retriever
        self.feeds = feeds
        self.analytics = analytics

        self.url_map = Map([
            Rule("/", endpoint="feed"),
            Rule("/feed/<name>", endpoint="feed"),
            Rule("/analytics/<analytics>", endpoint="analytics"),
            Rule("/timeline/<application>", endpoint="timeline"),
            Rule("/timeline/<application>/<logger>", endpoint="timeline"),
            Rule("/timeseries/<application>", endpoint="timeseries"),
            Rule("/timeseries/<application>/<logger>", endpoint="timeseries"),
            Rule("/timeseries/<application>/<logger>/<msg>", endpoint="timeseries"),
            Rule("/disorders", endpoint="disorders"),
            Rule("/run/collector/<collector>", endpoint="run_collector"),
        ])

        self.gevent = None
        self.WebSocketError = None
        self.queues = set()

        self.disorders = {}
        self.disorder_queues = set()

        self.celery = None

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

    def heartbeat(self):
        for queue, async in self.queues.copy():
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

        return self.serve_records(request, rules_tree, limit, None)

    def execute_timeline(self, request, application, logger=None):
        rules_tree = (operator.eq, lambda k: k("application"), application)

        if logger is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("logger"), logger))

        limit = request.args.get("limit", 1, int)

        return self.serve_records(request, rules_tree, limit, None,
                                  serialize_one=lambda record: themyutils.json.dumps(record.args),
                                  serialize_collection=lambda records: themyutils.json.dumps([record.args
                                                                                              for record in records]))

    def execute_timeseries(self, request, application, logger=None, msg=None):
        rules_tree = (operator.eq, lambda k: k("application"), application)

        if logger is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("logger"), logger))

        if msg is not None:
            rules_tree = (operator.and_, rules_tree, (operator.eq, lambda k: k("msg"), msg))

        timeout = request.args.get("timeout", type=int)

        return self.serve_records(request, rules_tree, 1, timeout,
                                  serialize_one=lambda record: themyutils.json.dumps(record.args),
                                  serialize_collection=lambda records: themyutils.json.dumps(records[0].args if records
                                                                                             else None))

    def serve_records(self, request, rules_tree, limit, timeout,
                      serialize_one=serialize_json,
                      serialize_collection=lambda records: "[" + ",".join(map(serialize_json, records)) + "]"):
        records = self.retriever.retrieve((operator.and_, rules_tree, (operator.gt, lambda k: k("datetime"),
                                                                       datetime.now() - timedelta(seconds=timeout)))
                                          if timeout else rules_tree,
                                          limit)

        if "wsgi.websocket" in request.environ:
            queue = Queue()
            async = self.gevent.get_hub().loop.async()
            self.queues.add((queue, async))

            ws = request.environ["wsgi.websocket"]

            last_record = None
            try:
                for record in reversed(records):
                    ws.send(serialize_one(record))
                    last_record = record

                while True:
                    self.gevent.get_hub().wait(async)

                    expires = datetime.now() - timedelta(seconds=timeout) if timeout else None
                    while not queue.empty():
                        record = queue.get()
                        if rules_tree is None or match_record(rules_tree, record):
                            if not expires or record.datetime > expires:
                                ws.send(serialize_one(record))
                                last_record = record

                    if (limit == 1 and
                            expires and
                            last_record is not None and
                            last_record.datetime < expires):
                        ws.send("null")
                        last_record = None
            except self.WebSocketError:
                pass
            finally:
                self.queues.remove((queue, async))

                if not ws.closed:
                    ws.close()

            return Response()
        else:
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
                        ws.send(self.serialize_disorders(queue.get()))
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
        return themyutils.json.dumps([dict(title=title, **(maybe._asdict() if maybe else {"disorder": None}))
                                      for title, maybe in disorders.iteritems()])

    def execute_run_collector(self, request, collector):
        if self.celery is None:
            return Response("Celery is unavailable", 503)

        task = self.celery.tasks.get("collectors.%s" % collector)
        if task is None:
            return Response("Collector does not exist. Available collectors: %s" %
                            ", ".join([key for key in self.celery.tasks if key.startswith("collectors.")]), 404)

        task.delay()
        return Response()

    def execute_analytics(self, request, analytics):
        analytics = self.analytics.get(analytics)
        if analytics is None:
            return Response("Analytics does not exist", 404)

        kwargs = get_analytics_kwargs(analytics, self.retriever)

        if "wsgi.websocket" in request.environ:
            queue = Queue()
            async = self.gevent.get_hub().loop.async()
            self.queues.add((queue, async))

            ws = request.environ["wsgi.websocket"]

            try:
                ws.send(themyutils.json.dumps(analytics.analyze(**kwargs)))

                while True:
                    self.gevent.get_hub().wait(async)

                    kwargs_modified = False
                    if queue.empty():
                        # Just a heartbeat
                        kwargs_modified = process_analytics_special_kwargs(analytics, kwargs)
                    else:
                        while not queue.empty():
                            record = queue.get()
                            for feed in analytics.feeds_order:
                                rules_tree = prepare_analytics_rules_tree(analytics, feed, kwargs)
                                limit = analytics.feeds[feed].get("limit", None)
                                if match_record(rules_tree, record):
                                    if limit == 1:
                                        kwargs[feed] = record
                                    else:
                                        kwargs[feed] = [record] + kwargs[feed]
                                        if limit is not None:
                                            kwargs[feed] = kwargs[feed][:limit]
                                    kwargs_modified = True

                    if kwargs_modified:
                        ws.send(themyutils.json.dumps(analytics.analyze(**kwargs)))
            except self.WebSocketError:
                pass
            finally:
                self.queues.remove((queue, async))

                if not ws.closed:
                    ws.close()

            return Response()
        else:
            return Response(themyutils.json.dumps(analytics.analyze(**kwargs)), mimetype="application/json")
