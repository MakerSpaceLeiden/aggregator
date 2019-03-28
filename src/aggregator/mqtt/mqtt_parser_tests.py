import os
import unittest
from .mqtt_parser import parse_message

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
SAMPLE_MESSAGES_FILE_PATH = os.path.join(DIR_PATH, 'sample_mqtt_messages.txt')

MISCELLANEOUS_ERRORS_IN_LOGS_3_MAR_2019_FILE_PATH = os.path.join(DIR_PATH, 'errors_3_mar_2019.txt')


class TestMqttParsing(unittest.TestCase):
    def test_groteschakelaar(self):
        self.assertEqual(
            parse_message('makerspace/groteschakelaar', '1'),
            ('space_open', True)
        )
        self.assertEqual(
            parse_message('makerspace/groteschakelaar', '0'),
            ('space_open', False)
        )
        self.assertEqual(
            parse_message('makerspace/groteschakelaar/status/', 'werkend'),
            ('ignore', )
        )

    def test_door(self):
        self.assertEqual(
            parse_message('ac/log/master', 'JSON={"ok": true, "userid": 22, "name": "Stefano Masini", "email": "stefano@stefanomasini.com", "machine": "spacedeur", "acl": "approved", "cmd": "energize"}'),
            ('user_entered_space', 22)
        )
        self.assertEqual(
            parse_message('ac/log/master', 'JSON={"ok": true, "userid": 22, "name": "Stefano Masini", "email": "stefano@stefanomasini.com", "machine": "spacedeur", "acl": "approved", "cmd": "leave"}'),
            ('user_left_space', 22)
        )

    def test_tableSaw(self):
        self.assertEqual(
            parse_message('ac/log/master', 'JSON={"ok": true, "userid": 22, "name": "Stefano Masini", "email": "stefano@stefanomasini.com", "machine": "tablesaw", "acl": "approved"}'),
            ('user_activated_machine', 22, 'tablesaw')
        )
        self.assertEqual(
            parse_message('ac/log/tablesaw', 'tablesaw Machine switched ON with the safety contacto green on-button.'),
            ('machine_power', 'tablesaw', 'on')
        )
        self.assertEqual(
            parse_message('ac/log/tablesaw', 'tablesaw Machine switched OFF with the safety contactor off-button.'),
            ('machine_power', 'tablesaw', 'off')
        )

    def test_planer(self):
        self.assertEqual(
            parse_message('ac/log/master', 'JSON={"ok": true, "userid": 22, "name": "Stefano Masini", "email": "stefano@stefanomasini.com", "machine": "planer", "acl": "approved"}'),
            ('user_activated_machine', 22, 'planer')
        )
        self.assertEqual(
            parse_message('ac/log/planer', 'planer Green button on safety contactor pressed.'),
            ('machine_power', 'planer', 'on')
        )
        self.assertEqual(
            parse_message('ac/log/planer', 'planer Switching off - red button at the back pressed.'),
            ('machine_power', 'planer', 'off')
        )

    def test_lights(self):
        self.assertEqual(
            parse_message('test/log/lights', 'lights {"node":"lights","machine":"lights","maxMqtt":768,"id":"a46210bf713c","ip":"3C:71:BF:10:62:A7","net":"UTP","mac":"3C:71:BF:10:62:A7","beat":2778380,"approve":0,"deny":0,"requests":0,"cache_hit":0,"cache_miss":0,"mqtt_reconnects":12,"loop_rate":9593.431,"coreTemp":71.66666,"heap_free":194472,"state":"Powered - no lights","powered_time":4194,"running_time":197566402,"ota":true,"acstate1":false,"acstate2":true,"acstate3":true}'),
            ('lights', 'large_room', False)
        )
        self.assertEqual(
            parse_message('test/log/lights', 'lights {"node":"lights","machine":"lights","maxMqtt":768,"id":"a46210bf713c","ip":"3C:71:BF:10:62:A7","net":"UTP","mac":"3C:71:BF:10:62:A7","beat":2779074,"approve":0,"deny":0,"requests":0,"cache_hit":0,"cache_miss":0,"mqtt_reconnects":12,"loop_rate":9555.698,"coreTemp":72.77778,"heap_free":194520,"state":"Lights are ON","powered_time":0,"running_time":197566447,"ota":true,"acstate1":true,"acstate2":false,"acstate3":false}'),
            ('lights', 'large_room', True)
        )

    def test_sample_mqtt_messages(self):
        for line in open(SAMPLE_MESSAGES_FILE_PATH).readlines():
            topic, message = line.strip().split(' - ', 1)
            parsed_message = parse_message(topic, message)
            self.assertIsNotNone(parsed_message, f'Unable to parse message: ({repr(topic)}, {repr(message)})')
            if parsed_message[0] == 'machine_state' and parsed_message[-1] != 'ready':
                print(parsed_message)

    def test_miscellaneous_errors_in_logs_3_mar_2019(self):
        for line in open(MISCELLANEOUS_ERRORS_IN_LOGS_3_MAR_2019_FILE_PATH).readlines():
            topic, message = line.strip()[line.strip().index('Cannot parse message:')+22:].split(' - ', 1)
            parsed_message = parse_message(topic, message)
            self.assertIsNotNone(parsed_message, f'Unable to parse message: ({repr(topic)}, {repr(message)})')
            # if parsed_message[0] == 'machine_state' and parsed_message[-1] != 'ready':
            #     print(parsed_message)
