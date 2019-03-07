from datetime import timezone, datetime, timedelta
from dateutil.tz import tzlocal
import humanize
from croniter import croniter
from functools import total_ordering


HUMAN_DATETIME_STRING = '%H:%M:%S %d/%m/%Y'


local_timezone = tzlocal()


# Used for testing
def set_local_timezone_to_utc():
    global local_timezone
    local_timezone = timezone.utc


class Clock(object):
    @staticmethod
    def now():
        return Time.from_datetime(datetime.utcnow())


@total_ordering
class Time(object):
    # Internally represents time in UTC
    # The internal instance of datetime object is naive, i.e. without timezone information

    def __init__(self, dt):
        self.dt = dt

    def __repr__(self):
        return f'<Time {self.human_str()}>'

    def __eq__(self, other):
        return self.dt == other.dt

    def __ne__(self, other):
        return self.dt != other.dt

    def __lt__(self, other):
        return self.dt < other.dt

    def __hash__(self):
        return hash(self.dt)

    def as_int_timestamp(self):
        return int(self.dt.replace(tzinfo=timezone.utc).timestamp())

    def sorting_key(self):
        return self.as_int_timestamp()

    def replace(self, hour=None, minute=None):
        return Time(self.dt.replace(hour=hour, minute=minute, second=0))

    @classmethod
    def from_timestamp(cls, ts):
        return cls(datetime.utcfromtimestamp(ts))

    @classmethod
    def from_datetime(cls, dt):
        return cls(dt)

    def human_str(self):
        return self.strftime(HUMAN_DATETIME_STRING)

    def strftime(self, _format):
        return self.dt.replace(tzinfo=timezone.utc).astimezone(local_timezone).strftime(_format)

    def human_delta_from(self, ts_from):
        delta = (self.dt - ts_from.dt).total_seconds()
        return humanize.naturaldelta(delta) + ' ago'

    def delta_in_hours(self, ts_from):
        return (self.dt - ts_from.dt).total_seconds() / 3600

    def add(self, how_much, what):
        if what in ('minute', 'minutes'):
            return Time(self.dt + timedelta(minutes=how_much))
        if what in ('hour', 'hours'):
            return Time(self.dt + timedelta(hours=how_much))
        if what in ('day', 'days'):
            return Time(self.dt + timedelta(days=how_much))

    @classmethod
    def iter_crontab(cls, crontab, starting_ts):
        croniter_iterator = croniter(crontab, starting_ts.dt)
        while True:
            dt = croniter_iterator.get_next(datetime)
            yield cls.from_datetime(dt)


class MockClock(object):
    def __init__(self):
        self.now_dt = None
        self.set_day_and_time('3/2/2019 8:55')

    def set_day_and_time(self, ts_str):
        self.now_dt = datetime.strptime(ts_str, '%d/%m/%Y %H:%M')
        return self.now()

    # Set a time during day 3 Feb 2019, e.g. "06:13" or "13:27"
    def set_time_of_day(self, time_str):
        self.now_dt = datetime.strptime(time_str + ' 03/02/2019', '%H:%M %d/%m/%Y')
        return self.now()

    def add(self, how_much, what):
        if what in ('hour', 'hours'):
            self.now_dt += timedelta(hours=how_much)

    def now(self):
        return Time.from_datetime(self.now_dt)

