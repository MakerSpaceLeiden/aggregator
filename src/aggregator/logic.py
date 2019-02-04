
class Aggregator(object):
    def __init__(self, mysql_adapter, redis_adapter, notifications_queue, clock, checkin_stale_after_hours):
        self.mysql_adapter = mysql_adapter
        self.redis_adapter = redis_adapter
        self.notifications_queue = notifications_queue
        self.clock = clock
        self.checkin_stale_after_hours = checkin_stale_after_hours

    def _get_user_by_id(self, user_id, logger):
        user = self.redis_adapter.get_user_by_id(user_id, logger)
        if not user:
            all_users = self.mysql_adapter.get_all_users(logger)
            self.redis_adapter.set_users_by_ids(all_users, logger)
            filtered_users = [u for u in all_users if u.user_id == user_id]
            if len(filtered_users) == 1:
                user = filtered_users[0]
        return user

    def get_tags(self, logger):
        return self.mysql_adapter.get_all_tags(logger)

    def user_entered_space_door(self, user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user = self._get_user_by_id(user_id, logger)
        if not user:
            raise Exception(f'User ID {user_id} not found in database')
        logger.info(f'user_entered_space_door: {user.full_name}')
        self.redis_adapter.store_user_in_space(user, self.clock.now(), logger)
        self.notifications_queue.send_message(msg_type='user_entered_space')

    def get_space_state_for_json(self, logger):
        logger = logger.getLogger(subsystem='aggregator')
        data = self.redis_adapter.get_user_ids_in_space_with_timestamps(logger)
        users = [(self._get_user_by_id(user_id, logger), ts_checkin) for user_id, ts_checkin in data]
        users.sort(key=lambda checkin: -checkin[1].sorting_key())
        return {
            'machines_on': [self._get_machine_state(machine, logger) for machine in self.redis_adapter.get_machines_on(logger)],
            'users_in_space': [{
                'user': user.for_json() if user else None,
                'ts_checkin': ts_checkin.human_str(),
                'ts_checkin_human': ts_checkin.human_delta_from(self.clock.now()),
                'machines_on': [self._get_machine_state(machine, logger) for machine in self.redis_adapter.get_machines_on_for_user_id(user.user_id, logger)],
            } for user, ts_checkin in users],
        }

    def _get_machine_state(self, machine, logger):
        state = self.redis_adapter.get_machine_on(machine, logger)
        user = None
        if state:
            user = self._get_user_by_id(state['user_id'], logger)
        return {
            'machine': machine,
            'ts': state['ts'] if state else None,
            'user': user.for_json() if user else None,
        }

    def clean_stale_user_checkins(self, logger):
        logger = logger.getLogger(subsystem='aggregator')
        logger.info('Checking for stale users')
        users = self.redis_adapter.get_user_ids_in_space_with_timestamps(logger)
        now = self.clock.now()
        for user_id, ts_checkin in users:
            elapsed_time_in_hours = now.delta_in_hours(ts_checkin)
            if elapsed_time_in_hours > self.checkin_stale_after_hours:
                self._check_out_stale_user(user_id, elapsed_time_in_hours, logger)

    def _check_out_stale_user(self, user_id, elapsed_time_in_hours, logger):
        user = self._get_user_by_id(user_id, logger)
        logger.info(f'Checking out stale user {user.full_name if user else user_id} after {int(elapsed_time_in_hours)} hours')
        self.redis_adapter.remove_user_from_space(user_id, logger)

    def user_activated_machine(self, user_id, machine, logger):
        user = self._get_user_by_id(user_id, logger)
        logger.info(f'User {user.full_name if user else user_id} activated machine {machine}')
        self.redis_adapter.store_pending_machine_activation(user_id, machine, logger)

    def machine_power(self, machine, state, logger):
        if state == 'on':
            user_id = self.redis_adapter.get_pending_machine_activation(machine, logger)
            if not user_id:
                logger.error(f'Machine {machine} started without pending activation')
            else:
                user = self._get_user_by_id(user_id, logger)
                logger.info(f'User {user.full_name if user else user_id} turning on machine {machine}')
                now = self.clock.now()
                self.redis_adapter.set_machine_on(machine, user_id, now, logger)
        else:
            assert state == 'off'
            state = self.redis_adapter.get_machine_on(machine, logger)
            if not state:
                logger.error(f'Machine {machine} turned off without corresponding ON record')
            else:
                logger.info(f'Turning off machine {machine}')
                self.redis_adapter.set_machine_off(machine, state['user_id'], logger)


