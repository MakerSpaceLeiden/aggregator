import time
import datetime
import humanize


HUMAN_DATETIME_STRING = '%H:%M:%S %d/%m/%Y'


class Clock(object):
    @staticmethod
    def now():
        return Time.from_timestamp(time.time())


class Time(object):
    def __init__(self, ts):
        self.ts = ts

    def __repr__(self):
        return f'<Time {self.human_str()}, {self.ts}>'

    def as_int_timestamp(self):
        return int(self.ts)

    def sorting_key(self):
        return self.ts

    @classmethod
    def from_timestamp(cls, ts):
        return cls(ts)

    def human_str(self):
        return datetime.datetime.fromtimestamp(self.ts).strftime(HUMAN_DATETIME_STRING)

    def human_delta_from(self, ts_from):
        delta = self.ts - ts_from.ts
        return humanize.naturaldelta(delta) + ' ago'

    def delta_in_hours(self, ts_from):
        return (self.ts - ts_from.ts) / 3600


class MockClock(object):
    def __init__(self):
        self.now_ts = 1549180499.251611  # ~ 3 Feb 2019 8:55

    # Set a time during day 3 Feb 2019, e.g. "06:13" or "13:27"
    def set_time_of_day(self, time_str):
        d = datetime.datetime.strptime(time_str + ' 03/02/2019', '%H:%M %d/%m/%Y')
        self.now_ts = time.mktime(d.timetuple())

    def add(self, how_much, what):
        if what in ('hour', 'hours'):
            self.now_ts += how_much * 3600

    def now(self):
        return Time.from_timestamp(self.now_ts)

