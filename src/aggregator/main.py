import daemon
import daemon.pidfile


def run_aggregator(config):
    # Run locally
    if not config.get('daemon', None):
        _main(config)
        return

    # Production: run as daemon
    with daemon.DaemonContext(
            working_directory=config['daemon'].get('work_dir'),
            umask=config['daemon'].get('umask'),
            pidfile=daemon.pidfile.PIDLockFile(config['daemon']['pidfile_path']),
            uid=config['daemon']['uid'],
            gid=config['daemon']['gid'],
            prevent_core=True,
        ):
        _main(config)


def _main(config):
    # Imports are made here because some libraries initialize file descriptors upon import,
    # but when daemonized those file descriptors are closed

    import signal
    import sys
    from aggregator.http_server import run_http_server, get_input_message_queue, get_worker_input_queue
    from aggregator.mqtt_client import MqttListenerClient
    from aggregator.database import MySQLAdapter
    from aggregator.redis import RedisAdapter
    from aggregator.logic import Aggregator
    from aggregator.logging import Logger, configure_logging
    from aggregator.worker import Worker

    configure_logging(**config.get('logging', {}))

    logger = Logger(subsystem='root')

    logger.info('Initializing Aggregator service')

    # Communication queues
    q = get_input_message_queue()
    worker_input_queue = get_worker_input_queue()

    # Application logic
    aggregator = Aggregator(
        MySQLAdapter(**config['mysql']),
        RedisAdapter(**config['redis']),
        q,
    )

    mqtt_listener_client = MqttListenerClient(q, worker_input_queue, aggregator, logger, **config['mqtt'])
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
