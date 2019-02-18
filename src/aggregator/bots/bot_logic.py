from aggregator.messages import MessageHelp, MessageNotRegistered, MessageWho, MessageUnknown, ALL_COMMANDS, COMMAND_WHO, COMMAND_HELP


class BotLogic(object):
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.chat_states = {}

    def handle_new_conversation(self, chat_id, user, message, logger):
        if user:
            return MessageHelp(user, ALL_COMMANDS)
        return MessageNotRegistered()

    def handle_message(self, chat_id, user, message, logger):
        # state = self.chat_states.get(chat_id)

        # Unregistered user
        if not user:
            return MessageNotRegistered()

        # Default state
        normalized_message = message.strip().lower()
        if normalized_message == COMMAND_WHO.text:
            space_status = self.aggregator.get_space_state_for_json(logger)
            return MessageWho(user, space_status)
        elif normalized_message == COMMAND_HELP.text:
            return MessageHelp(user, ALL_COMMANDS)
        else:
            return MessageUnknown(user)

