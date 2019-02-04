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
            parsed_result = self._parse_message(msg)
            if parsed_result:
                msg_type, *args = parsed_result
                if msg_type:
                    logger.info(f'Received message of type: {msg_type}')
                    method = getattr(self.aggregator, msg_type, None)
                    if method:
                        aggregator_function = functools.partial(method, *args)
                        self.worker_input_queue.add_task(aggregator_function, logger)
                    else:
                        logger.error(f'Missing method {msg_type} in {self.aggregator}')
        except Exception as e:
            logger.error('Error in _on_message handler', exc_info=e)

    def _parse_message(self, msg):
        msg_str = msg.payload.decode('utf-8')
        self.logger.info(f'{msg.topic} - {msg_str}')
        if msg.topic == 'ac/log/master' and msg_str.startswith('JSON='):
            payload = json.loads(msg_str[5:])
            if payload.get('userid', None) and payload.get('machine', None) == 'spacedeur' and payload.get('acl', None) == 'approved':
                return 'user_entered_space_door', payload['userid']
            if payload.get('userid', None) and payload.get('machine', None) == 'tablesaw' and payload.get('acl', None) == 'approved':
                return 'user_activated_machine', payload['userid'], payload['machine']

        if msg.topic == 'ac/log/tablesaw' and msg_str.startswith('tablesaw Machine switched'):
            if msg_str == 'tablesaw Machine switched ON with the safety contacto green on-button.':
                return 'machine_power', 'tablesaw', 'on'
            if msg_str == 'tablesaw Machine switched OFF with the safety contactor off-button.':
                return 'machine_power', 'tablesaw', 'off'

