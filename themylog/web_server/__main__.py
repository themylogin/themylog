import logging
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

from themylog.config import find_config, read_config
from themylog.config.handlers import create_handlers
from themylog.config.feeds import get_feeds
from themylog.handler.interface import IRetrieveCapable
from themylog.record.serializer import serialize_json

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = read_config(find_config())

    """Create handlers"""

    handlers = create_handlers(config)

    for handler in handlers:
        if IRetrieveCapable.providedBy(handler):
            retriever = handler
            break
    else:
        raise Exception("You should have at least one handler that is IRetrieveCapable to use web server")

    """Get feeds"""

    feeds = get_feeds(config)

    """Web application"""

    def application(environ, start_response):
        request = Request(environ)

        if "feed" in request.args and request.args["feed"] in feeds:
            feed = feeds[request.args["feed"]]
        else:
            feed = None

        limit = request.args.get("limit", 50, int)

        response = Response("[" + ",".join(map(serialize_json, retriever.retrieve(feed.rules_tree, limit))) + "]",
                            headers=[("Access-Control-Allow-Origin", "*")],
                            mimetype="application/json")
        return response(environ, start_response)

    run_simple("0.0.0.0", 46405, application)
