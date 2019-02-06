import unittest
from .mqtt_parser import parse_message


class TestMqttParsing(unittest.TestCase):

    def test_door(self):
        self.assertEqual(
            parse_message('ac/log/master', 'JSON={"ok": true, "userid": 22, "name": "Stefano Masini", "email": "stefano@stefanomasini.com", "machine": "spacedeur", "acl": "approved"}'),
            ('user_entered_space_door', 22)
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
