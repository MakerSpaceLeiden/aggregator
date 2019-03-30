from aggregator.messages import MessageHelp, MessageNotRegistered, MessageWho, MessageUnknown, \
    MessageUserNotInSpace, MessageConfirmCheckout, MessageConfirmedCheckout, MessageCancelAction, \
    MessageConfirmedVolunteering, MessageVolunteeringNotNecessary, \
    BASIC_COMMANDS, COMMAND_WHO, COMMAND_HELP, COMMAND_OUT, COMMAND_YES, COMMAND_NO, COMMAND_CHECKIN, \
    STATE_CONFIRM_CHECKOUT, STATE_CONFIRM_VOLUNTEERING


class BotLogic(object):
    def __init__(self, aggregator):
        self.aggregator = aggregator
        self.chat_states = ChatStates(aggregator.clock)

    def handle_new_conversation(self, chat_id, user, message, logger):
        if user:
            return MessageHelp(user, BASIC_COMMANDS)
        return MessageNotRegistered()

    def handle_message(self, chat_id, user, message, logger):
        state, chat_metadata = self.chat_states.get(chat_id)

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
            elif normalized_message == COMMAND_OUT.text:
                return self._handle_checkout(chat_id, user, logger)
            elif normalized_message == COMMAND_CHECKIN.text:
                self.aggregator.user_entered_space(user.user_id, logger)
                space_status = self.aggregator.get_space_state_for_json(logger)
                return MessageWho(user, space_status)
            else:
                return MessageUnknown(user, [COMMAND_WHO.text, COMMAND_OUT.text])

        elif state == STATE_CONFIRM_CHECKOUT:
            if normalized_message == COMMAND_YES.text:
                self.aggregator.user_left_space(user.user_id, logger)
                self.chat_states.clear(chat_id)
                return MessageConfirmedCheckout(user)
            elif normalized_message == COMMAND_NO.text:
                self.chat_states.clear(chat_id)
                return MessageCancelAction()
            else:
                return MessageUnknown(user, [COMMAND_YES.text, COMMAND_NO.text])

        elif state == STATE_CONFIRM_VOLUNTEERING:
            if normalized_message == COMMAND_YES.text:
                registered = self.aggregator.user_volunteers_for_event(chat_metadata['user_id'], chat_metadata['event'], logger)
                self.chat_states.clear(chat_id)
                return MessageConfirmedVolunteering() if registered else MessageVolunteeringNotNecessary()
            elif normalized_message == COMMAND_NO.text:
                self.chat_states.clear(chat_id)
                return MessageCancelAction()
            else:
                return MessageUnknown(user, [COMMAND_YES.text, COMMAND_NO.text])

        else:
            # Unknown state - should never be here
            self.chat_states.clear(chat_id)
            return MessageUnknown(user)

    def _handle_checkout(self, chat_id, user, logger):
        is_in_space, ts_checkin = self.aggregator.is_user_id_in_space(user.user_id, logger)
        if not is_in_space:
            return MessageUserNotInSpace(user)
        else:
            self.chat_states.set(chat_id, STATE_CONFIRM_CHECKOUT)
            return MessageConfirmCheckout(user, ts_checkin)


class ChatStates(object):
    def __init__(self, clock):
        self.clock = clock
        self.states = {}

    def get(self, chat_id):
        value = self.states.get(chat_id)
        if not value:
            return None, None
        state, expiration_ts, metadata = value
        if not expiration_ts:
            return state, metadata
        if self.clock.now() < expiration_ts:
            return state, metadata
        else:
            self.clear(chat_id)
            return None, metadata

    def set(self, chat_id, state, expiration_in_min=None, metadata=None):
        expiration_ts = None
        if expiration_in_min:
            expiration_ts = self.clock.now().add(expiration_in_min, 'minutes')
        self.states[chat_id] = (state, expiration_ts, metadata)

    def clear(self, chat_id):
        self.states[chat_id] = None
