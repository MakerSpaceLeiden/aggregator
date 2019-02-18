from aggregator.messages import MessageHelp, MessageNotRegistered, MessageWho, MessageUnknown, \
    MessageUserNotInSpace, MessageConfirmCheckout, MessageConfirmedCheckout, MessageCancelAction, \
    BASIC_COMMANDS, COMMAND_WHO, COMMAND_HELP, COMMAND_OUT, COMMAND_YES, COMMAND_NO, COMMAND_CHECKIN


(STATE_CONFIRM_CHECKOUT) = range(1)


class BotLogic(object):
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.chat_states = {}

    def handle_new_conversation(self, chat_id, user, message, logger):
        if user:
            return MessageHelp(user, BASIC_COMMANDS)
        return MessageNotRegistered()

    def handle_message(self, chat_id, user, message, logger):
        state = self.chat_states.get(chat_id)

        # Unregistered user
        if not user:
            return MessageNotRegistered()

        normalized_message = message.strip().lower()

        if state is None:
            # Default state
            if normalized_message == COMMAND_WHO.text:
                space_status = self.aggregator.get_space_state_for_json(logger)
                return MessageWho(user, space_status)
            elif normalized_message == COMMAND_HELP.text:
                return MessageHelp(user, BASIC_COMMANDS)
            elif normalized_message == COMMAND_OUT:
                return self._handle_checkout(chat_id, user, logger)
            elif normalized_message == COMMAND_CHECKIN:
                self.aggregator.user_entered_space(user.user_id, logger)
                space_status = self.aggregator.get_space_state_for_json(logger)
                return MessageWho(user, space_status)
            else:
                return MessageUnknown(user)

        elif state == STATE_CONFIRM_CHECKOUT:
            if normalized_message == COMMAND_YES.text:
                self.aggregator.user_left_space(user.user_id, logger)
                self.chat_states[chat_id] = None
                return MessageConfirmedCheckout(user)
            elif normalized_message == COMMAND_NO.text:
                self.chat_states[chat_id] = None
                return MessageCancelAction()
            else:
                # Unknown command - should never be here
                self.chat_states[chat_id] = None
                return MessageUnknown(user)

        else:
            # Unknown state - should never be here
            self.chat_states[chat_id] = None
            return MessageUnknown(user)

    def _handle_checkout(self, chat_id, user, logger):
        is_in_space, ts_checkin = self.aggregator.is_user_id_in_space(user.user_id, logger)
        if not is_in_space:
            return MessageUserNotInSpace(user)
        else:
            self.chat_states[chat_id] = STATE_CONFIRM_CHECKOUT
            return MessageConfirmCheckout(user, ts_checkin)
