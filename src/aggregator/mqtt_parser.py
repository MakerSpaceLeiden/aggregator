import re
import json


MACHINE_TAG_RE = re.compile(r'ac\/log\/(.*)')


def parse_message(topic, message):
    if topic == 'ac/log/master' and message.startswith('JSON='):
        payload = json.loads(message[5:])
        if payload.get('userid', None) and payload.get('machine', None) == 'spacedeur' and payload.get('acl', None) == 'approved':
            return 'user_entered_space_door', payload['userid']
        elif payload.get('userid', None) and payload.get('machine', None) and payload.get('acl', None) == 'approved':
            return 'user_activated_machine', payload['userid'], payload['machine']

    machine_match = MACHINE_TAG_RE.match(topic)
    if machine_match:
        machine_name = machine_match.group(1)
        if message == f'{machine_name} Machine switched ON with the safety contacto green on-button.':
            return 'machine_power', machine_name, 'on'
        if message == f'{machine_name} Green button on safety contactor pressed.':
            return 'machine_power', machine_name, 'on'
        if message == f'{machine_name} Machine switched OFF with the safety contactor off-button.':
            return 'machine_power', machine_name, 'off'
        if message == f'{machine_name} Switching off - red button at the back pressed.':
            return 'machine_power', machine_name, 'off'
