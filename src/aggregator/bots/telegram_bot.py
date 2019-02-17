from functools import partial
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters)
from .bot_logic import ReplyMarkdownWithKeyboard, ReplyEndConversation


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
        self.updater.bot.send_message(user.telegram_user_id, text=notification.get_string_for_bot())

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
            user = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.get_user_by_telegram_id, telegram_id), self.logger)
            self.logger.info(f'Received message "{message}" from user {user.full_name if user else "<unregistered>"}')
            if message.startswith('/start'):
                reply = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.handle_new_conversation, chat_id, user, message), self.logger)
            else:
                reply = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.handle_bot_message, chat_id, user, message), self.logger)
            if isinstance(reply, ReplyMarkdownWithKeyboard):
                update.message.reply_markdown(reply.markdown, reply_markup=ReplyKeyboardMarkup(reply.next_commands, one_time_keyboard=True))
            elif isinstance(reply, ReplyEndConversation):
                update.message.reply_markdown(reply.markdown, reply_markup=ReplyKeyboardRemove())
            else:
                self.logger.error(f'Invalid reaction from BOT logic: {repr(reply)}')
        except Exception:
            self.logger.exception(f'Unexpected exception in message handler')

    def stop_bot(self):
        self.logger.info('Stopping Telegram BOT')
        if self.updater.running:
            self.updater.stop()

    def _error(self, bot, update, error):
        self.logger.error(f'Update "{update}" caused error "{error}"', error)
