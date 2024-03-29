# This is where the main business logic lives.

import random
from functools import partial
from collections import defaultdict, namedtuple
from .model import ALL_LIGHTS, history_line_to_json, get_history_line_description, UserEntered, UserLeft
from .messages import MessageHelp, BASIC_COMMANDS, \
    StaleCheckoutNotification, MachineLeftOnNotification, ProblemsLeavingSpaceNotification, TestNotification, \
    ProblemMachineLeftOnByUser, ProblemMachineLeftOnBySomeoneElse, ProblemSpaceLeftOpen, ProblemLightLeftOn
from .bots.bot_logic import BotLogic
from .urls import Urls
from .chores.chores_logic import ChoresLogic, NudgesParams


class Aggregator(object):
    def __init__(self,
                 database_adapter, redis_adapter, notifications_queue, clock, email_adapter, task_scheduler, checkin_stale_after_hours,
                 chores_timeframe_in_days, chores_warnings_check_window_in_hours, chores_message_users_seen_no_later_than_days):
        self.database_adapter = database_adapter
        self.redis_adapter = redis_adapter
        self.notifications_queue = notifications_queue
        self.clock = clock
        self.checkin_stale_after_hours = checkin_stale_after_hours
        self.chores_timeframe_in_days = chores_timeframe_in_days
        self.chores_warnings_check_window_in_hours = chores_warnings_check_window_in_hours
        self.chores_message_users_seen_no_later_than_days = chores_message_users_seen_no_later_than_days
        self.email_adapter = email_adapter
        self.task_scheduler = task_scheduler
        self.bot_logic = BotLogic(self)
        self.telegram_bot = None
        self.signal_bot = None
        self.urls = Urls()

    def _get_user_by_id(self, user_id, logger):
        user = self.redis_adapter.get_user_by_id(user_id, logger)
        if not user:
            all_users = self.database_adapter.get_all_users(logger)
            self.redis_adapter.set_users_by_ids(all_users, logger)
            filtered_users = [u for u in all_users if u.user_id == user_id]
            if len(filtered_users) == 1:
                user = filtered_users[0]
        return user

    def _get_machine_by_name(self, machine_name, logger):
        machine = self.redis_adapter.get_machine_by_name(machine_name, logger)
        if not machine:
            all_machines = self.database_adapter.get_all_machines(logger)
            self.redis_adapter.set_all_machines(all_machines, logger)
            filtered_machines = [m for m in all_machines if m.node_machine_name == machine_name]
            if len(filtered_machines) == 1:
                machine = filtered_machines[0]
        return machine

    def _get_all_machines(self, logger):
        machines = self.redis_adapter.get_all_machines(logger)
        if not machines:
            machines = self.database_adapter.get_all_machines(logger)
            self.redis_adapter.set_all_machines(machines, logger)
        machines.sort(key=lambda m: (m.location_name or '', m.name or ''))
        return machines

    # --------------------------------------------------

    def make_new_telegram_association_for_user(self, current_user, connection_token, telegram_id, logger):
        if current_user:
            # Clear current association (if there is one)
            self.delete_telegram_id_for_user(current_user.user_id, logger)
        connecting_user = self.register_user_by_telegram_token(connection_token, telegram_id, logger)
        return connecting_user

    def get_user_by_telegram_id(self, telegram_id, logger):
        user = self.redis_adapter.get_user_by_telegram_id(telegram_id, logger)
        if not user:
            all_users = self.database_adapter.get_all_users(logger)
            self.redis_adapter.set_users_by_ids(all_users, logger)
            filtered_users = [u for u in all_users if u.telegram_user_id == telegram_id]
            if len(filtered_users) == 1:
                user = filtered_users[0]
        return user

    def get_user_by_phone_number(self, phone_number, logger):
        user = self.redis_adapter.get_user_by_phone_number(phone_number, logger)
        if not user:
            all_users = self.database_adapter.get_all_users(logger)
            self.redis_adapter.set_users_by_ids(all_users, logger)
            filtered_users = [u for u in all_users if u.phone_number == phone_number]
            if len(filtered_users) == 1:
                user = filtered_users[0]
        return user

    def get_tags(self, logger):
        return self.database_adapter.get_all_tags(logger)

    def user_entered_space(self, user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user = self._get_user_by_id(user_id, logger)
        if not user:
            raise Exception(f'User ID {user_id} not found in database')
        logger.info(f'user_entered_space: {user.full_name}')
        now = self.clock.now()
        self.redis_adapter.store_user_in_space(user, now, logger)
        self.notifications_queue.send_message(msg_type='user_entered_space')
        self.redis_adapter.store_history_line(UserEntered(user_id, now, user.first_name, user.last_name), logger)

    def user_left_space(self, user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user = self._get_user_by_id(user_id, logger)
        if not user:
            raise Exception(f'User ID {user_id} not found in database')
        logger.info(f'user_left_space: {user.full_name}')
        self.redis_adapter.user_left_space(user, logger)
        self.redis_adapter.store_history_line(UserLeft(user_id, self.clock.now(), user.first_name, user.last_name), logger)
        users_still_in_space = self.redis_adapter.get_user_ids_in_space_with_timestamps(logger)
        is_last_user_leaving = len(users_still_in_space) == 0
        self._user_leave_checks(user, is_last_user_leaving, logger)

    def _user_leave_checks(self, user, is_last_user_leaving, logger):
        problems = []

        # Check machines left on
        all_machines_states = self._get_machines_on_for_json(logger)
        for machine_state in all_machines_states:
            if machine_state['user'] and machine_state['user']['user_id'] == user.user_id:
                problems.append(ProblemMachineLeftOnByUser(machine_state['machine']['name']))
            elif is_last_user_leaving:
                problems.append(ProblemMachineLeftOnBySomeoneElse(machine_state['machine']['name']))

        # When space remains empty
        if is_last_user_leaving:
            # Check big switch
            # space_open = self.redis_adapter.get_space_open(logger)
            # if is_last_user_leaving and space_open:
            #     problems.append(ProblemSpaceLeftOpen())

            # Check lights
            lights_on = self.redis_adapter.get_lights_on(logger)
            for light in ALL_LIGHTS:
                if light.label in lights_on:
                    problems.append(ProblemLightLeftOn(light))

        if len(problems) > 0:
            self.send_user_notification(user, ProblemsLeavingSpaceNotification(user, self.clock.now(), problems, is_last_user_leaving), logger)

    def is_user_id_in_space(self, user_id, logger):
        for user_id_in_space, ts_checkin in self.redis_adapter.get_user_ids_in_space_with_timestamps(logger):
            if user_id_in_space == user_id:
                return True, ts_checkin
        return False, None

    def check_expired_machine_state(self, logger):
        logger = logger.getLogger(subsystem='aggregator')
        for machine in self.redis_adapter.get_machines_on(logger):
            machine_state = self.redis_adapter.get_machine_state(machine, logger)
            state_machine_on = self.redis_adapter.get_machine_on(machine, logger)
            if state_machine_on and not machine_state:
                logger.info('Machine {0} ON state expired. Cable must have been disconnected. Setting to off.')
                self.redis_adapter.set_machine_off(machine, logger)

    def get_space_state_for_json(self, logger):
        logger = logger.getLogger(subsystem='aggregator')
        data = self.redis_adapter.get_user_ids_in_space_with_timestamps(logger)
        users = [(self._get_user_by_id(user_id, logger), ts_checkin) for user_id, ts_checkin in data]
        users.sort(key=lambda checkin: -checkin[1].sorting_key())
        all_machines = self._get_all_machines(logger)
        all_machines_states = self._get_machines_on_for_json(logger)
        machines_on_by_user = defaultdict(list)
        for state in all_machines_states:
            if state.get('user', None) and state['user'].get('user_id', None):
                machines_on_by_user[state['user']['user_id']].append(state)
        lights_on = self.redis_adapter.get_lights_on(logger)
        all_history_lines = self.redis_adapter.get_all_history_lines(logger)
        all_history_lines.sort(key=lambda hl: hl.ts)
        return {
            'lights_on': [light.for_json() for light in ALL_LIGHTS if light.label in lights_on],
            'space_open': self.redis_adapter.get_space_open(logger),
            'machines_on': all_machines_states,
            'machines': [self._get_machine_state(machine, logger) for machine in all_machines],
            'history': [self._get_history_line_for_json(hl) for hl in all_history_lines],
            'users_in_space': [{
                'user': user.for_json(),
                'ts_checkin': ts_checkin.human_str(),
                'ts_checkin_human': ts_checkin.human_delta_from(self.clock.now()),
                'machines_on': machines_on_by_user.get(user.user_id, []),
            } for user, ts_checkin in users if user],
        }

    def _get_machines_on_for_json(self, logger):
        all_machines_states = [self._get_machine_onoff_state(machine, logger) for machine in self.redis_adapter.get_machines_on(logger)]
        all_machines_states = [ms for ms in all_machines_states if ms]
        return all_machines_states

    def _get_history_line_for_json(self, hl):
        data = history_line_to_json(hl)
        data['description'] = get_history_line_description(hl)
        return data

    def _get_machine_state(self, machine, logger):
        state = self.redis_adapter.get_machine_state(machine.node_machine_name, logger)
        return {
            'machine': {
                'name': machine.name,
                'machine_id': machine.machine_id,
                'location_name': machine.location_name or '',
            },
            'state': state if state else 'off',
        }

    def _get_machine_onoff_state(self, machine_name, logger):
        state = self.redis_adapter.get_machine_on(machine_name, logger)
        user = None
        if state:
            user = self._get_user_by_id(state['user_id'], logger)
        if not user:
            return None
        machine = self._get_machine_by_name(machine_name, logger)
        if not machine:
            return None
        return {
            'machine': {
                'name': machine.name,
                'machine_id': machine.machine_id,
            },
            'ts': state['ts'].human_str() if state else None,
            'ts_human': state['ts'].human_delta_from(self.clock.now()) if state else None,
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
                self._check_out_stale_user(user_id, ts_checkin, elapsed_time_in_hours, logger)

    def _check_out_stale_user(self, user_id, ts_checkin, elapsed_time_in_hours, logger):
        user = self._get_user_by_id(user_id, logger)
        logger.info(f'Checking out stale user {user.full_name if user else user_id} after {int(elapsed_time_in_hours)} hours')
        self.redis_adapter.remove_user_from_space(user_id, logger)
        notification = StaleCheckoutNotification(user, ts_checkin, self.urls.notification_settings(), self.urls.space_state())
        self.task_scheduler.schedule_task_at_time(self.clock.now().replace(hour=8, minute=0), partial(self.send_user_notification, user, notification), logger)

    def send_user_notification(self, user, notification, logger):
        if self.telegram_bot and user.uses_telegram_bot():
            chat_id = None
            try:
                chat_id = self.telegram_bot.send_notification(user, notification, logger)
            except:
                logger.exception('Unexpected exception when trying to notify user via Telegram')
            if chat_id:
                notification.set_chat_state(chat_id, self.bot_logic)
        if self.signal_bot and user.uses_signal_bot():
            chat_id = None
            try:
                chat_id = self.signal_bot.send_notification(user, notification, logger)
            except:
                logger.exception('Unexpected exception when trying to notify user via Signal')
            if chat_id:
                notification.set_chat_state(chat_id, self.bot_logic)
        if user.uses_email():
            try:
                self.email_adapter.send_email_to_user(user, notification, logger)
            except:
                logger.exception('Unexpected exception when trying to notify user via email')

    def user_activated_machine(self, user_id, machine, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user = self._get_user_by_id(user_id, logger)
        logger.info(f'User {user.full_name if user else user_id} activated machine {machine}')
        self.redis_adapter.store_pending_machine_activation(user_id, machine, logger)

    def machine_power(self, machine, state, logger):
        logger = logger.getLogger(subsystem='aggregator')
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
                self.redis_adapter.set_machine_off(machine, logger)

    def space_open(self, is_open, logger):
        logger = logger.getLogger(subsystem='aggregator')
        self.redis_adapter.set_space_open(is_open, logger)

    def lights(self, room, state, logger):
        logger = logger.getLogger(subsystem='aggregator')
        self.redis_adapter.set_lights(room, state, logger)

    def create_telegram_connect_token(self, user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        token = str(random.randint(10**20, 10**21))
        self.redis_adapter.set_telegram_token(token, user_id, logger)
        return token

    def register_user_by_telegram_token(self, token, telegram_user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user_id = self.redis_adapter.get_user_id_by_telegram_token(token, logger)
        if user_id:
            user = self._get_user_by_id(user_id, logger)
            logger.info(f'Registering user {user_id} with Telegram User ID {telegram_user_id}')
            self.database_adapter.store_telegram_user_id_for_user_id(telegram_user_id, user.user_id, logger)
            return user

    def delete_telegram_id_for_user(self, user_id, logger):
        self.database_adapter.delete_telegram_user_id_for_user_id(user_id, logger)
        all_users = self.database_adapter.get_all_users(logger)
        self.redis_adapter.set_users_by_ids(all_users, logger)

    def handle_bot_message(self, chat_id, user, message, logger):
        return self.bot_logic.handle_message(chat_id, user, message, logger)

    def handle_new_bot_conversation(self, chat_id, user, message, logger):
        return self.bot_logic.handle_new_conversation(chat_id, user, message, logger)

    def onboard_new_signal_user(self, user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user = self._get_user_by_id(user_id, logger)
        if self.signal_bot:
            self.signal_bot.send_notification(user, MessageHelp(user, BASIC_COMMANDS), logger)

    def send_notification_test(self, user_id, logger):
        logger = logger.getLogger(subsystem='aggregator')
        user = self._get_user_by_id(user_id, logger)
        self.send_user_notification(user, TestNotification(user), logger)

    def machine_state(self, machine, state, logger):
        if state == 'ready':
            state_on = self.redis_adapter.get_machine_on(machine, logger)
            if state_on:
                self._warn_user_of_machine_left_on(machine, state_on['user_id'], logger)
                self.redis_adapter.set_machine_off(machine, logger)
        self.redis_adapter.set_machine_state(machine, state, logger)

    def _warn_user_of_machine_left_on(self, machine_name, user_id, logger):
        user = self._get_user_by_id(user_id, logger)
        logger.info(f'Warning user {user.full_name if user else user_id} that machine {machine_name} was left on')
        if user:
            machine = self._get_machine_by_name(machine_name, logger)
            self.send_user_notification(user, MachineLeftOnNotification(machine), logger)

    def _get_chores_logic(self, logger):
        try:
           logger.info('ok 1')
           return ChoresLogic(self.database_adapter.get_all_chores(logger))
           logger.info('ok 2')
        except Exception as e:
           logger.exception('Unexpected exception {}'.format(e))

    def get_chores_for_json(self, logger):
        try:
           logger.info('ok 3')
           chores_logic = self._get_chores_logic(logger)
           now = self.clock.now()
           events = chores_logic.get_events_from_to(now, now.add(self.chores_timeframe_in_days, 'days'))
        except Exception as e:
           logger.exception('Unexpected exception {}'.format(e))

        logger.info(events)
        return {
            'events': [event.for_json() for event in events],
        }

    def get_users_seen_no_later_than_days(self, num_days, logger):
        ts_and_users = self.redis_adapter.get_users_last_in_space(logger)
        threshold = self.clock.now().add(-num_days, 'days')
        return [self._get_user_by_id(user_id, logger) for ts, user_id in ts_and_users if ts > threshold]

    def send_warnings_for_chores(self, logger):
        logger = logger.getLogger(subsystem='aggregator')
        chores_logic = self._get_chores_logic(logger)
        now = self.clock.now()
        for event in chores_logic.iter_events_with_reminders_from_to(now.add(-self.chores_warnings_check_window_in_hours, 'hours'), now):
            volunteers = self.database_adapter.get_chore_volunteers_for_event(event, logger)
            params = NudgesParams(
                volunteers,
                now,
                self.urls,
                self.chores_message_users_seen_no_later_than_days,
            )
            for nudge in event.iter_nudges(params):
                logger.info('Processing Chore nudge: {0}'.format(nudge))
                if not self.redis_adapter.nudge_has_been_processed(nudge, logger):
                    nudge.send(self, logger)
                    self.redis_adapter.store_nudge_marker(nudge, logger)

    def user_volunteers_for_event(self, user_id, event, logger):
        user = self._get_user_by_id(user_id, logger)
        if not user:
            raise Exception(f'User not found with ID {user_id}')
        volunteers = self.database_adapter.get_chore_volunteers_for_event(event, logger)
        if len(volunteers) >= event.chore.min_required_people:
            # No need for more volunteers
            return False
        self.database_adapter.add_chore_volunteer_for_event(event, user, logger)
        return True
