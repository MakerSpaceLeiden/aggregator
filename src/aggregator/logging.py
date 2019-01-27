import logging

logger = logging.getLogger('aggregator')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s:%(subsystem)s - %(levelname)s - %(message)s')
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

