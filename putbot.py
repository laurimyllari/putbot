import argparse
import putiopy
import logging
import os

from ConfigParser import SafeConfigParser
from multiprocessing import Process, Queue
from time import sleep

from putbot.callbacklistener import CallbackListener
from putbot.downloader import Downloader
from putbot.watcher import Watcher

class PutBot(object):
    def __init__(self, client, putio_rootfolder, torrents, incomplete, downloads, callback_url=None, listen_port=5000):
        self._client = client
        self._putio_rootfolder = putio_rootfolder
        self._torrents = torrents
        self._incomplete = incomplete
        self._downloads = downloads
        self._callback_url = callback_url
        self._listen_port = listen_port
        self._watcher_cmd_queue = Queue()
        self._downloader_cmd_queue = Queue()
        self._callbacklistener_cmd_queue = Queue()

    def run(self):
        logging.info("launch torrent watcher process for {}".format(self._torrents))
        self._watcher = Watcher(self._watcher_cmd_queue, self._torrents, self._client, self._putio_rootfolder)
        self._watcher_process = Process(target = self._watcher.run)
        self._watcher_process.start()

        logging.info("launch downloader process ({} to {})".format(self._incomplete, self._downloads))
        self._downloader = Downloader(self._downloader_cmd_queue, self._client, self._putio_rootfolder, self._incomplete, self._downloads)
        self._downloader_process = Process(target = self._downloader.run)
        self._downloader_process.start()

        logging.info("launch callback listener on port {}".format(self._listen_port))
        self._callbacklistener = CallbackListener(self._callbacklistener_cmd_queue, self._listen_port, self._downloader_cmd_queue)
        self._callbacklistener_process = Process(target=self._callbacklistener.run)
        self._callbacklistener_process.start()

    def exit(self):
        logging.info("shut down putbot")
        self._watcher_cmd_queue.put_nowait("exit")
        self._downloader_cmd_queue.put_nowait("exit")
        self._callbacklistener_cmd_queue.put_nowait("exit")

        self._watcher_process.join()
        logging.info("watcher exited")
        self._downloader_process.join()
        logging.info("downloader exited")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Output informational messages")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Output debug messages")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    config = SafeConfigParser(allow_no_value = True)
    config.read("putbot.ini")

    oauth_token = os.getenv("PUTBOT_TOKEN", config.get("putio", "token"))
    client = putiopy.Client(oauth_token)

    putio_rootfolder = os.getenv("PUTBOT_ROOTFOLDER", config.get("putio", "rootfolder"))

    torrents = os.getenv("PUTBOT_TORRENTS", config.get("local", "torrents"))
    incomplete = os.getenv("PUTBOT_INCOMPLETE", config.get("local", "incomplete"))
    downloads = os.getenv("PUTBOT_DOWNLOADS", config.get("local", "downloads"))

    putbot = PutBot(client, putio_rootfolder, torrents, incomplete, downloads)

    putbot.run()

    try:
        while True:
            sleep(60)
    except KeyboardInterrupt:
        logging.info("keyboard interrupt")
        putbot.exit()

