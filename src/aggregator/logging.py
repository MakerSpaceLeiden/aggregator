import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('aggregator')


def configure_logging(log_filepath=None, max_bytes=None, backup_count=None):
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s:%(subsystem)s - %(levelname)s - %(message)s')

    if log_filepath:
        ch = RotatingFileHandler(log_filepath, maxBytes=max_bytes, backupCount=backup_count)
    else:
        ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class Logger(object):
    def __init__(self, **extra):
        self.extra = extra

    def info(self, msg, **extra):
        e = self.extra.copy()
        e.update(extra)
        logger.info(msg, extra=e)

    def error(self, msg, **extra):
        e = self.extra.copy()
        e.update(extra)
        logger.error(msg, extra=e)

    def exception(self, msg, **extra):
        e = self.extra.copy()
        e.update(extra)
        logger.exception(msg, extra=e)

    def getLogger(self, **extra):
        new_extra = self.extra.copy()
        new_extra.update(extra)
        return Logger(**new_extra)

