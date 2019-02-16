from functools import partial
from .bot_logic import ReplyMarkdownWithKeyboard, ReplyEndConversation
import ravel
import dbussy as dbus
from dbussy import DBUS


BUS_NAME = "org.asamk.Signal"
PATH_NAME = "/org/asamk/Signal"
IFACE_NAME = "org.asamk.Signal"
SIGNAL_NAME = "MessageReceived"
IN_SIGNATURE = "xsaysas"


class SignalBot(object):
    def __init__(self, worker_input_queue, aggregator, logger, asyncio_loop):
        self.logger = logger.getLogger(subsystem='signal_bot')
        self.worker_input_queue = worker_input_queue
        self.aggregator = aggregator
        self.aggregator.bot_logic.send_message.plug(self._send_message_markdown_to_user)
        self.bus = ravel.system_bus()
        self.bus.attach_asyncio(asyncio_loop)

    def _send_message_markdown_to_user(self, user, markdown, logger):
        pass
        # self.updater.bot.send_message(user.telegram_user_id, text=markdown)

    def start_bot(self):
        self.logger.info('Starting Signal BOT')

        self.bus.listen_signal(
            path=PATH_NAME,
            interface=IFACE_NAME,
            name=SIGNAL_NAME,
            func=self.handle_message,
            fallback=True,
        )

    @ravel.signal(name=SIGNAL_NAME, in_signature=IN_SIGNATURE)
    def handle_message(self, msgid, sender, groupIDs, body, attachments):
        print(f'Received {body} from {sender} - sending an ack.')

        # attachments = ['/tmp/x.txt']
        attachments = []

        # Ack just to the sender (not the group)
        self._send_message("Ack!", attachments, [sender])

    def _send_message(self, body, attachments, destinations):
        ep = self.bus[BUS_NAME][PATH_NAME].get_interface(IFACE_NAME)
        ep.sendMessage(body, attachments, destinations)

    # def handle_message(self, bot, update):
    #     try:
    #         chat_id = str(update.message.chat_id)
    #         message = update.message.text
    #         user = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.get_user_by_telegram_id, chat_id), self.logger)
    #         if message.startswith('/start'):
    #             reply = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.handle_new_conversation, chat_id, user, message), self.logger)
    #         else:
    #             reply = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.handle_bot_message, chat_id, user, message), self.logger)
    #         if isinstance(reply, ReplyMarkdownWithKeyboard):
    #             update.message.reply_markdown(reply.markdown, reply_markup=ReplyKeyboardMarkup(reply.next_commands, one_time_keyboard=True))
    #         elif isinstance(reply, ReplyEndConversation):
    #             update.message.reply_markdown(reply.markdown, reply_markup=ReplyKeyboardRemove())
    #         else:
    #             self.logger.error(f'Invalid reaction from BOT logic: {repr(reply)}')
    #     except Exception:
    #         self.logger.exception(f'Unexpected exception in message handler')

    def stop_bot(self):
        self.logger.info('Stopping Signal BOT')

        self.bus.unlisten_signal(
            path=PATH_NAME,
            interface=IFACE_NAME,
            name=SIGNAL_NAME,
            func=self.handle_message,
            fallback=True,
        )

    # def _error(self, bot, update, error):
    #     self.logger.error(f'Update "{update}" caused error "{error}"', error)
