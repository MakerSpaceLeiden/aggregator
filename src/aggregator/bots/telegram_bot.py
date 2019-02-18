from functools import partial
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters)


class TelegramBot(object):
    def __init__(self, worker_input_queue, aggregator, logger, api_token):
        self.logger = logger.getLogger(subsystem='telegram_bot')
        self.worker_input_queue = worker_input_queue
        self.aggregator = aggregator
        self.updater = Updater(api_token)
        self.aggregator.telegram_bot = self

    def send_notification(self, user, notification, logger):
        logger = logger.getLogger(subsystem='telegram_bot')
        logger.info(f'Sending notification of type {notification.__class__.__name__} to user {user.user_id} {user.full_name}')
        self._send_message(notification, user.telegram_user_id)

    def start_bot(self):
        self.logger.info('Starting Telegram BOT')

        dp = self.updater.dispatcher
        dp.add_handler(CommandHandler("start", self.handle_message))
        dp.add_handler(MessageHandler(Filters.text, self.handle_message))
        dp.add_error_handler(self._error)

        self.updater.start_polling()

    def handle_message(self, bot, update):
        try:
            telegram_id = update.message.chat_id
            chat_id = f'telegram-{telegram_id}'
            message = update.message.text
            user = self._get_user_by_telegram_id(telegram_id)
            self.logger.info(f'Received message "{message}" from user {user.full_name if user else "<unregistered>"}')
            if message.startswith('/start'):
                connection_token = get_connection_token_from_message(message)
                if connection_token:
                    user = self._make_new_telegram_association_for_user(user, connection_token, telegram_id)
                    reply = self._handle_new_bot_conversation(chat_id, user, message)
                else:
                    reply = self._handle_bot_message(chat_id, user, message)
            else:
                reply = self._handle_bot_message(chat_id, user, message)
            if not reply:
                self.logger.error('Missing reply from BOT logic')
            else:
                self._send_message(reply, telegram_id)
        except Exception:
            self.logger.exception(f'Unexpected exception in message handler')

    def _send_message(self, message, telegram_user_id):
        markdown = message.get_markdown()
        reply_markup = ReplyKeyboardMarkup([[command.text for command in message.next_commands]], one_time_keyboard=True) if message.next_commands else ReplyKeyboardRemove()
        self.updater.bot.send_message(telegram_user_id, markdown, reply_markup=reply_markup)

    def stop_bot(self):
        self.logger.info('Stopping Telegram BOT')
        if self.updater.running:
            self.updater.stop()

    def _error(self, bot, update, error):
        self.logger.error(f'Update "{update}" caused error "{error}"', error)

    # -- Proxied aggregator methods (via worker_input_queue) ----

    def _make_new_telegram_association_for_user(self, current_user, connection_token, telegram_id):
        return self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.make_new_telegram_association_for_user, current_user, connection_token, telegram_id), self.logger)

    def _get_user_by_telegram_id(self, telegram_id):
        return self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.get_user_by_telegram_id, telegram_id), self.logger)

    def _handle_new_bot_conversation(self, chat_id, user, message):
        return self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.handle_new_bot_conversation, chat_id, user, message), self.logger)

    def _handle_bot_message(self, chat_id, user, message):
        message = message.lstrip('/')
        return self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.handle_bot_message, chat_id, user, message), self.logger)


def get_connection_token_from_message(message):
    if message.startswith('/start'):
        parts = message.split(' ', 1)
        if len(parts) > 1:
            authorization_token = parts[1]
            return authorization_token
