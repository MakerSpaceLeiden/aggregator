import time


class Clock(object):
    @staticmethod
    def now_as_timestamp():
        return time.time()
