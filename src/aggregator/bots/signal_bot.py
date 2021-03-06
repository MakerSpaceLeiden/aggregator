from functools import partial
import ravel


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
        self.aggregator.signal_bot = self
        self.bus = ravel.system_bus()
        self.bus.attach_asyncio(asyncio_loop)

    # Called from the working thread
    def send_notification(self, user, notification, logger):
        logger = logger.getLogger(subsystem='signal_bot')
        logger.info(f'Sending notification of type {notification.__class__.__name__} to user {user.user_id} {user.full_name}')
        self._send_message(notification, user.phone_number)
        chat_id = f'signal-{user.phone_number}'
        return chat_id

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
    def handle_message(self, msgid, sender, groupIDs, message, attachments):
        try:
            phone_number = sender
            chat_id = f'signal-{phone_number}'
            user = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.get_user_by_phone_number, phone_number), self.logger)
            reply = self.worker_input_queue.add_task_with_result_blocking(partial(self.aggregator.handle_bot_message, chat_id, user, message), self.logger)
            if not reply:
                self.logger.error('Missing reply from BOT logic')
            else:
                self._send_message(reply, sender)
        except Exception:
            self.logger.exception(f'Unexpected exception in message handler')

    def _send_message(self, message, phone_number):
        body = message.get_text()
        ep = self.bus[BUS_NAME][PATH_NAME].get_interface(IFACE_NAME)
        ep.sendMessage(body, [], [phone_number])

    def stop_bot(self):
        self.logger.info('Stopping Signal BOT')

        self.bus.unlisten_signal(
            path=PATH_NAME,
            interface=IFACE_NAME,
            name=SIGNAL_NAME,
            func=self.handle_message,
            fallback=True,
        )
