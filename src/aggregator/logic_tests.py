import unittest
from .database import MockDatabaseAdapter
from .logic import Aggregator
from .redis import RedisAdapter
from .clock import MockClock
from .logging import Logger, configure_logging
from .model import User
from .http_server import get_input_message_queue

# configure_logging()

STEFANO = User(1, 'Stefano', 'Masini', 'stefano@stefanomasini.com')

ALL_USERS = [
    STEFANO,
]


class TestStringMethods(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None  # To see large JSON diffs
        self.logger = Logger(subsystem='root')
        self.database_adapter = MockDatabaseAdapter
        self.clock = MockClock()
        http_server_input_message_queue = get_input_message_queue()
        redis_adapter = RedisAdapter(self.clock, '127.0.0.1', 6379, 0, 'msl_aggregator_tests', 60, 90)
        self._delete_all_redis_keys(redis_adapter)
        self.aggregator = Aggregator(
            MockDatabaseAdapter(ALL_USERS),
            redis_adapter,
            http_server_input_message_queue,
            self.clock,
            5,
        )

    def _delete_all_redis_keys(self, redis_adapter):
        keys = redis_adapter.redis.keys(redis_adapter.key_prefix + ':*')
        for key in keys:
            redis_adapter.redis.delete(key)

    def test_stale_checkout_detection(self):
        # Check in at 11pm
        self.clock.set_time_of_day('23:00')
        self.aggregator.user_entered_space_door(STEFANO.user_id, self.logger)

        # After an hour (at midnight)
        self.clock.add(1, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {
            'machines_on': [],
            'users_in_space': [{
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
            ]}
        )

        # At 5 am
        self.clock.add(5, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {
            'machines_on': [],
            'users_in_space': [{
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
            ]}
        )

        # Detect stale checkins
        self.aggregator.clean_stale_user_checkins(self.logger)
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {'machines_on': [], 'users_in_space': []})

    def test_machine_on_and_off(self):
        self.aggregator.user_entered_space_door(STEFANO.user_id, self.logger)
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {
            'machines_on': [],
            'users_in_space': [{'machines_on': [],
                                'ts_checkin': '08:54:59 03/02/2019',
                                'ts_checkin_human': 'a moment ago',
                                'user': {'email': 'stefano@stefanomasini.com',
                                         'first_name': 'Stefano',
                                         'full_name': 'Stefano Masini',
                                         'last_name': 'Masini',
                                         'user_id': 1}}]
            }
        )

        self.aggregator.user_activated_machine(STEFANO.user_id, 'tablesaw', self.logger)
        self.aggregator.machine_power('tablesaw', 'on', self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {
         'machines_on': [{'machine': 'tablesaw', 'ts': 1549180499,
                          'user': {'email': 'stefano@stefanomasini.com',
                                   'first_name': 'Stefano',
                                   'full_name': 'Stefano Masini',
                                   'last_name': 'Masini',
                                   'user_id': 1},
                          }],
         'users_in_space': [{'machines_on': [{'machine': 'tablesaw', 'ts': 1549180499,
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
                                      'user_id': 1}}]}
        )

        self.aggregator.machine_power('tablesaw', 'off', self.logger)

        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {
         'machines_on': [],
         'users_in_space': [{'machines_on': [],
                             'ts_checkin': '08:54:59 03/02/2019',
                             'ts_checkin_human': 'a moment ago',
                             'user': {'email': 'stefano@stefanomasini.com',
                                      'first_name': 'Stefano',
                                      'full_name': 'Stefano Masini',
                                      'last_name': 'Masini',
                                      'user_id': 1}}]}
        )