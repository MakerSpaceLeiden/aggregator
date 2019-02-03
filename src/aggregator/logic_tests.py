import unittest
from .database import MockDatabaseAdapter
from .logic import Aggregator
from .redis import MockRedisAdapter
from .clock import MockClock
from .logging import Logger
from .model import User
from .http_server import get_input_message_queue


STEFANO = User(1, 'Stefano', 'Masini', 'stefano@stefanomasini.com')

ALL_USERS = [
    STEFANO,
]


class TestStringMethods(unittest.TestCase):

    def setUp(self):
        self.logger = Logger(subsystem='root')
        self.database_adapter = MockDatabaseAdapter
        self.clock = MockClock()
        http_server_input_message_queue = get_input_message_queue()
        self.aggregator = Aggregator(
            MockDatabaseAdapter(ALL_USERS),
            MockRedisAdapter(self.clock),
            http_server_input_message_queue,
            self.clock,
            5,
        )

    def test_stale_checkout_detection(self):
        # Check in at 11pm
        self.clock.set_time_of_day('23:00')
        self.aggregator.user_entered_space_door(STEFANO.user_id, self.logger)

        # After an hour (at midnight)
        self.clock.add(1, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {
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
            },
            ]}
        )

        # At 5 am
        self.clock.add(5, 'hour')
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, {
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
            },
            ]}
        )

        # Detect stale checkins
        self.aggregator.clean_stale_user_checkins(self.logger)
        space_state = self.aggregator.get_space_state_for_json(self.logger)
        self.assertEqual(space_state, { 'users_in_space': [] })

