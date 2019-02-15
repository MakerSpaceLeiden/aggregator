import random
import string


CHARS_FOR_RANDOM_REQ_ID = string.digits + string.ascii_lowercase


def make_random_string(length):
    return ''.join([random.choice(CHARS_FOR_RANDOM_REQ_ID) for _ in range(length)])
