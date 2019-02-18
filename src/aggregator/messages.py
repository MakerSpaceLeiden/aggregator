from collections import namedtuple

# -- BOT Commands ----

Command = namedtuple('Command', 'text description')


COMMAND_WHO = Command('who', 'Show the last checkins at the space')
COMMAND_HELP = Command('help', 'Show the available commands')
ALL_COMMANDS = (COMMAND_WHO, COMMAND_HELP)


# -- Messages ----

CR = '\n'


class BaseBotMessage(object):
    next_commands = ALL_COMMANDS
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


class MessageWho(BaseBotMessage):
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
    def __init__(self, user):
        self.user = user

    def get_text(self):
        return f"Sorry {self.user.first_name}, I don't understand that command. Try \"help\"."


class MessageHelp(BaseBotMessage):
    def __init__(self, user, commands):
        self.user = user
        self.commands = commands

    def get_text(self):
        commands_text = '\n'.join(f'{command.text} - {command.description}' for command in self.commands)
        return (
            f"Hello {self.user.first_name}! I'm the MakerSpace Leiden BOT.\n"
            "I try to help where I can, reminding people to turn off machines, and stuff like that.\n"
            f'These are the commands you can type:\n{commands_text}'
        )


# -- Notifications ----


class StaleCheckoutNotification(BaseBotMessage):
    def __init__(self, ts_checkin):
        self.ts_checkin = ts_checkin

    def get_text(self):
        return f'Did you forget to checkout yesterday?\nYou entered the Space at {self.ts_checkin.human_str()}'


class MachineLeftOnNotification(BaseBotMessage):
    def __init__(self, machine):
        self.machine = machine

    def get_text(self):
        return f"You forgot to press the red button on the {self.machine.name}! But don't worry: it turned off automatically. Just don't forget next time. ;-)"

