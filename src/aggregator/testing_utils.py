import unittest
from collections import defaultdict

from .clock import MockClock
from .logging import configure_logging_for_tests
from .logic import Aggregator
from .model import Machine, User
from .redis import RedisAdapter
from .timed_tasks import TaskScheduler

STEFANO = User(
    user_id=1,
    first_name="Stefano",
    last_name="Masini",
    email="stefano@stefanomasini.com",
    telegram_user_id="1234",
    phone_number="+316123456",
    uses_signal=True,
    always_uses_email=True,
)

BOB = User(
    user_id=2,
    first_name="Bob",
    last_name="de Bouwer",
    email="bob@bouwer.com",
    telegram_user_id="2345",
    phone_number="+316456789",
    uses_signal=True,
    always_uses_email=True,
)

ALL_USERS = [
    STEFANO,
    BOB,
]

TABLE_SAW = Machine(1, "Tablesaw", "Table saw", "tablesaw", "tablesaw", "Wood workshop")

ALL_MACHINES = [
    TABLE_SAW,
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


class MockCrmAdapter(object):
    def __init__(self):
        pass

    def user_checkin(self, user_id, logger):
        pass

    def user_checkout(self, user_id, logger):
        pass


class AggregatorBaseTestSuite(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # To see large JSON diffs
        self.logger = configure_logging_for_tests()
        self.clock = MockClock()
        http_server_input_message_queue = MockeHttpServerInputMessageQueue()
        self.redis_adapter = RedisAdapter(
            self.clock,
            "127.0.0.1",
            6379,
            0,
            "msl_aggregator_tests",
            60,
            90,
            60,
            60,
            7,
        )
        self.crm_adapter = MockCrmAdapter()
        self._delete_all_redis_keys()
        self.task_scheduler = TaskScheduler(self.clock, self.logger)
        self.db = MockDatabaseAdapter(self)
        self.aggregator = Aggregator(
            self.db,
            self.redis_adapter,
            self.crm_adapter,
            http_server_input_message_queue,
            self.clock,
            self,
            self.task_scheduler,
            5,
        )
        self.aggregator.signal_bot = self
        self.bot_messages = []
        self.emails_sent = []
        self.bot_notification_objects = []
        self.volunteers = defaultdict(list)

    def tearDown(self):
        self._delete_all_redis_keys()

    def _delete_all_redis_keys(self):
        keys = self.redis_adapter.redis.keys(self.redis_adapter.key_prefix + ":*")
        for key in keys:
            self.redis_adapter.redis.delete(key)

    def send_notification(self, user, notification, logger):
        self.assertNotEqual(notification.get_text(), "")
        self.assertNotEqual(notification.get_markdown(), "")
        self.assertNotEqual(notification.get_email_text(), "")
        self.assertNotEqual(notification.get_subject_for_email(), "")
        self.bot_messages.append((user.user_id, notification.__class__.__name__))
        self.bot_notification_objects.append(notification)
        chat_id = f"signal-{user.phone_number}"
        return chat_id

    def send_email_to_user(self, user, message, logger):
        self.emails_sent.append((user.user_id, message.__class__.__name__))

    def send_email(self, name, email, message, logger):
        self.emails_sent.append((name, email, message.__class__.__name__))

    def send_bot_message(self, user, message):
        reply = self.aggregator.handle_bot_message(
            f"signal-{user.phone_number}", user, message, self.logger
        )
        if not reply:
            raise Exception("Missing reply from BOT logic")
        else:
            self.send_notification(user, reply, self.logger)
