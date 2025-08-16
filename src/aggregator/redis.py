import json

import redis

from aggregator.model import Machine, User

from .clock import Time
from .model import history_line_to_json, json_to_history_line
from .utils import make_random_string


class RedisAdapter(object):
    def __init__(
        self,
        clock,
        host,
        port,
        db,
        password,
        key_prefix,
        users_expiration_time_in_sec,
        pending_machine_activation_timeout_in_sec,
        telegram_token_expiration_in_sec,
        machine_state_timeout_in_minutes,
        history_lines_expiration_in_days,
    ):
        self.clock = clock
        self.redis = redis.Redis(host=host, port=port, db=db, password=password)
        self.key_prefix = key_prefix
        self.users_expiration_time_in_sec = users_expiration_time_in_sec
        self.pending_machine_activation_timeout_in_sec = (
            pending_machine_activation_timeout_in_sec
        )
        self.telegram_token_expiration_in_sec = telegram_token_expiration_in_sec
        self.machine_state_timeout_in_minutes = machine_state_timeout_in_minutes
        self.history_lines_expiration_in_days = history_lines_expiration_in_days

    def get_machine_by_name(self, machine, logger):
        logger = logger.getLogger(subsystem="redis")
        data = self.redis.hget(self._k_machines_by_id(), machine)
        if data:
            logger.info(f"Found machine {machine}")
            return Machine(**json.loads(data))
        else:
            logger.info(f"Machine {machine} not found")

    def set_all_machines(self, machines, logger):
        logger = logger.getLogger(subsystem="redis")
        if len(machines) > 0:
            logger.info(f"Storing {len(machines)} machines")
            self.redis.hmset(
                self._k_machines_by_id(),
                dict(
                    (str(machine.node_machine_name), json.dumps(machine._asdict()))
                    for machine in machines
                ),
            )
            self.redis.pexpire(
                self._k_machines_by_id(), self.users_expiration_time_in_sec * 1000
            )

    def get_all_machines(self, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info("Getting all machines")
        values = self.redis.hvals(self._k_machines_by_id())
        return [Machine(**json.loads(value)) for value in values]

    def get_user_by_id(self, user_id, logger):
        logger = logger.getLogger(subsystem="redis")
        data = self.redis.hget(self._k_users_by_id(), str(user_id))
        if data:
            logger.info(f"Found user {user_id}")
            return User(**json.loads(data))
        else:
            logger.info(f"User {user_id} not found")

    def set_users_by_ids(self, users, logger):
        logger = logger.getLogger(subsystem="redis")
        if len(users) > 0:
            logger.info(f"Storing {len(users)} users")
            self.redis.delete(self._k_users_by_id())
            self.redis.hmset(
                self._k_users_by_id(),
                dict((str(user.user_id), json.dumps(user._asdict())) for user in users),
            )
            self.redis.pexpire(
                self._k_users_by_id(), self.users_expiration_time_in_sec * 1000
            )

            self.redis.delete(self._k_users_by_telegram_id())
            telegram_users = [u for u in users if u.telegram_user_id]
            if len(telegram_users) > 0:
                self.redis.hmset(
                    self._k_users_by_telegram_id(),
                    dict(
                        (user.telegram_user_id, json.dumps(user._asdict()))
                        for user in telegram_users
                    ),
                )
                self.redis.pexpire(
                    self._k_users_by_telegram_id(),
                    self.users_expiration_time_in_sec * 1000,
                )

            self.redis.delete(self._k_users_by_phone_number())
            users_with_phone_number = [u for u in users if u.phone_number]
            if len(users_with_phone_number) > 0:
                self.redis.hmset(
                    self._k_users_by_phone_number(),
                    dict(
                        (user.phone_number, json.dumps(user._asdict()))
                        for user in users_with_phone_number
                    ),
                )
                self.redis.pexpire(
                    self._k_users_by_phone_number(),
                    self.users_expiration_time_in_sec * 1000,
                )

    def store_user_in_space(self, user, ts, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Storing user ID {user.user_id} in space")
        self.redis.hset(self._k_users_in_space(), user.user_id, ts.as_int_timestamp())
        self.redis.hset(
            self._k_users_last_in_space(), user.user_id, ts.as_int_timestamp()
        )

    def get_users_last_in_space(self, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info("Getting all users last access to space")
        values = self.redis.hgetall(self._k_users_last_in_space())
        return [
            (Time.from_timestamp(int(value)), int(key)) for key, value in values.items()
        ]

    def user_left_space(self, user, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Removing user ID {user.user_id} from space")
        self.redis.hdel(self._k_users_in_space(), user.user_id)

    def remove_user_from_space(self, user_id, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Removing user ID {user_id} from space")
        self.redis.hdel(self._k_users_in_space(), user_id)

    def get_user_ids_in_space_with_timestamps(self, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info("Getting all users in space")
        values = self.redis.hgetall(self._k_users_in_space())
        return [
            (int(key), Time.from_timestamp(int(value))) for key, value in values.items()
        ]

    def store_pending_machine_activation(self, user_id, machine, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(
            f"Storing pending machine activation: user {user_id}, machine {machine}"
        )
        self.redis.setex(
            self._k_pending_machine_activation(machine),
            self.pending_machine_activation_timeout_in_sec,
            str(user_id),
        )

    def get_pending_machine_activation(self, machine, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Reading pending machine activation for machine {machine}")
        value = self.redis.get(self._k_pending_machine_activation(machine))
        return int(value) if value else None

    def set_machine_on(self, machine, user_id, ts, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Setting machine {machine} state ON, for user {user_id}")
        self.redis.set(
            self._k_machine_on(machine),
            json.dumps({"user_id": user_id, "ts": ts.as_int_timestamp()}),
        )
        self.redis.sadd(self._k_machines_on(), machine)

    def get_machine_on(self, machine, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Reading machine {machine} state")
        value = self.redis.get(self._k_machine_on(machine))
        if value:
            data = json.loads(value)
            data["ts"] = Time.from_timestamp(data["ts"])
            return data

    def set_machine_off(self, machine, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Setting machine {machine} state OFF")
        self.redis.delete(self._k_machine_on(machine))
        self.redis.srem(self._k_machines_on(), machine)

    def set_machine_state(self, machine, state, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Setting machine {machine} state {state}")
        self.redis.setex(
            self._k_machine_state(machine),
            self.machine_state_timeout_in_minutes * 60,
            state,
        )

    def get_machine_state(self, machine, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Getting machine {machine} state")
        value = self.redis.get(self._k_machine_state(machine))
        return value.decode("utf-8") if value else None

    def get_machines_on(self, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info("Reading ON machines")
        return [m.decode("utf-8") for m in self.redis.smembers(self._k_machines_on())]

    def set_space_open(self, is_open, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Setting space open {is_open}")
        self.redis.set(self._k_space_open(), str(is_open))

    def get_space_open(self, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info("Getting space open")
        value = self.redis.get(self._k_space_open())
        return value.decode("utf-8") == "True" if value else False

    def set_lights(self, room, lights_on, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f'Setting lights {room} {"ON" if lights_on else "OFF"}')
        if lights_on:
            self.redis.sadd(self._k_lights_on(), room)
        else:
            self.redis.srem(self._k_lights_on(), room)

    def get_lights_on(self, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info("Reading lights ON")
        return [m.decode("utf-8") for m in self.redis.smembers(self._k_lights_on())]

    def set_telegram_token(self, token, user_id, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Set Telegram token for user {user_id}")
        self.redis.setex(
            self._k_telegram_token(token),
            self.telegram_token_expiration_in_sec,
            str(user_id),
        )

    def get_user_id_by_telegram_token(self, token, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Get Telegram token {token}")
        value = self.redis.get(self._k_telegram_token(token))
        return int(value) if value else None

    def get_user_by_telegram_id(self, telegram_id, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Get user with Telegram ID {telegram_id}")
        data = self.redis.hget(self._k_users_by_telegram_id(), telegram_id)
        if data:
            return User(**json.loads(data))

    def get_user_by_phone_number(self, phone_number, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Get user with phone number {phone_number}")
        data = self.redis.hget(self._k_users_by_phone_number(), phone_number)
        if data:
            return User(**json.loads(data))

    def store_history_line(self, hl, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info(f"Storing history line of type {hl.__class__.__name__}")
        hl_id = make_random_string(10)
        self.redis.setex(
            self._k_history_line(hl_id),
            self.history_lines_expiration_in_days * 24 * 3600,
            json.dumps(history_line_to_json(hl)),
        )
        self.redis.sadd(self._k_history_lines(), hl_id)

    def get_all_history_lines(self, logger):
        logger = logger.getLogger(subsystem="redis")
        logger.info("Get all history lines")
        all_ids = [
            hl_id.decode("utf-8")
            for hl_id in self.redis.smembers(self._k_history_lines())
        ]
        ids_to_remove = []
        result = []
        for hl_id in all_ids:
            value = self.redis.get(self._k_history_line(hl_id))
            if value:
                result.append(json_to_history_line(json.loads(value)))
            else:
                ids_to_remove.append(hl_id)
        if len(ids_to_remove) > 0:
            self.redis.srem(self._k_history_lines(), *ids_to_remove)
        return result

    # -- Keys ----

    def _k_history_line(self, hl_id):
        return f"{self.key_prefix}:hl{hl_id}"

    def _k_history_lines(self):
        return f"{self.key_prefix}:hs"

    def _k_lights_on(self):
        return f"{self.key_prefix}:li"

    def _k_pending_machine_activation(self, machine):
        return f"{self.key_prefix}:ma{machine}"

    def _k_machines_by_id(self):
        return f"{self.key_prefix}:mc"

    def _k_machine_on(self, machine):
        return f"{self.key_prefix}:mo{machine}"

    def _k_machines_on(self):
        return f"{self.key_prefix}:ms"

    def _k_machine_state(self, machine):
        return f"{self.key_prefix}:mt{machine}"

    def _k_nudge(self, nudge_key):
        return f"{self.key_prefix}:nu{nudge_key}"

    def _k_space_open(self):
        return f"{self.key_prefix}:so"

    def _k_telegram_token(self, token):
        return f"{self.key_prefix}:tt{token}"

    def _k_users_by_id(self):
        return f"{self.key_prefix}:ui"

    def _k_users_last_in_space(self):
        return f"{self.key_prefix}:ul"

    def _k_users_by_phone_number(self):
        return f"{self.key_prefix}:up"

    def _k_users_in_space(self):
        return f"{self.key_prefix}:us"

    def _k_users_by_telegram_id(self):
        return f"{self.key_prefix}:ut"
