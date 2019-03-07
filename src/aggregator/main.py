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
    import os
    import asyncio
    from aggregator.http_server import run_http_server
    from aggregator.timed_tasks import start_checking_for_stale_checkins, TaskScheduler
    from aggregator.mqtt.mqtt_client import MqttListenerClient
    from aggregator.database import MySQLAdapter
    from aggregator.redis import RedisAdapter
    from aggregator.logic import Aggregator
    from aggregator.logging import configure_logging
    from aggregator.worker import Worker
    from aggregator.clock import Clock
    from aggregator.email_adapter import EmailAdapter
    from aggregator.communication import HttpServerInputMessageQueue, WorkerInputQueue

    logger, logging_handler = configure_logging(**config.get('logging', {}))
    logger.info('Initializing Aggregator service')

    # From https://stackoverflow.com/questions/2549939/get-signal-names-from-numbers-in-python
    # _signames = {v: k
    #              for k, v in reversed(sorted(vars(signal).items()))
    #              if k.startswith('SIG') and not k.startswith('SIG_')}
    #
    #
    # def get_signal_name(signum):
    #     """Returns the signal name of the given signal number."""
    #     return _signames[signum]
    #
    # # Properly detect Ctrl+C
    # def signal_handler(signum, frame):
    #     print('AAA')
    #     # print('Received signal {} ({}), stopping...'.format(signum, get_signal_name(signum)))
    #     # os._exit(1)
    # signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler)
    # signal.signal(signal.SIGABRT, signal_handler)

    # Initialize AsyncIO
    loop = asyncio.get_event_loop()


    # Communication queues
    http_server_input_message_queue = HttpServerInputMessageQueue(loop)
    worker_input_queue = WorkerInputQueue(loop)

    # Clock
    clock = Clock()

    # Email
    email_adapter = EmailAdapter(**config['email'])

    # Task scheduler
    task_scheduler = TaskScheduler(clock, logger)

    # Application logic
    aggregator = Aggregator(
        MySQLAdapter(**config['mysql']),
        RedisAdapter(clock, config['chores']['warnings_check_window_in_hours'], **config['redis']),
        http_server_input_message_queue,
        clock,
        email_adapter,
        task_scheduler,
        config['check_stale_checkins']['stale_after_hours'] if 'check_stale_checkins' in config else 0,
        config['chores']['timeframe_in_days'],
        config['chores']['warnings_check_window_in_hours'],
        config['chores']['message_users_seen_no_later_than_days'],
    )

    # Start MQTT listener
    mqtt_listener_client = MqttListenerClient(http_server_input_message_queue, worker_input_queue, aggregator, logger, **config['mqtt'])
    mqtt_listener_client.start_listening_on_a_background_thread()

    # Start worker
    worker = Worker(worker_input_queue)
    worker.start_working_in_background_thread()

    # Start Telegram BOT
    telegram_bot = None
    if config.get('telegram_bot'):
        try:
            from aggregator.bots.telegram_bot import TelegramBot
            telegram_bot = TelegramBot(worker_input_queue, aggregator, logger, **config['telegram_bot'])
            telegram_bot.start_bot()
        except Exception:
            logger.exception('Unexpected error while starting Telegram BOT')

    # Start Signal BOT
    signal_bot = None
    if config.get('signal_bot'):
        try:
            from aggregator.bots.signal_bot import SignalBot
            signal_bot = SignalBot(worker_input_queue, aggregator, logger, loop)
            signal_bot.start_bot()
        except Exception:
            logger.exception('Unexpected error while starting Signal BOT')

    # Start cronjobs
    if 'check_stale_checkins' in config:
        start_checking_for_stale_checkins(aggregator, worker_input_queue, config['check_stale_checkins']['crontab'], logger)
    task_scheduler.start_running_scheduled_tasks(worker_input_queue)

    # Start HTTP server (blocks until Ctrl-C)
    run_http_server(
        loop=loop,
        input_message_queue=http_server_input_message_queue,
        aggregator=aggregator,
        worker_input_queue=worker_input_queue,
        logger=logger,
        logging_handler=logging_handler,
        **config['http']
    )

    # Quit the application
    if telegram_bot:
        telegram_bot.stop_bot()
    if signal_bot:
        signal_bot.stop_bot()
    mqtt_listener_client.stop()
