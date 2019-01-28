from collections import namedtuple


User = namedtuple('User', 'user_id first_name last_name email')
Tag = namedtuple('Tag', 'tag_id tag user')
