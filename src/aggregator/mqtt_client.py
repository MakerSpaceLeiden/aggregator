import functools
from uuid import uuid4
import paho.mqtt.client as mqtt
from .mqtt_parser import parse_message


class MqttListenerClient(object):
    def __init__(self, http_server_input_message_queue, worker_input_queue, aggregator, logger, host, port, log_all_messages):
        self.http_server_input_message_queue = http_server_input_message_queue
        self.worker_input_queue = worker_input_queue
        self.aggregator = aggregator
        self.logger = logger.getLogger(subsystem='mqtt')
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.host = host
        self.port = port
        self.log_all_messages = log_all_messages
        self.client.connect(host, port)

    def start_listening_on_a_background_thread(self):
        self.client.loop_start()

    def stop(self):
        self.logger.info('Stopping MQTT client')
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, rc):
        self.logger.info(f'Connected to {self.host}:{self.port}')
        self.client.subscribe([("#", 0)])

    def _on_message(self, client, userdata, msg):
        logger = self.logger.getLogger(req_id=uuid4())
        try:
            msg_str = msg.payload.decode('utf-8')
            if self.log_all_messages:
                self.logger.info(f'{msg.topic} - {msg_str}')
            parsed_result = parse_message(msg.topic, msg_str)
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
