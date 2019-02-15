from collections import namedtuple
from .clock import Time


# -- Domain objects ----

class User(namedtuple('User', 'user_id first_name last_name email telegram_user_id')):
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def for_json(self):
        d = dict(self._asdict())
        d['full_name'] = self.full_name
        del d['telegram_user_id']
        return d

    def uses_telegram(self):
        return bool(self.telegram_user_id)


Tag = namedtuple('Tag', 'tag_id tag user')


class Machine(namedtuple('Machine', 'machine_id name description node_machine_name node_name location_name')):
    def for_json(self):
        return dict(self._asdict())


class Light(namedtuple('Light', 'label name')):
    def for_json(self):
        return dict(self._asdict())


ALL_LIGHTS = [
    Light('large_room', 'Large room'),
]


# -- History lines ----


UserEntered = namedtuple('UserEntered', 'user_id ts first_name last_name')
UserLeft    = namedtuple('UserLeft',    'user_id ts first_name last_name')


ALL_HISTORY_LINES = [
    UserEntered,
    UserLeft,
]

DICT_ALL_HISTORY_LINES = dict((cls.__name__, cls) for cls in ALL_HISTORY_LINES)


def history_line_to_json(hl):
    data = dict(hl._asdict())
    for key, value in data.items():
        if isinstance(value, Time):
            data[key] = value.as_int_timestamp()
    data['hl_type'] = hl.__class__.__name__
    return data


def json_to_history_line(data):
    for key, value in data.items():
        if key.startswith('ts'):
            data[key] = Time.from_timestamp(data[key])
    cls = DICT_ALL_HISTORY_LINES[data['hl_type']]
    del data['hl_type']
    return cls(**data)


def get_history_line_description(hl):
    template = {
        'UserEntered': 'User {first_name} {last_name} entered the space at {ts}',
        'UserLeft': 'User {first_name} {last_name} left the space at {ts}',
    }[hl.__class__.__name__]
    data = dict(hl._asdict())
    if 'ts' in data:
        data['ts'] = data['ts'].human_str()
    return template.format(**data)
