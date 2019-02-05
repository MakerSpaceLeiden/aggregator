import unittest
from .mqtt_parser import parse_message


class TestMqttParsing(unittest.TestCase):

    def test_tableSaw(self):
        self.assertEqual(
            parse_message('ac/log/tablesaw', 'tablesaw Machine switched ON with the safety contacto green on-button.'),
            ('machine_power', 'tablesaw', 'on')
        )
        self.assertEqual(
            parse_message('ac/log/tablesaw', 'tablesaw Machine switched OFF with the safety contactor off-button.'),
            ('machine_power', 'tablesaw', 'off')
        )
