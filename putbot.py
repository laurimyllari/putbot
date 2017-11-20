import argparse
import putiopy
import logging
import os

from ConfigParser import SafeConfigParser
from multiprocessing import Process, Queue
from threading import Event
from time import sleep

from putbot.watcher import Watcher

class PutBot(object):
    def __init__(self, client, putio_rootfolder, torrents, incomplete, downloads):
        self._client = client
        self._putio_rootfolder = putio_rootfolder
        self._torrents = torrents
        self._incomplete = incomplete
        self._downloads = downloads
        self._exit = Event()

    def run(self):
        logging.info("launch torrent watcher process for {}".format(self._torrents))
        self._watcher = Watcher(self._exit, self._torrents, self._client, self._putio_rootfolder)
        self._watcher_process = Process(target = self._watcher.run)
        self._watcher_process.start()

        logging.info("launch put.io polling process for folder {}".format(self._putio_rootfolder))
        logging.info("launch callback listener process")
        logging.info("launch downloader process ({} to {})".format(self._incomplete, self._downloads))

    def exit(self):
        logging.info("shut down putbot")
        self._exit.set()
        self._watcher_process.join()
        logging.info("watcher exited")


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

