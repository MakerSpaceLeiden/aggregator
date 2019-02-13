import re
import json


MACHINE_TAG_RE = re.compile(r'ac\/log\/(.*)')


def parse_message(topic, message):
    if topic == 'makerspace/groteschakelaar':
        return 'space_open', message == '1'

    if topic == 'ac/log/master' and message.startswith('JSON='):
        payload = json.loads(message[5:])
        if payload.get('userid', None) and payload.get('machine', None) == 'spacedeur' and payload.get('acl', None) == 'approved' and payload.get('cmd', None) == 'leave':
            return 'user_left_space', payload['userid']
        elif payload.get('userid', None) and payload.get('machine', None) == 'spacedeur' and payload.get('acl', None) == 'approved' and payload.get('cmd', None) == 'energize':
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
        if message.startswith(f'{machine_name} {{'):
            payload = json.loads(message[len(machine_name)+1:])
            if payload['state'] == 'Waiting for card':
                return 'machine_state', machine_name, 'ready'

    # Message to ignore
    if (topic, message) in (
            ('makerspace/groteschakelaar/status', 'open'),
            ('makerspace/grotelasercutter', 'offline'),
            ('makerspace/kleinelasercutter', 'offline'),
            ('makerspace/switch', 'online'),
            ('makerspace/vogelkooi/chirp', '0'),
            ('ac/log/master', 'Got disconnected: error 1'),
            ('ac/log/voordeur', 'voordeur Requesting approval'),
            ('test/log/lights', 'lights Lights are on.'),
        ):
        return 'ignore',

    if topic in (
            'makerspace/deur/voor',
            'makerspace/deur/tussen',
            'makerspace/deur/space2',
        ):
        return 'ignore',

    if topic == 'ac/log/voordeur' and message.startswith('voordeur {'):
        return 'ignore',

    if message.startswith('SIG/2.0 ') and (message.endswith(' beat') or ' announce ' in message or ' welcome ' in message or ' energize '):
        return 'ignore',

    if topic == 'ac/log/master' and message.startswith('Announce of'):
        return 'ignore',

    if 'Time warp by' in message:
        return 'ignore',

    if 'Warning: LOW Loop rate' in message:
        return 'ignore',

    if '(Re)calculated session key' in message:
        return 'ignore',

    if '(re)Connected to' in message:
        return 'ignore',

    if '(re)Subscribed.' in message:
        return 'ignore',

    if 'MySQL Connection not available' in message:
        return 'ignore',

    if ' approved action ' in message:
        return 'ignore',

    if ' Received OK to power on ' in message:
        return 'ignore',

    if ' Time-out; transition from ' in message:
        return 'ignore',

    if ' Requesting approval' in message:
        return 'ignore',

    if ' Changed from state ' in message:
        return 'ignore',

    if 'Control node is switched off - but voltage on motor detected' in message:
        return 'ignore',
