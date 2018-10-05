import logging

from flask import Flask, request
from Queue import Empty
from wsgiref.simple_server import make_server

logger = logging.getLogger(__name__)

class CallbackListenerWebApp(Flask):
    def __init__(self, import_name, downloader_cmd_queue):
        super(CallbackListenerWebApp, self).__init__(import_name)
        self._downloader_cmd_queue = downloader_cmd_queue
        self.route('/', methods=["GET", "POST"])(self.receive)

    def receive(self):
        if request.method == "POST":
            logger.info(u"received POST: {}".format(request.data))
            self._downloader_cmd_queue.put_nowait("poll")
        else:
            logger.warn(u"unsupported HTTP method: {}".format(request.data))
        return ""


class CallbackListener:
    def __init__(self, cmd_queue, port, downloader_cmd_queue):
        self._cmd_queue = cmd_queue
        self._port = port
        self._downloader_cmd_queue = downloader_cmd_queue

    def run(self):
        logger.info("started")
        webapp = CallbackListenerWebApp(__name__, self._downloader_cmd_queue)
        httpd = make_server("", self._port, webapp)

        httpd.serve_forever()



