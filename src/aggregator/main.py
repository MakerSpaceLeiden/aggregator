import signal
import sys
from aggregator.http_server import run_http_server, get_input_message_queue, get_worker_input_queue
from aggregator.mqtt_client import MqttListenerClient
from aggregator.database import MySQLAdapter
from aggregator.redis import RedisAdapter
from aggregator.logic import Aggregator
from aggregator.logging import Logger
from aggregator.worker import Worker


def run_aggregator(config):
    logger = Logger(subsystem='root')

    aggregator = Aggregator(
        MySQLAdapter(**config['mysql']),
        RedisAdapter(**config['redis']),
    )

    q = get_input_message_queue()
    worker_input_queue = get_worker_input_queue()
    mqtt_listener_client = MqttListenerClient(q, **config['mqtt'])
    mqtt_listener_client.start_listening_on_a_background_thread()

    worker = Worker(worker_input_queue)
    worker.start_working_in_background_thread()

    def signal_handler(sig, frame):
        print('Detected Ctrl+C')
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    # signal.pause()

    run_http_server(
        input_message_queue=q,
        aggregator=aggregator,
        worker_input_queue=worker_input_queue,
        logger=logger,
        **config['http']
    )
