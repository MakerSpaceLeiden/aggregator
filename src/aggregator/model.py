from collections import namedtuple


# -- Domain objects ----

class User(namedtuple('User', 'user_id first_name last_name email')):
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def for_json(self):
        d = dict(self._asdict())
        d['full_name'] = self.full_name
        return d


Tag = namedtuple('Tag', 'tag_id tag user')
