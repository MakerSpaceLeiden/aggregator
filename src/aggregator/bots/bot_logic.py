from collections import namedtuple
from aggregator.communication import PluggableMethodProxy

ReplyMarkdownWithKeyboard = namedtuple('MarkdownReply', 'markdown next_commands')
ReplyEndConversation = namedtuple('ReplyEndConversation', 'markdown')


CR = '\n'

COMMAND_EXIT_ONBOARDING = 'Ok, thanks. Show me the Space.'
COMMANDS_ONBOARDING = (
    (COMMAND_EXIT_ONBOARDING,),
)


COMMAND_SPACE_STATUS = 'Space State'
COMMAND_BYE_BYE = 'Bye bye'
COMMANDS_MAIN = (
    (COMMAND_SPACE_STATUS,),
    (COMMAND_BYE_BYE,)
)

STATE_ONBOARDING, STATE_MAIN = range(2)


class BotLogic(object):
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.chat_states = {}
        self.send_message = PluggableMethodProxy()

    def send_stale_checkout_notification(self, user, ts_checkin, logger):
        self.send_message(user.telegram_user_id, f'Did you forget to checkout yesterday?\nYou entered the Space at {ts_checkin.human_str()}', logger)

    def send_machine_left_on_notification(self, user, machine, logger):
        self.send_message(user.telegram_user_id, f"You forgot to press the red button on the {machine.name}! But don't worry: it turned off automatically. Just don't forget next time. ;-)", logger)

    def handle_message(self, chat_id, message, logger):
        user = self.aggregator.get_user_by_telegram_id(chat_id, logger)
        state = self.chat_states.get(chat_id)

        # /start command
        if message.startswith('/start'):
            connection_token = get_connection_token_from_message(message)
            if connection_token:
                # Clean up old association
                if user:
                    self.aggregator.delete_telegram_id_for_user(user.user_id, logger)
                connecting_user = self.aggregator.register_user_by_telegram_token(connection_token, chat_id, logger)
                if connecting_user:
                    return self._handle_state_onboarding(chat_id, connecting_user, logger)
                return self._handle_state_not_registered(chat_id, logger)
            else:
                if user:
                    return self._handle_state_main(chat_id, user, logger)
                else:
                    return self._handle_state_not_registered(chat_id, logger)

        # Unregistered user
        if not user:
            return self._handle_state_not_registered(chat_id, logger)

        # No current chat state
        if state is None:
            return self._handle_state_onboarding(chat_id, user, logger)

        # Main state
        if state == STATE_MAIN:
            if message == COMMAND_SPACE_STATUS:
                return self._handle_state_main(chat_id, user, logger)
            elif message == COMMAND_BYE_BYE:
                return self._handle_bye_bye(chat_id, logger)
            else:
                return self._handle_unknown_message(chat_id, COMMANDS_MAIN, logger)

        if state == STATE_ONBOARDING:
            if message == COMMAND_EXIT_ONBOARDING:
                return self._handle_state_main(chat_id, user, logger)
            else:
                return self._handle_unknown_message(chat_id, COMMANDS_ONBOARDING, logger)

    def _handle_state_onboarding(self, chat_id, user, logger):
        self.chat_states[chat_id] = STATE_ONBOARDING
        markdown = (f"Hello {user.full_name}! I'm the MakerSpace Leiden BOT.\n"
                    "I try to help where I can, "
                    "reminding people to turn off machines, and stuff like that. "
                    "I can show you the status of the Space, if it's open, who is in and what machines are on.\n\n"
                    "You can always start chatting with me by typing /start.")
        return ReplyMarkdownWithKeyboard(markdown, COMMANDS_ONBOARDING)

    def _handle_state_not_registered(self, chat_id, logger):
        self.chat_states[chat_id] = None
        markdown = (f"Hi! I'm the MakerSpace Leiden BOT.\n"
                    "In order to interact with me you must first connect your CRM account.\n"
                    "You can do that from the your Personal Details page.")
        return ReplyEndConversation(markdown)

    def _handle_state_main(self, chat_id, user, logger):
        self.chat_states[chat_id] = STATE_MAIN
        space_status = self.aggregator.get_space_state_for_json(logger)

        markdown = (f"Hi {user.first_name}.\n"
                    f'''The space is {'*OPEN*' if space_status["space_open"] or True else "closed"}.\n\n'''
                    f"{len(space_status['users_in_space'])} makers at the Space:\n"
                    f"{CR.join(' - {0} (_{1}_ - {2})'.format(user_data['user']['full_name'], user_data['ts_checkin_human'], user_data['ts_checkin']) for user_data in space_status['users_in_space'])}"
                    )
        return ReplyMarkdownWithKeyboard(markdown, COMMANDS_MAIN)

    def _handle_bye_bye(self, chat_id, logger):
        self.chat_states[chat_id] = None
        return ReplyEndConversation("_See you later! You can summon me again with_ /start.")

    def _handle_unknown_message(self, chat_id, commands, logger):
        return ReplyMarkdownWithKeyboard("Sorry, I don't understand that.", commands)


def get_connection_token_from_message(message):
    if message.startswith('/start'):
        parts = message.split(' ', 1)
        if len(parts) > 1:
            authorization_token = parts[1]
            return authorization_token
