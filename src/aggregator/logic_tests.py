import unittest
from .database import MockDatabaseAdapter
from .logic import Aggregator
from .redis import RedisAdapter
from .clock import MockClock
from .logging import Logger, configure_logging
from .model import User, Machine
from .http_server import get_input_message_queue

# configure_logging()

STEFANO = User(1, 'Stefano', 'Masini', 'stefano@stefanomasini.com', '1234')

ALL_USERS = [
    STEFANO,
]

TABLE_SAW = Machine(1, 'Tablesaw', 'Table saw', 'tablesaw', 'tablesaw')

ALL_MACHINES = [
    TABLE_SAW,
]


class TestApplicationLogic(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None  # To see large JSON diffs
        self.logger = Logger(subsystem='root')
        self.database_adapter = MockDatabaseAdapter
        self.clock = MockClock()
        http_server_input_message_queue = get_input_message_queue()
        self.redis_adapter = RedisAdapter(self.clock, '127.0.0.1', 6379, 0, 'msl_aggregator_tests', 60, 90, 60, 60)
        self._delete_all_redis_keys()
        self.aggregator = Aggregator(
            MockDatabaseAdapter(ALL_USERS, ALL_MACHINES),
            self.redis_adapter,
            http_server_input_message_queue,
            self.clock,
            5,
        )
        self.aggregator.bot_logic.send_message.plug(self._send_bot_message)
        self.bot_messages = []

    def tearDown(self):
        self._delete_all_redis_keys()

    def _send_bot_message(self, chat_id, markdown, logger):
        self.bot_messages.append( (chat_id, markdown) )

    def _delete_all_redis_keys(self):
        keys = self.redis_adapter.redis.keys(self.redis_adapter.key_prefix + ':*')
        for key in keys:
            self.redis_adapter.redis.delete(key)

    def test_enter_and_leave_space(self):
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [])

        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [{
            'machines_on': [],
            'ts_checkin': '08:54:59 03/02/2019',
            'ts_checkin_human': 'a moment ago',
            'user': {'email': 'stefano@stefanomasini.com',
                     'first_name': 'Stefano',
                     'full_name': 'Stefano Masini',
                     'last_name': 'Masini',
                     'user_id': 1}}
        ])

        self.aggregator.user_left_space(STEFANO.user_id, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [])

    def test_stale_checkout_detection(self):
        # Check in at 11pm
        self.clock.set_time_of_day('23:00')
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)

        # After an hour (at midnight)
        self.clock.add(1, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [
            {
                'ts_checkin': '23:00:00 03/02/2019',
                'ts_checkin_human': 'an hour ago',
                'user': {
                    'email': 'stefano@stefanomasini.com',
                    'first_name': 'Stefano',
                    'full_name': 'Stefano Masini',
                    'last_name': 'Masini',
                    'user_id': 1,
                },
                'machines_on': [],
            },
        ])

        # At 5 am
        self.clock.add(5, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [
            {
                'ts_checkin': '23:00:00 03/02/2019',
                'ts_checkin_human': '6 hours ago',
                'user': {
                    'email': 'stefano@stefanomasini.com',
                    'first_name': 'Stefano',
                    'full_name': 'Stefano Masini',
                    'last_name': 'Masini',
                    'user_id': 1,
                },
                'machines_on': [],
            },
        ])

        # Detect stale checkins
        self.aggregator.clean_stale_user_checkins(self.logger)
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['users_in_space'], [])
        self.assertEqual(self.bot_messages, [
            ('1234', 'Did you forget to checkout yesterday?\nYou entered the Space at 23:00:00 03/02/2019'),
        ])

    def test_machine_on_and_off(self):
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['machines_on'], [])
        self.assertEqual(space_state['users_in_space'], [
            {
                'machines_on': [],
                'ts_checkin': '08:54:59 03/02/2019',
                'ts_checkin_human': 'a moment ago',
                'user': {'email': 'stefano@stefanomasini.com',
                         'first_name': 'Stefano',
                         'full_name': 'Stefano Masini',
                         'last_name': 'Masini',
                         'user_id': 1}
            }]
        )

        self.aggregator.user_activated_machine(STEFANO.user_id, 'tablesaw', self.logger)
        self.aggregator.machine_power('tablesaw', 'on', self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['machines_on'], [
            {
                'machine': {'name': 'Tablesaw', 'machine_id': 1}, 'ts': '08:54:59 03/02/2019', 'ts_human': 'a moment ago',
                'user': {'email': 'stefano@stefanomasini.com',
                         'first_name': 'Stefano',
                         'full_name': 'Stefano Masini',
                         'last_name': 'Masini',
                         'user_id': 1},
                }
        ])
        self.assertEqual(space_state['users_in_space'], [
            {'machines_on': [{'machine': {'name': 'Tablesaw', 'machine_id': 1}, 'ts': '08:54:59 03/02/2019', 'ts_human': 'a moment ago',
                                                 'user': {'email': 'stefano@stefanomasini.com',
                                                          'first_name': 'Stefano',
                                                          'full_name': 'Stefano Masini',
                                                          'last_name': 'Masini',
                                                          'user_id': 1},
                                                 }],
                                'ts_checkin': '08:54:59 03/02/2019',
                                'ts_checkin_human': 'a moment ago',
                                'user': {'email': 'stefano@stefanomasini.com',
                                         'first_name': 'Stefano',
                                         'full_name': 'Stefano Masini',
                                         'last_name': 'Masini',
                                         'user_id': 1}
             }
        ])

        self.aggregator.machine_power('tablesaw', 'off', self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['machines_on'], [])
        self.assertEqual(space_state['users_in_space'], [
            {
                'machines_on': [],
                'ts_checkin': '08:54:59 03/02/2019',
                'ts_checkin_human': 'a moment ago',
                'user': {'email': 'stefano@stefanomasini.com',
                         'first_name': 'Stefano',
                         'full_name': 'Stefano Masini',
                         'last_name': 'Masini',
                         'user_id': 1}}
        ])

    def test_space_open_and_closed(self):
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['space_open'], False)

        self.aggregator.space_open(True, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['space_open'], True)

        self.aggregator.space_open(False, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['space_open'], False)

    def test_lights_on_and_off(self):
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['lights_on'], [])

        self.aggregator.lights('large_room', True, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['lights_on'], [{
            'label': 'large_room',
            'name': 'Large room',
        }])

        self.aggregator.lights('large_room', False, self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state['lights_on'], [])
