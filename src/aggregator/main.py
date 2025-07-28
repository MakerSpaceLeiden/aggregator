def run_aggregator(config):
    # Run locally
    if not config.get("daemon", None):
        _main(config)
        return

    # Production: run as daemon
    import daemon
    import daemon.pidfile

    with daemon.DaemonContext(
        working_directory=config["daemon"].get("work_dir"),
        umask=config["daemon"].get("umask"),
        pidfile=daemon.pidfile.PIDLockFile(config["daemon"]["pidfile_path"]),
        uid=config["daemon"]["uid"],
        gid=config["daemon"]["gid"],
        prevent_core=True,
    ):
        _main(config)


def _main(config):
    # Imports are made here because some libraries initialize file descriptors upon import,
    # but when daemonized those file descriptors are closed

    import asyncio

    from aggregator.clock import Clock
    from aggregator.communication import HttpServerInputMessageQueue, WorkerInputQueue
    from aggregator.crm_adapter import CrmAdapter
    from aggregator.database import MySQLAdapter
    from aggregator.email_adapter import EmailAdapter
    from aggregator.http_server import run_http_server
    from aggregator.logging import configure_logging
    from aggregator.logic import Aggregator
    from aggregator.mqtt.mqtt_client import MqttListenerClient
    from aggregator.redis import RedisAdapter
    from aggregator.timed_tasks import (
        TaskScheduler,
        start_checking_for_off_machines,
        start_checking_for_stale_checkins,
    )
    from aggregator.worker import Worker

    logger, logging_handler = configure_logging(**config.get("logging", {}))
    logger.info("Initializing Aggregator service")

    # Initialize AsyncIO
    loop = asyncio.get_event_loop()

    # Communication queues
    http_server_input_message_queue = HttpServerInputMessageQueue(loop)
    worker_input_queue = WorkerInputQueue(loop)

    # Clock
    clock = Clock()

    # Email
    email_adapter = EmailAdapter(**config["email"])

    # Task scheduler
    task_scheduler = TaskScheduler(clock, logger)

    # Application logic
    aggregator = Aggregator(
        MySQLAdapter(**config["mysql"]),
        RedisAdapter(clock, **config["redis"]),
        CrmAdapter(**config["crm"]),
        http_server_input_message_queue,
        clock,
        email_adapter,
        task_scheduler,
        config["check_stale_checkins"]["stale_after_hours"]
        if "check_stale_checkins" in config
        else 0,
    )

    # Start MQTT listener
    mqtt_listener_client = MqttListenerClient(
        http_server_input_message_queue,
        worker_input_queue,
        aggregator,
        logger,
        **config["mqtt"],
    )
    mqtt_listener_client.start_listening_on_a_background_thread()

    # Start worker
    worker = Worker(worker_input_queue)
    worker.start_working_in_background_thread()

    # Start cronjobs
    if "check_stale_checkins" in config:
        start_checking_for_stale_checkins(
            aggregator,
            worker_input_queue,
            config["check_stale_checkins"]["crontab"],
            logger,
        )
    start_checking_for_off_machines(aggregator, worker_input_queue, logger)
    task_scheduler.start_running_scheduled_tasks(worker_input_queue)

    # Start HTTP server (blocks until Ctrl-C)
    run_http_server(
        loop=loop,
        input_message_queue=http_server_input_message_queue,
        aggregator=aggregator,
        worker_input_queue=worker_input_queue,
        logger=logger,
        logging_handler=logging_handler,
        **config["http"],
    )

    # Quit the application
    mqtt_listener_client.stop()
