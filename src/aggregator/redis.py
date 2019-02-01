import redis
import json
from aggregator.model import User


class RedisAdapter(object):
    def __init__(self, host, port, db, key_prefix, expiration_time_in_sec):
        self.redis = redis.Redis(host=host, port=port, db=db)
        self.key_prefix = key_prefix
        self.expiration_time_in_sec = expiration_time_in_sec

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

    def store_user_in_space(self, user, ts, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Storing user ID {user.user_id} in space')
        self.redis.hset(self._k_users_in_space(), user.user_id, int(ts))

    def remove_user_from_space(self, user_id, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Removing user ID {user_id} from space')
        self.redis.hdel(self._k_users_in_space(), user_id)

    def get_user_ids_in_space(self, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info('Getting all users in space')
        values = self.redis.hkeys(self._k_users_in_space())
        user_ids = [int(value) for value in values]
        return user_ids

    def get_user_ids_in_space_with_timestamps(self, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info('Getting all users in space')
        values = self.redis.hgetall(self._k_users_in_space())
        return [(int(key), int(value)) for key, value in values.items()]

    # -- Keys ----

    def _k_users_by_id(self):
        return f'{self.key_prefix}:ui'

    def _k_users_in_space(self):
        return f'{self.key_prefix}:us'
