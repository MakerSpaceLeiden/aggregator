import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger('aggregator')


def configure_logging(log_filepath=None, when=None, interval=None, backup_count=None):
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(req_id)s - %(subsystem)s - %(levelname)s - %(message)s')

    if log_filepath:
        ch = TimedRotatingFileHandler(log_filepath, when=when, interval=interval, backupCount=backup_count)
    else:
        ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class Logger(object):
    def __init__(self, **extra):
        extra.setdefault('subsystem', '')
        extra.setdefault('req_id', '')
        self.extra = extra

    def info(self, msg, **extra):
        e = self.extra.copy()
        e.update(extra)
        logger.info(msg, extra=e)

    def error(self, msg, exc_info=None, **extra):
        e = self.extra.copy()
        e.update(extra)
        logger.error(msg, exc_info=exc_info, extra=e)

    def exception(self, msg, exc_info=True, **extra):
        e = self.extra.copy()
        e.update(extra)
        logger.exception(msg, exc_info=exc_info, extra=e)

    def getLogger(self, **extra):
        new_extra = self.extra.copy()
        new_extra.update(extra)
        return Logger(**new_extra)

