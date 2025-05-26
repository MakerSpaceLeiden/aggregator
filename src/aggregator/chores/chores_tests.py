from ..testing_utils import STEFANO, AggregatorBaseTestSuite


class TestChores(AggregatorBaseTestSuite):
    def test_sending_all_reminders(self):
        self.clock.set_day_and_time("20/2/2019 8:0")
        self.aggregator.user_entered_space(STEFANO.user_id, self.logger)

        # No nudges before the gentle reminder threshold
        self.clock.set_day_and_time("23/2/2019 16:59")
        self.aggregator.send_warnings_for_chores(self.logger)
        self.assertEqual(self.emails_sent, [])

        # Email nudge after the gentle reminder threshold
        self.clock.set_day_and_time("23/2/2019 17:01")
        self.aggregator.send_warnings_for_chores(self.logger)
        self.assertEqual(
            self.emails_sent,
            [("deelnemers@mailing.list", "deelnemers@mailing.list", "EmailNudge")],
        )
        self.emails_sent = []

        # No double nudges
        self.aggregator.send_warnings_for_chores(self.logger)
        self.assertEqual(self.emails_sent, [])

        # Email nudge after the hard reminder threshold
        self.clock.set_day_and_time("24/2/2019 17:01")
        self.aggregator.send_warnings_for_chores(self.logger)
        self.assertEqual(
            self.emails_sent,
            [
                ("deelnemers@mailing.list", "deelnemers@mailing.list", "EmailNudge"),
                (1, "AskForVolunteeringNotification"),
            ],
        )
        self.emails_sent = []
        self.assertEqual(
            self.bot_messages,
            [
                (1, "AskForVolunteeringNotification"),
            ],
        )
        self.bot_messages = []

        # Wrong confirmation via chat-bot
        self.send_bot_message(STEFANO, "wefwef")
        self.assertEqual(
            self.bot_messages,
            [
                (1, "MessageUnknown"),
            ],
        )
        self.bot_messages = []

        # Confirm volunteering via chat-bot
        self.send_bot_message(STEFANO, "yes")
        self.assertEqual(
            self.bot_messages,
            [
                (1, "MessageConfirmedVolunteering"),
            ],
        )
        self.bot_messages = []

        # Reminder the day before
        self.clock.set_day_and_time("25/2/2019 19:01")
        self.aggregator.send_warnings_for_chores(self.logger)
        self.assertEqual(
            self.emails_sent,
            [
                (1, "VolunteeringReminderNotification"),
            ],
        )
        self.emails_sent = []
        self.assertEqual(
            self.bot_messages,
            [
                (1, "VolunteeringReminderNotification"),
            ],
        )
        self.bot_messages = []
