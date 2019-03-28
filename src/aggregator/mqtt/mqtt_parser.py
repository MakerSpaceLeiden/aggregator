import re
import json


MACHINE_TAG_RE = re.compile(r'(?:ac|test)\/log\/(.*)')


def parse_message(topic, message):
    if topic == 'makerspace/groteschakelaar':
        return 'space_open', message == '1'
    if topic == 'makerspace/groteschakelaar/status':
        return 'space_open', message == 'open'
    if topic == 'makerspace/groteschakelaar/status/' and message == 'werkend':
        return 'ignore',

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
        if message.startswith(machine_name) and message.endswith('Connected.'):
            return 'ignore',
        if message == f'{machine_name} Machine switched ON with the safety contacto green on-button.':
            return 'machine_power', machine_name, 'on'
        if message == f'{machine_name} Green button on safety contactor pressed.':
            return 'machine_power', machine_name, 'on'
        if message == f'{machine_name} Switched on - green button at the back pressed.':
            return 'machine_power', machine_name, 'on'
        if message == f'{machine_name} Machine switched OFF with the safety contactor off-button.':
            return 'machine_power', machine_name, 'off'
        if message == f'{machine_name} Switching off - red button at the back pressed.':
            return 'machine_power', machine_name, 'off'
        if message == f'{machine_name} Switching off - card swiped but the green button was not pressed within 120 seconds.':
            return 'machine_power', machine_name, 'off'
        if message == f'{machine_name} Switching off - red button at the back pressed - while running - BAD !':
            return 'machine_power', machine_name, 'off'
        if message == f'{machine_name} Machine idle for too long - switching off.':
            return 'machine_power', machine_name, 'off'
        if message == f'{machine_name} Machine switched OFF with the off-button.':
            return 'machine_power', machine_name, 'off'
        if message.startswith(f'{machine_name} {{'):
            payload = json.loads(message[len(machine_name)+1:])
            if payload['state'] == 'Waiting for card':
                return 'machine_state', machine_name, 'ready'
            if payload['state'] == 'Powered - but idle':
                return 'machine_state', machine_name, 'powered_idle'
            if payload['state'] == 'Running':
                return 'machine_state', machine_name, 'powered_running'
            if payload['state'] == 'Door held open':
                return 'machine_state', machine_name, 'door_held_open'
            if payload['state'] == 'Opening door':
                return 'machine_state', machine_name, 'door_opening'
            if payload['state'] == 'Closing door':
                return 'machine_state', machine_name, 'door_closing'
            if payload['state'] == 'Compressor runnning':
                return 'machine_state', machine_name, 'compressor_running'
            if payload['state'] == 'Powered - compressor off':
                return 'machine_state', machine_name, 'compressor_off'
            if payload['state'] == 'Lights are ON':
                return 'machine_state', machine_name, 'lights_on'
            if payload['state'] == 'Powered - no lights':
                return 'machine_state', machine_name, 'lights_off'
            if payload['state'] == 'Buzzing door':
                return 'machine_state', machine_name, 'buzzing_door'
            if payload['state'] == 'Out of order':
                return 'machine_state', machine_name, 'out_of_order'
            if payload['state'] == 'Contactor Enabled':
                return 'machine_state', machine_name, 'contactor_enabled'

    # Message to ignore
    if (topic, message) in (
            ('makerspace/grotelasercutter', 'offline'),
            ('makerspace/kleinelasercutter', 'offline'),
            ('makerspace/switch', 'online'),
            ('makerspace/vogelkooi/chirp', '0'),
            ('ac/log/master', 'Got disconnected: error 1'),
            ('ac/log/voordeur', 'voordeur Requesting approval'),
            ('test/log/lights', 'lights Lights are on.'),
            ('ac/log/lights', 'lights Lights are on.'),
            ('test/log/dewalt', 'dewalt DeWalt powered on, not running.'),
            ('test/log/dewalt', 'dewalt DeWalt is actually running.'),
            ('test/log/compressor', 'compressor 0.0.0.0 Connected.'),
            ('ac/log/woodlathe', 'woodlathe Problem with the interlock -- is the big green connector unseated ?'),
            ('ac/log/woodlathe', "woodlathe Very strange - current observed while we are 'off'. Should not happen."),
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

    if topic == 'makerspace/grotelasercutter':
        return 'ignore',

    if message.startswith('SIG/2.0 ') and (message.endswith(' beat') or ' announce ' in message or ' welcome ' in message or ' energize '):
        return 'ignore',

    if topic == 'test/master/exhaustnode' and 'event manual-start' in message:
        return 'ignore',

    if topic == 'test/master/exhaustnode' and 'event manual-stop' in message:
        return 'ignore',

    if topic == 'ac/log/master' and message.startswith('Announce of'):
        return 'ignore',

    for substring in MESAGES_TO_IGNORE:
        if substring in message:
            return 'ignore',

    if topic == 'ac/log/master' and 'not found either DB' in message:
        return 'ignore',


MESAGES_TO_IGNORE = [
    'Time warp by',
    'Warning: LOW Loop rate',
    '(Re)calculated session key',
    '(re)Connected to',
    '(re)Subscribed.',
    'MySQL Connection not available',
    ' approved action ',
    ' Received OK to power on ',
    ' Time-out; transition from ',
    ' Requesting approval',
    ' Changed from state ',
    'Control node is switched off - but voltage on motor detected',
    'Out of order energize/denied command received',
    'Motor started',
    'Motor stopped',
    'Failing HELO on',
    'SIG/2 ready',
    'Allowing beats to be',
    'Adjusting beat significantly',
    'List email not sent',
    'Compressor running',
    'swiped - needed a LIKE',
    'rejecting without a nonce',
    'Countdown to forced reboot',
    'Learned a public key of node',
    'key of master, stored in persistent store',
    'OTA: Begin failed',
    'Failed to send',
    'seconds off (max leeway is',
]
