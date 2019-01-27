import redis
import json
from aggregator.model import User


class RedisAdapter(object):
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.key_prefix = 'msl'
        self.expiration_time_in_sec = 60

    def get_user_by_id(self, user_id, logger):
        logger = logger.getLogger(subsystem='redis')
        data = self.redis.hget(self._k_users_by_id(), str(user_id))
        if data:
            logger.info(f'Found user {user_id}')
            return User(**json.loads(data))
        else:
            logger.info(f'User {user_id} not found')

    def set_users_by_ids(self, users, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Storing {len(users)} users')
        self.redis.hmset(self._k_users_by_id(), dict((str(user.user_id), json.dumps(user._asdict())) for user in users))
        self.redis.pexpire(self._k_users_by_id(), self.expiration_time_in_sec * 1000)

    # -- Keys ----

    def _k_users_by_id(self):
        return f'{self.key_prefix}:ui'
