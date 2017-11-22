import inotify.adapters
import inotify.constants
import logging
import os
import os.path

from Queue import Empty

logger = logging.getLogger(__name__)

class Watcher:
    def __init__(self, cmd_queue, directory, client, rootfolder):
        self._cmd_queue = cmd_queue
        self._directory = directory
        self._client = client
        self._rootfolder = rootfolder

    def run(self):
        logger.info("started")

        # process existing files first
        for filename in os.listdir(self._directory):
            self._process(filename)

        i = inotify.adapters.Inotify()
        i.add_watch(self._directory, mask=inotify.constants.IN_CLOSE_WRITE|inotify.constants.IN_MOVED_TO)

        try:
            for event in i.event_gen():
                if event is not None:
                    (header, type_names, watch_path, filename) = event
                    logger.debug("WD=(%d) MASK=(%d) COOKIE=(%d) LEN=(%d) MASK->NAMES=%s "
                             "WATCH-PATH=[%s] FILENAME=[%s]",
                             header.wd, header.mask, header.cookie, header.len, type_names,
                             watch_path.decode('utf-8'), filename.decode('utf-8'))
                    try:
                        self._process(filename.decode('utf-8'))
                    except Exception as e:
                        logger.exception("error processing {}".format(filename))
                else:
                    # inotify timed out, check command queue
                    try:
                        cmd = self._cmd_queue.get_nowait()
                        if cmd == "exit":
                            logger.debug("watcher got exit event")
                            break
                    except Empty:
                        pass
        except KeyboardInterrupt:
            logger.debug("watcher got keyboard interrupt")
        finally:
            i.remove_watch(self._directory)

        logger.info("exiting")

    def _process(self, filename):
        logger.debug("process {}".format(filename))
        path = os.path.join(self._directory, filename)
        _, ext = os.path.splitext(path)
        if ext == '.magnet':
            with open(path) as f: magnet_uri = f.read()
            transfer = self._client.Transfer.add_url(magnet_uri, parent_id=self._rootfolder)
            os.unlink(path)
        elif ext == '.torrent':
            transfer = self._client.Transfer.add_torrent(path, parent_id=self._rootfolder)
            os.unlink(path)
        else:
            logger.info("unknown file extension {}".format(filename))
