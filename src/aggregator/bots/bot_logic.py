from collections import namedtuple

ReplyMarkdownWithKeyboard = namedtuple('MarkdownReply', 'markdown next_commands')
ReplyEndConversation = namedtuple('ReplyEndConversation', 'markdown')

Command = namedtuple('Command', 'text description')

CR = '\n'


COMMAND_WHO = Command('who', 'Show the last checkins at the space'),
COMMAND_HELP = Command('help', 'Show the available commands'),
ALL_COMMANDS = (COMMAND_WHO, COMMAND_HELP)

STATE_ONBOARDING, STATE_MAIN = range(2)


class BotLogic(object):
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.chat_states = {}

    def handle_new_conversation(self, chat_id, user, message, logger):
        if user:
            return self._handle_state_onboarding(chat_id, user, logger)
        return self._handle_state_not_registered(chat_id, logger)

    def handle_message(self, chat_id, user, message, logger):
        state = self.chat_states.get(chat_id)

        # Unregistered user
        if not user:
            return self._handle_state_not_registered(chat_id, logger)

        # No current chat state
        if state is None:
            return self._handle_state_onboarding(chat_id, user, logger)

        # Main state
        if state == STATE_MAIN:
            if message == COMMAND_WHO.text:
                return self._handle_state_main(chat_id, user, logger)
            elif message == COMMAND_HELP.text:
                return MessageHelp(user, ALL_COMMANDS)
            else:
                return MessageUnknown(user)

    def _handle_state_onboarding(self, chat_id, user, logger):
        self.chat_states[chat_id] = STATE_MAIN
        return MessageOnboarding(user)

    def _handle_state_not_registered(self, chat_id, logger):
        self.chat_states[chat_id] = None
        return MessageNotRegistered()

    def _handle_state_main(self, chat_id, user, logger):
        self.chat_states[chat_id] = STATE_MAIN
        space_status = self.aggregator.get_space_state_for_json(logger)
        return MessageWho(user, space_status)


# -- BOT messages ----

class BaseBotMessage(object):
    next_commands = None
    message = ''

    def get_markdown(self):
        return self.get_text()

    def get_text(self):
        return self.message


class MessageNotRegistered(BaseBotMessage):
    message = (
        "Hi! I'm the MakerSpace Leiden BOT.\n"
        "In order to interact with me you must first connect your CRM account.\n"
        "You can do that from the your Your Data page, in the Notification Settings."
    )


class MessageOnboarding(BaseBotMessage):
    next_commands = ALL_COMMANDS

    def __init__(self, user):
        self.user = user

    def get_text(self):
        return (
            f"Hello {self.user.full_name}! I'm the MakerSpace Leiden BOT.\n"
            "I try to help where I can, reminding people to turn off machines, and stuff like that.\n"
            'Type "help" to see what you can do with me.'
        )


class MessageWho(BaseBotMessage):
    next_commands = ALL_COMMANDS

    def __init__(self, user, space_status):
        self.user = user
        self.space_status = space_status

    def get_text(self):
        return (
            f'''{self.user.first_name}, the space is marked as {'OPEN' if self.space_status["space_open"] or True else "closed"}.\n'''
            f"Latest checkins today:\n"
            f"{CR.join(' - {0} ({1} - {2})'.format(user_data['user']['full_name'], user_data['ts_checkin_human'], user_data['ts_checkin']) for user_data in self.space_status['users_in_space'])}"
        )


class MessageUnknown(BaseBotMessage):
    next_commands = ALL_COMMANDS

    def __init__(self, user):
        self.user = user

    def get_text(self):
        return f"Sorry {self.user.first_name}, I don't understand that command. Type \"help\"."


class MessageHelp(BaseBotMessage):
    def __init__(self, user, commands):
        self.user = user
        self.commands = commands

    def get_text(self):
        commands_text = '\n'.join(f'{command.text} - {command.description}' for command in self.commands)
        return f'{self.user.first_name}, here are the commands you can type:\n{commands_text}'
