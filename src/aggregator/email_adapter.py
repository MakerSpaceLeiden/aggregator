from subprocess import Popen, PIPE
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailAdapter(object):
    def __init__(self, from_address):
        self.from_address = from_address

    def send_email(self, user, message, logger):
        logger = logger.getLogger(subsystem = 'mail')
        email_body = compose_email(self.from_address, f'{user.full_name} <{user.email}>', message.get_subject_for_email(), message.get_email_text())
        logger.info(f'Sending email to {user.email}')
        try:
            ps = Popen(['/usr/sbin/sendmail', user.email], stdin=PIPE, stderr=PIPE)
            ps.stdin.write(email_body.encode('utf-8'))
            (stdout, stderr) = ps.communicate()
        except:
            logger.exception('Unexpexted error while sending email')
            return
        if ps.returncode:
            error = stderr if stderr else stdout
            logger.error(f'Unexpexted return code while sending email: {error}')


def compose_email(from_address, to_address, subject, body_text):
    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))
    return msg.as_string()

