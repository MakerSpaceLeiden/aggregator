import time
import datetime
import humanize
from functools import total_ordering


HUMAN_DATETIME_STRING = '%H:%M:%S %d/%m/%Y'


class Clock(object):
    @staticmethod
    def now():
        return Time.from_timestamp(time.time())


@total_ordering
class Time(object):
    def __init__(self, ts):
        self.ts = ts

    def __repr__(self):
        return f'<Time {self.human_str()}, {self.ts}>'

    def __eq__(self, other):
        return self.ts == other.ts

    def __ne__(self, other):
        return self.ts != other.ts

    def __lt__(self, other):
        return self.ts < other.ts

    def __hash__(self):
        return hash(self.ts)

    def as_int_timestamp(self):
        return int(self.ts)

    def sorting_key(self):
        return self.ts

    def replace(self, hour=None, minute=None):
        return Time(datetime.datetime.fromtimestamp(self.ts).replace(hour=hour, minute=minute, second=0).timestamp())

    @classmethod
    def from_timestamp(cls, ts):
        return cls(ts)

    @classmethod
    def from_datetime(cls, dt):
        return cls(dt.timestamp())

    def human_str(self):
        return self.strftime(HUMAN_DATETIME_STRING)

    def strftime(self, _format):
        return datetime.datetime.fromtimestamp(self.ts).strftime(_format)

    def human_delta_from(self, ts_from):
        delta = self.ts - ts_from.ts
        return humanize.naturaldelta(delta) + ' ago'

    def delta_in_hours(self, ts_from):
        return (self.ts - ts_from.ts) / 3600

    def add(self, how_much, what):
        if what in ('minute', 'minutes'):
            return Time(self.ts + how_much * 60)
        if what in ('hour', 'hours'):
            return Time(self.ts + how_much * 3600)
        if what in ('day', 'days'):
            return Time(self.ts + how_much * 3600 * 24)


class MockClock(object):
    def __init__(self):
        self.now_ts = 1549180499.251611  # ~ 3 Feb 2019 8:55

    def set_day_and_time(self, ts_str):
        d = datetime.datetime.strptime(ts_str, '%d/%m/%Y %H:%M')
        self.now_ts = time.mktime(d.timetuple())
        return self.now()

    # Set a time during day 3 Feb 2019, e.g. "06:13" or "13:27"
    def set_time_of_day(self, time_str):
        d = datetime.datetime.strptime(time_str + ' 03/02/2019', '%H:%M %d/%m/%Y')
        self.now_ts = time.mktime(d.timetuple())
        return self.now()

    def add(self, how_much, what):
        if what in ('hour', 'hours'):
            self.now_ts += how_much * 3600

    def now(self):
        return Time.from_timestamp(self.now_ts)

