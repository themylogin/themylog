import logging
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

from themylog.config import find_config, read_config, create_storages, get_feeds
from themylog.record.serializer import serialize_json
from themylog.storage.interface import IRetriever

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = read_config(find_config())

    """Create storages"""

    storages = create_storages(config)

    for storage in storages:
        if IRetriever.providedBy(storage):
            retriever = storage
            break
    else:
        raise Exception("You should have at least one storage that implements IRetriever to use web server")

    """Get feeds"""

    feeds = get_feeds(config)

    """Web application"""

    def application(environ, start_response):
        request = Request(environ)

        if "feed" in request.args and request.args["feed"] in feeds:
            feed = feeds[request.args["feed"]]
        else:
            feed = None

        response = Response("[" + ",".join(map(serialize_json,retriever.retrieve(feed))) + "]",
                            mimetype="application/json")
        return response(environ, start_response)

    run_simple("0.0.0.0", 46405, application)
