import binascii
import io
import logging
import os
import os.path
import shutil
import subprocess

from Queue import Empty

KB = 1024
CHUNK_SIZE = 256 * KB

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self, cmd_queue, client, rootfolder, incomplete, downloads):
        self._cmd_queue = cmd_queue
        self._client = client
        self._rootfolder = rootfolder
        self._incomplete = incomplete
        self._downloads = downloads

    def run(self):
        logger.info("started")

        try:
            while True:
                self._poll_and_process()
                try:
                    cmd = self._cmd_queue.get(timeout=900)
                    if cmd == "exit":
                        logger.debug("downloader got exit event")
                        break
                    if cmd == "poll":
                        logger.debug("downloader got poll event")
                        # no need to do anything here, next iteration will poll
                except Empty:
                    pass
        except KeyboardInterrupt:
            logger.debug("watcher got keyboard interrupt")
        finally:
            pass

        logger.info("exiting")

    def _poll_and_process(self):
        logger.info("checking for files to download")
        for f in self._client.File.list(parent_id=self._rootfolder):
            self._process(f)

    def _process(self, f):
        logger.info("process {}".format(f.name))

        self._download(f, self._incomplete)
        if self._verify(f, self._incomplete):
            logger.info("verified {}".format(f.name))
            self._move(f, self._incomplete, self._downloads)
            f.delete()
        else:
            logger.warning("verification failed {}".format(f.name))

    def _download(self, f, path):
        logger.info("download {} to {}".format(f.name, path))
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
            if os.path.getsize(destfile) == f.size and not os.path.exists(destfile+".aria2"):
                logger.info("{} is already correct size ({})".format(destfile, f.size))
                return

        dl_redirect = self._client.request('/files/%s/download' % f.id, raw=True, allow_redirects=False)
        if dl_redirect.status_code == 302:
            url = dl_redirect.headers["Location"]
            logger.debug("download redirect: {}".format(url))
            # subprocess.call(["wget", "-c", "-O", destfile, url])
            subprocess.call(["aria2c", "-c", "-x4", "-d", path, "-o", f.name, url])

    def _verify(self, f, path):
        logger.info("verify {} in {}".format(f.name, path))
        if f.file_type == "FOLDER":
            logger.debug("{} is a folder".format(f.name))
            destdir = os.path.join(path, f.name)
            for child in f.dir():
                if not self._verify(child, destdir):
                    return False
        else:
            logger.debug("{} is a file".format(f.name))
            return self._verify_file(f, path)
        return True

    def _verify_file(self, fobj, path):
        logger.debug("verify file {} in {}".format(fobj.name, path))
        crcbin = 0
        filepath = os.path.join(path, fobj.name)
        with io.open(filepath, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                crcbin = binascii.crc32(chunk, crcbin) & 0xffffffff

        crc32 = '%08x' % crcbin

        if crc32 != fobj.crc32:
            logging.error('file %s CRC32 is %s, should be %s' % (filepath, crc32, fobj.crc32))
            return False

        return True

    def _move(self, fobj, src, dst):
        logger.info("move {} from {} to {}".format(fobj.name, src, dst))
        shutil.move(os.path.join(src, fobj.name), dst)

