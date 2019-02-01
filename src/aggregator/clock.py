import time
import datetime
import humanize


HUMAN_DATETIME_STRING = '%H:%M:%S %d/%m/%Y'


class Clock(object):
    @staticmethod
    def now_as_timestamp():
        return time.time()

    @staticmethod
    def human_str_from_ts(ts):
        return datetime.datetime.fromtimestamp(ts).strftime(HUMAN_DATETIME_STRING)

    @staticmethod
    def human_time_delta_from_ts(ts):
        return humanize.naturaltime(datetime.datetime.fromtimestamp(ts))
