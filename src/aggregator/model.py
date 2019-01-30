from collections import namedtuple


class User(namedtuple('User', 'user_id first_name last_name email')):
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


Tag = namedtuple('Tag', 'tag_id tag user')
