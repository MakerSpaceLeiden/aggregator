import re
import json


MACHINE_TAG_RE = re.compile(r'ac\/log\/(.*)')


def parse_message(topic, message):
    if topic == 'makerspace/groteschakelaar':
        return 'space_open', message == '1'

    if topic == 'ac/log/master' and message.startswith('JSON='):
        payload = json.loads(message[5:])
        if payload.get('userid', None) and payload.get('machine', None) == 'spacedeur' and payload.get('acl', None) == 'approved' and payload.get('cmd', None == 'leave'):
            return 'user_left_space', payload['userid']
        elif payload.get('userid', None) and payload.get('machine', None) == 'spacedeur' and payload.get('acl', None) == 'approved':
            return 'user_entered_space', payload['userid']
        elif payload.get('userid', None) and payload.get('machine', None) and payload.get('acl', None) == 'approved':
            return 'user_activated_machine', payload['userid'], payload['machine']

    if topic == 'test/log/lights' and message.startswith('lights {'):
        payload = json.loads(message[7:])
        if payload.get('machine', None) == 'lights' and payload.get('state', None) == 'Powered - no lights':
            return 'lights', 'large_room', False
        if payload.get('machine', None) == 'lights' and payload.get('state', None) == 'Lights are ON':
            return 'lights', 'large_room', True

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
