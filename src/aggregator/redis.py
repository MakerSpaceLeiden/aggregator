import redis
import json
from aggregator.model import User, Machine
from .clock import Time


class RedisAdapter(object):
    def __init__(self, clock, host, port, db, key_prefix, users_expiration_time_in_sec, pending_machine_activation_timeout_in_sec):
        self.clock = clock
        self.redis = redis.Redis(host=host, port=port, db=db)
        self.key_prefix = key_prefix
        self.users_expiration_time_in_sec = users_expiration_time_in_sec
        self.pending_machine_activation_timeout_in_sec = pending_machine_activation_timeout_in_sec

    def get_machine_by_name(self, machine, logger):
        logger = logger.getLogger(subsystem='redis')
        data = self.redis.hget(self._k_machines_by_id(), machine)
        if data:
            logger.info(f'Found machine {machine}')
            return Machine(**json.loads(data))
        else:
            logger.info(f'Machine {machine} not found')

    def set_all_machines(self, machines, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Storing {len(machines)} machines')
        self.redis.hmset(self._k_machines_by_id(), dict((str(machine.node_machine_name), json.dumps(machine._asdict())) for machine in machines))
        self.redis.pexpire(self._k_machines_by_id(), self.users_expiration_time_in_sec * 1000)

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
        self.redis.pexpire(self._k_users_by_id(), self.users_expiration_time_in_sec * 1000)

    def store_user_in_space(self, user, ts, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Storing user ID {user.user_id} in space')
        self.redis.hset(self._k_users_in_space(), user.user_id, ts.as_int_timestamp())

    def remove_user_from_space(self, user_id, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Removing user ID {user_id} from space')
        self.redis.hdel(self._k_users_in_space(), user_id)

    def get_user_ids_in_space_with_timestamps(self, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info('Getting all users in space')
        values = self.redis.hgetall(self._k_users_in_space())
        return [(int(key), Time.from_timestamp(int(value))) for key, value in values.items()]

    def store_pending_machine_activation(self, user_id, machine, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Storing pending machine activation: user {user_id}, machine {machine}')
        self.redis.setex(self._k_pending_machine_activation(machine), self.pending_machine_activation_timeout_in_sec, str(user_id))

    def get_pending_machine_activation(self, machine, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Reading pending machine activation for machine {machine}')
        value = self.redis.get(self._k_pending_machine_activation(machine))
        return int(value) if value else None

    def set_machine_on(self, machine, user_id, ts, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Setting machine {machine} state ON, for user {user_id}')
        self.redis.set(self._k_machine_on(machine), json.dumps({'user_id': user_id, 'ts': ts.as_int_timestamp()}))
        self.redis.sadd(self._k_machines_on(), machine)

    def get_machine_on(self, machine, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Reading machine {machine} state')
        value = self.redis.get(self._k_machine_on(machine))
        if value:
            data = json.loads(value)
            data['ts'] = Time.from_timestamp(data['ts'])
            return data

    def set_machine_off(self, machine, user_id, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Setting machine {machine} state OFF, for user {user_id}')
        self.redis.delete(self._k_machine_on(machine))
        self.redis.srem(self._k_machines_on(), machine)

    def get_machines_on(self, logger):
        logger = logger.getLogger(subsystem='redis')
        logger.info(f'Reading ON machines')
        return [m.decode('utf-8') for m in self.redis.smembers(self._k_machines_on())]

    # -- Keys ----

    def _k_pending_machine_activation(self, machine):
        return f'{self.key_prefix}:ma{machine}'

    def _k_machines_by_id(self):
        return f'{self.key_prefix}:mc'

    def _k_machine_on(self, machine):
        return f'{self.key_prefix}:mo{machine}'

    def _k_machines_on(self):
        return f'{self.key_prefix}:ms'

    def _k_users_by_id(self):
        return f'{self.key_prefix}:ui'

    def _k_users_in_space(self):
        return f'{self.key_prefix}:us'

