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
    from aggregator.http_server import run_http_server, get_input_message_queue, get_worker_input_queue, start_checking_for_stale_checkins
    from aggregator.mqtt_client import MqttListenerClient
    from aggregator.database import MySQLAdapter
    from aggregator.redis import RedisAdapter
    from aggregator.logic import Aggregator
    from aggregator.logging import Logger, configure_logging
    from aggregator.worker import Worker
    from aggregator.clock import Clock

    configure_logging(**config.get('logging', {}))
    logger = Logger(subsystem='root')
    logger.info('Initializing Aggregator service')

    # Properly detect Ctrl+C
    def signal_handler(sig, frame):
        print('Detected Ctrl+C')
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    # Communication queues
    http_server_input_message_queue = get_input_message_queue()
    worker_input_queue = get_worker_input_queue()

    # Clock
    clock = Clock()

    # Application logic
    aggregator = Aggregator(
        MySQLAdapter(**config['mysql']),
        RedisAdapter(clock, **config['redis']),
        http_server_input_message_queue,
        clock,
        config['check_stale_checkins']['stale_after_hours'] if 'check_stale_checkins' in config else 0,
    )

    # Start MQTT listener
    mqtt_listener_client = MqttListenerClient(http_server_input_message_queue, worker_input_queue, aggregator, logger, **config['mqtt'])
    mqtt_listener_client.start_listening_on_a_background_thread()

    # Start worker
    worker = Worker(worker_input_queue)
    worker.start_working_in_background_thread()

    # Start cronjobs
    if 'check_stale_checkins' in config:
        start_checking_for_stale_checkins(aggregator, worker_input_queue, config['check_stale_checkins']['crontab'], logger)

    # Start HTTP server
    run_http_server(
        input_message_queue=http_server_input_message_queue,
        aggregator=aggregator,
        worker_input_queue=worker_input_queue,
        logger=logger,
        **config['http']
    )
