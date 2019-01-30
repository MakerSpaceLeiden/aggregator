import json
import functools
from uuid import uuid4
import paho.mqtt.client as mqtt


class MqttListenerClient(object):
    def __init__(self, http_server_input_message_queue, worker_input_queue, aggregator, logger, host, port):
        self.http_server_input_message_queue = http_server_input_message_queue
        self.worker_input_queue = worker_input_queue
        self.aggregator = aggregator
        self.logger = logger.getLogger(subsystem='mqtt')
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.host = host
        self.port = port
        self.client.connect(host, port)

    def start_listening_on_a_background_thread(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, rc):
        self.logger.info(f'Connected to {self.host}:{self.port}')
        self.client.subscribe([("ac/#", 0)])

    def _on_message(self, client, userdata, msg):
        logger = self.logger.getLogger(req_id=uuid4())
        try:
            msg_type, aggregator_function = self._parse_message(msg)
            if msg_type:
                logger.info(f'Received message of type: {msg_type}')
                self.worker_input_queue.add_task(aggregator_function, logger)
        except Exception as e:
            logger.error('Error in _on_message handler', exc_info=e)

    def _parse_message(self, msg):
        msg_str = msg.payload.decode('utf-8')
        if msg.topic == 'ac/log/master' and msg_str.startswith('JSON='):
            payload = json.loads(msg_str[5:])
            if payload.get('user_id', None):
                return 'user_entered_space_door', functools.partial(self.aggregator.user_entered_space_door, payload['user_id'])
        # return 'test_msg', functools.partial(self.aggregator.user_entered_space_door, 22)
        return None, None

