from collections import namedtuple

# -- BOT Commands ----

Command = namedtuple('Command', 'text description')


COMMAND_WHO = Command('who', 'Show the last checkins at the Space')
COMMAND_HELP = Command('help', 'Show the available commands')
COMMAND_OUT = Command('out', 'Check-out of the Space')
COMMAND_CHECKIN = Command('checkin', 'Check-in to the Space')

BASIC_COMMANDS = (COMMAND_WHO, COMMAND_HELP, COMMAND_OUT)

COMMAND_YES = Command('yes', 'Yes')
COMMAND_NO = Command('no', 'No')
YES_NO_COMMANDS = (COMMAND_YES, COMMAND_NO)


# -- Messages ----


class BaseBotMessage(object):
    next_commands = BASIC_COMMANDS
    message = ''

    def get_markdown(self):
        return self.get_text()

    def get_text(self):
        return self.message

    def get_email_text(self):
        return self.get_text()

    def get_subject_for_email(self):
        return ''


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
        lines = [
            f'''{self.user.first_name}, the space is marked as {'OPEN' if self.space_status["space_open"] else "closed"}.'''
        ]
        if not self.space_status['users_in_space']:
            lines.append('''There's no one at the space now.''')
        else:
            lines.append('Latest checkins today:')
            for user_data in self.space_status['users_in_space']:
                lines.append(' - {0} ({1} - {2})'.format(user_data['user']['full_name'], user_data['ts_checkin_human'], user_data['ts_checkin']))
        return '\n'.join(lines)


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


class MessageUserNotInSpace(BaseBotMessage):
    def __init__(self, user):
        self.user = user

    def get_text(self):
        return f"{self.user.first_name}, it doesn't look like you are in the space in this moment."


class MessageConfirmCheckout(BaseBotMessage):
    next_commands = YES_NO_COMMANDS

    def __init__(self, user, ts_checkin):
        self.user = user
        self.ts_checkin = ts_checkin

    def get_text(self):
        return f"So, {self.user.first_name}, it looks like you checked into the Space at {self.ts_checkin.human_str()}.\nDo you want to check-out now?"


class MessageConfirmedCheckout(BaseBotMessage):
    def __init__(self, user):
        self.user = user

    def get_text(self):
        return f"Ok {self.user.first_name}, you are now checked out of the Space."


class MessageCancelAction(BaseBotMessage):
    message = 'Ok, never mind.'


# -- Notifications ----


class StaleCheckoutNotification(BaseBotMessage):
    def __init__(self, user, ts_checkin, notification_settings_url):
        self.user = user
        self.ts_checkin = ts_checkin
        self.notification_settings_url = notification_settings_url

    def get_text(self):
        return f'Did you forget to checkout yesterday?\nYou entered the Space at {self.ts_checkin.human_str()}'

    def get_email_text(self):
        return (
            f"Hello {self.user.first_name},\n\n"
            "It looks like you might have forgotten to checkout at the space yesterday?\n"
            f"According to the logs you entered the space at {self.ts_checkin.human_str()}, but there's no trace of a checkout.\n\n"
            "Checking out is useful so that other people know when to expect other fellow makers at the space, and it allows me to provide useful reminders, "
            "like if the lights are still on when the last person leaves.\n\n"
            "Checking out can be done when you leave, by simply swiping your card again, while you hold the door open on your way out.\n"
            "Or it can also be done via the Chat BOT (Telegram or Signal). If you would like to use the Chat BOT, you can activate it from your personal data "
            f"page in the CRM. This is the link: {self.notification_settings_url}\n\n"
            "The MakerSpace BOT\n\n"
            "PS. If you would rather receive these communications via the Chat BOT instead of email, you can configure your notification settings at the URL above."
        )

    def get_subject_for_email(self):
        return 'Forgot to checkout'


class MachineLeftOnNotification(BaseBotMessage):
    def __init__(self, machine):
        self.machine = machine

    def get_text(self):
        return f"You forgot to press the red button on the {self.machine.name}! But don't worry: it turned off automatically. Just don't forget next time. ;-)"

    def get_subject_for_email(self):
        return f'{self.machine.name} left on'


class TestNotification(BaseBotMessage):
    def __init__(self, user):
        self.user = user

    def get_text(self):
        return f"Hello {self.user.first_name}! This is a test notification from your friendly MakerSpace BOT. You can safely ignore it. Cheers!"

    def get_email_text(self):
        return (
            f"Hello {self.user.first_name}!\n\n"
            "This is a test notification from your friendly MakerSpace BOT.\n"
            "You can safely ignore it.\n\n"
            "Cheers!\n"
            "The MakerSpace BOT"
        )

    def get_subject_for_email(self):
        return 'Test notification'


class ProblemsLeavingSpaceNotification(BaseBotMessage):
    def __init__(self, user, ts_checkout, problems, is_last_user_leaving):
        self.user = user
        self.ts_checkout = ts_checkout
        self.problems = problems
        self.is_last_user_leaving = is_last_user_leaving

    def get_text(self):
        lines = [
            f"{self.user.first_name}, "
        ]
        if self.is_last_user_leaving:
            lines.append(f'{self.user.first_name}, it appears you were the last leaving the space at {self.ts_checkout.human_str()}.')
        else:
            lines.append(f'{self.user.first_name}, it appears you left the space at {self.ts_checkout.human_str()}.')
        lines.append('I noticed the following issues:')
        for problem in self.problems:
            lines.append(' - ' + problem.get_text())
        lines.append('Please remember to take care of this sort of things when you leave the space!')
        return '\n'.join(lines)

    def get_email_text(self):
        lines = [
            f"Hello {self.user.first_name},\n"
        ]
        if self.is_last_user_leaving:
            lines.append(f'It appears you were the last leaving the space at {self.ts_checkout.human_str()}.')
        else:
            lines.append(f'It appears you left the space at {self.ts_checkout.human_str()}.')
        lines.append('\nI noticed the following issues:')
        for problem in self.problems:
            lines.append(' - ' + problem.get_text())
        lines.append('\nPlease remember to take care of this sort of things when you leave the space!')
        lines.append('\nYours truly,')
        lines.append("The MakerSpace BOT")
        return '\n'.join(lines)

    def get_subject_for_email(self):
        return 'Forgotten when leaving the space'


# -- Problems (used to compose notifications) ----


class ProblemMachineLeftOnByUser(object):
    def __init__(self, machine_name):
        self.machine_name = machine_name

    def get_text(self):
        return f'You left the {self.machine_name} turned on (press the RED button!)'


class ProblemMachineLeftOnBySomeoneElse(object):
    def __init__(self, machine_name):
        self.machine_name = machine_name

    def get_text(self):
        return f'Someone left the {self.machine_name} turned on (please, press the RED button)'


class ProblemSpaceLeftOpen(object):
    def get_text(self):
        return f'The big switch (left of the door) was left on the OPEN position'


class ProblemLightLeftOn(object):
    def __init__(self, light):
        self.light = light

    def get_text(self):
        return f'The {self.light.name} lights were left on'
