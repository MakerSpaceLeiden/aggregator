import unittest
from collections import defaultdict

from .logic import Aggregator
from .redis import RedisAdapter
from .clock import MockClock
from .logging import configure_logging_for_tests
from .model import User, Machine, Chore
from .timed_tasks import TaskScheduler


STEFANO = User(
    user_id = 1,
    first_name = 'Stefano',
    last_name = 'Masini',
    email = 'stefano@stefanomasini.com',
    telegram_user_id = '1234',
    phone_number = '+316123456',
    uses_signal = True,
    always_uses_email = True,
)

BOB = User(
    user_id = 2,
    first_name = 'Bob',
    last_name = 'de Bouwer',
    email = 'bob@bouwer.com',
    telegram_user_id = '2345',
    phone_number = '+316456789',
    uses_signal = True,
    always_uses_email = True,
)

ALL_USERS = [
    STEFANO,
    BOB,
]

TABLE_SAW = Machine(1, 'Tablesaw', 'Table saw', 'tablesaw', 'tablesaw', 'Wood workshop')

ALL_MACHINES = [
    TABLE_SAW,
]


EMPTY_TRASH = Chore(1, 'Empty trash', 'Empty trash every 2 weeks', 'BasicChore', {
    'min_required_people': 2,
    'first_tuesday': '26/2/2019 7:30',
    'reminders': [{
        'reminder_type': 'missing_volunteers',
        'when': {
            'days_before': 3,
            'time': '17:00',
        },
        'nudges': [{
            'nudge_type': 'email',
            'nudge_key': 'gentle_email_reminder',
            'destination': 'deelnemers@mailing.list',
            'subject_template': 'Volunteers needed for {event_day}, {chore_description}',
            'body_template': 'Hello, we need {num_volunteers_needed} volunteers for {event_day}, {chore_description}. Click here {signup_url}',
        }],
    }, {
        'reminder_type': 'missing_volunteers',
        'when': {
            'days_before': 2,
            'time': '17:00',
        },
        'nudges': [{
            'nudge_type': 'email',
            'nudge_key': 'hard_email_reminder',
            'destination': 'deelnemers@mailing.list',
            'subject_template': 'Volunteers WANTED for {event_day}, {chore_description}',
            'body_template': 'Hello, we need {num_volunteers_needed} volunteers for {event_day}, {chore_description}. Click here {signup_url}',
        }, {
            'nudge_type': 'volunteer_via_chat_bot',
            'nudge_key': 'volunteer_via_chat_bot',
        }],
    }, {
        'reminder_type': 'volunteers_who_signed_up',
        'when': {
            'days_before': 1,
            'time': '19:00',
        },
    }],
})

ALL_CHORES = [
    EMPTY_TRASH,
]


class MockeHttpServerInputMessageQueue(object):
    def send_message(self, **kwargs):
        pass


class MockDatabaseAdapter(object):
    def __init__(self, test_suite):
        self.test_suite = test_suite

    def get_all_users(self, logger):
        return ALL_USERS

    def get_all_machines(self, logger):
        return ALL_MACHINES

    def get_all_chores(self, logger):
        return ALL_CHORES

    def get_chore_volunteers_for_event(self, event, logger):
        return self.test_suite.get_chore_volunteers_for_event(event)

    def add_chore_volunteer_for_event(self, event, user, logger):
        self.test_suite.add_chore_volunteer_for_event(event, user)


class AggregatorBaseTestSuite(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # To see large JSON diffs
        self.logger = configure_logging_for_tests()
        self.clock = MockClock()
        http_server_input_message_queue = MockeHttpServerInputMessageQueue()
        self.redis_adapter = RedisAdapter(self.clock, 2, '127.0.0.1', 6379, 0, 'msl_aggregator_tests', 60, 90, 60, 60, 7)
        self._delete_all_redis_keys()
        self.task_scheduler = TaskScheduler(self.clock, self.logger)
        self.db = MockDatabaseAdapter(self)
        self.aggregator = Aggregator(
            self.db,
            self.redis_adapter,
            http_server_input_message_queue,
            self.clock,
            self,
            self.task_scheduler,
            5,
            90,
            2,
            14,
        )
        self.aggregator.signal_bot = self
        self.bot_messages = []
        self.emails_sent = []
        self.bot_notification_objects = []
        self.volunteers = defaultdict(list)

    def tearDown(self):
        self._delete_all_redis_keys()

    def _delete_all_redis_keys(self):
        keys = self.redis_adapter.redis.keys(self.redis_adapter.key_prefix + ':*')
        for key in keys:
            self.redis_adapter.redis.delete(key)

    def get_chore_volunteers_for_event(self, event):
        key = '{chore_id}-{ts}'.format(**event.get_object_key())
        return self.volunteers[key]

    def add_chore_volunteer_for_event(self, event, user):
        key = '{chore_id}-{ts}'.format(**event.get_object_key())
        return self.volunteers[key].append(user)

    def send_notification(self, user, notification, logger):
        self.assertNotEqual(notification.get_text(), '')
        self.assertNotEqual(notification.get_markdown(), '')
        self.assertNotEqual(notification.get_email_text(), '')
        self.assertNotEqual(notification.get_subject_for_email(), '')
        self.bot_messages.append( (user.user_id, notification.__class__.__name__) )
        self.bot_notification_objects.append(notification)
        chat_id = f'signal-{user.phone_number}'
        return chat_id

    def send_email_to_user(self, user, message, logger):
        self.emails_sent.append((user.user_id, message.__class__.__name__))

    def send_email(self, name, email, message, logger):
        self.emails_sent.append((name, email, message.__class__.__name__))

    def send_bot_message(self, user, message):
        reply = self.aggregator.handle_bot_message(f'signal-{user.phone_number}', user, message, self.logger)
        if not reply:
            raise Exception('Missing reply from BOT logic')
        else:
            self.send_notification(user, reply, self.logger)

