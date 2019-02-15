from collections import namedtuple


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
