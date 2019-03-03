import functools
import paho.mqtt.client as mqtt
from .mqtt_parser import parse_message


MESSAGE_TYPES_TO_DEDUPLICATE = (
    # 'space_open',
)


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
        self.msg_deduplication = {}

    def start_listening_on_a_background_thread(self):
        self.client.loop_start()

    def stop(self):
        self.logger.info('Stopping MQTT client')
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, rc):
        self.logger.info(f'Connected to {self.host}:{self.port}')
        self.client.subscribe([("#", 0)])

    def _on_message(self, client, userdata, msg):
        logger = self.logger.getLoggerWithRandomReqId('mqtt')
        try:
            try:
                msg_str = msg.payload.decode('utf-8')
            except UnicodeDecodeError:
                logger.error(f'Received message, but cannot decode UTF-8: {repr(msg.payload)}')
                return
            if self.log_all_messages:
                logger.info(f'RAW: {repr((msg.topic, msg_str))}')
            parsed_result = parse_message(msg.topic, msg_str)
            if parsed_result:
                if self.log_all_messages:
                    logger.info(f'PARSED: {repr(parsed_result)}')
                msg_type = parsed_result[0]
                if msg_type and msg_type != 'ignore':
                    self._process_parsed_message(parsed_result, logger)
            else:
                logger.error(f'Cannot parse message: {msg.topic} - {msg_str}')
        except Exception as e:
            logger.error('Error in _on_message handler', exc_info=e)

    def _process_parsed_message(self, parsed_result, logger):
        msg_type, *args = parsed_result
        if msg_type in MESSAGE_TYPES_TO_DEDUPLICATE:
            last_parsed_message = self.msg_deduplication.get(msg_type)
            if parsed_result == last_parsed_message:
                # Skipping this message because last time it was identical (and we know these messages are idempotent)
                return
            else:
                self.msg_deduplication[msg_type] = parsed_result

        method = getattr(self.aggregator, msg_type, None)
        if method:
            aggregator_function = functools.partial(method, *args)
            self.worker_input_queue.add_task(aggregator_function, logger)
        else:
            logger.error(f'Missing method {msg_type} in {self.aggregator}')
