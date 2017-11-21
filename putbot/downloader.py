import logging
import os
import os.path
import subprocess

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self, exit_event, client, rootfolder, incomplete, downloads):
        self._exit_event = exit_event
        self._client = client
        self._rootfolder = rootfolder
        self._incomplete = incomplete
        self._downloads = downloads

    def run(self):
        logger.info("started")

        # process existing files first
        for f in self._client.File.list(parent_id=self._rootfolder):
            self._process(f)

        try:
            while True:
                self._exit_event.wait(60)
                if self._exit_event.is_set():
                    logger.debug("downloader got exit event")
                    break
        except KeyboardInterrupt:
            logger.debug("watcher got keyboard interrupt")
        finally:
            pass

        logger.info("exiting")

    def _process(self, f):
        logger.debug("process {}".format(f.name))

        self._download(f, self._incomplete)
        if self._verify(f, self._incomplete):
            logger.debug("verified {}".format(f.name))
            self._move(f, self._incomplete, self._downloads)
            f.delete()
        else:
            logger.debug("verification failed {}".format(f.name))

    def _download(self, f, path):
        logger.debug("download {} to {}".format(f.name, path))
        if f.file_type == "FOLDER":
            logger.debug("{} is a folder".format(f.name))
            destdir = os.path.join(path, f.name)
            if not os.path.exists(destdir):
                os.makedirs(destdir)
            for child in f.dir():
                self._download(child, destdir)
        else:
            logger.debug("{} is a file".format(f.name))
            self._download_file(f, path)

    def _download_file(self, f, path):
        logger.debug("download file {} to {}".format(f.name, path))
        destfile = os.path.join(path, f.name)

        if os.path.exists(destfile):
            if os.path.getsize == f.size and not os.path.exists(destfile+".aria2"):
                logger.debug("{} is already correct size ({})".format(destdir, f.size))
                return

        dl_redirect = self._client.request('/files/%s/download' % f.id, raw=True, allow_redirects=False)
        if dl_redirect.status_code == 302:
            url = dl_redirect.headers["Location"]
            logger.debug("download redirect: {}".format(url))
            # subprocess.call(["wget", "-c", "-O", destfile, url])
            subprocess.call(["aria2c", "-c", "-x4", "-d", path, "-o", f.name, url])

    def _verify(self, f, path):
        logger.debug("verify {} in {}".format(f.name, path))
        return False

    def _verify_file(self, f, path):
        logger.debug("verify file {} in {}".format(f.name, path))
        return False

    def _move(self, f, src, dst):
        logger.debug("move {} to {}".format(src, dst))

