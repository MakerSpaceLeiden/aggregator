import logging
import random
import string
from logging.handlers import TimedRotatingFileHandler


CHARS_FOR_RANDOM_REQ_ID = string.digits + string.ascii_lowercase


def make_random_req_id():
    return ''.join([random.choice(CHARS_FOR_RANDOM_REQ_ID) for _ in range(7)])


def configure_logging(log_filepath=None, when=None, interval=None, backup_count=None):
    formatter = DispatchingFormatter({
        'aggregator': logging.Formatter('%(asctime)s - %(name)s - %(req_id)s - %(subsystem)s - %(levelname)s - %(message)s'),
        'quart.serving': logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        'quart.app': logging.Formatter('%(asctime)s - %(name)s - %(levelname)s in %(module)s: %(message)s'),
    }, logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    if log_filepath:
        handler = TimedRotatingFileHandler(log_filepath, when=when, interval=interval, backupCount=backup_count)
    else:
        handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    # Our own internal application logger wrapper
    logger = logging.getLogger('aggregator')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    application_logger = Logger(logger, subsystem='root')

    return application_logger, handler


def configure_logging_for_tests():
    logger = logging.getLogger('aggregator')
    logger.setLevel(logging.DEBUG)
    return Logger(logger, subsystem='root')


class Logger(object):
    def __init__(self, python_logger, **extra):
        extra.setdefault('subsystem', '')
        extra.setdefault('req_id', '__n/a__')
        self.python_logger = python_logger
        self.extra = extra

    def info(self, msg, **extra):
        e = self.extra.copy()
        e.update(extra)
        self.python_logger.info(msg, extra=e)

    def error(self, msg, exc_info=None, **extra):
        e = self.extra.copy()
        e.update(extra)
        self.python_logger.error(msg, exc_info=exc_info, extra=e)

    def exception(self, msg, exc_info=True, **extra):
        e = self.extra.copy()
        e.update(extra)
        self.python_logger.exception(msg, exc_info=exc_info, extra=e)

    def getLogger(self, **extra):
        new_extra = self.extra.copy()
        new_extra.update(extra)
        return Logger(self.python_logger, **new_extra)

    def getLoggerWithRandomReqId(self, prefix):
        new_extra = self.extra.copy()
        new_extra['req_id'] = f'{prefix}-{make_random_req_id()}'
        return Logger(self.python_logger, **new_extra)


# From https://stackoverflow.com/a/34626685

class DispatchingFormatter:
    def __init__(self, formatters, default_formatter):
        self._formatters = formatters
        self._default_formatter = default_formatter

    def format(self, record):
        # Search from record's logger up to it's parents:
        logger = logging.getLogger(record.name)
        while logger:
            # Check if suitable formatter for current logger exists:
            if logger.name in self._formatters:
                formatter = self._formatters[logger.name]
                break
            else:
                logger = logger.parent
        else:
            # If no formatter found, just use default:
            formatter = self._default_formatter
        return formatter.format(record)
