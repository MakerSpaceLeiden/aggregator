#!/usr/bin/env python
import os
import sys

# In production, using systemd, to set environment variables use:
# systemctl set-environment var=value


CONFIG = {
    # 'daemon': {
    #     'work_dir': '/Users/stefano',
    #     'umask': 0o022,
    #     'pidfile_path': '/Users/stefano/aggregator_pidfile',
    #     'uid': 501,
    #     'gid': 20,
    # },
    "logging": {
        "log_filepath": "/var/log/aggregator/aggregator.log",
        "when": "D",
        "interval": 1,  # Rotate every day
        "backup_count": 10,  # Keep 10 days of log
    },
    "mysql": {
        #        'host': 'localhost',
        #        'port': 20553,
        "unix_socket": "/var/run/mysqld/mysqld.sock",
        "database": "mslcrm",
        "user": "mslcrmuser",
        "auth_plugin": "mysql_native_password",
        "password": os.environ["MSL_AGGREGATOR_MYSQL_PASSWORD"],
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": os.environ.get("MSL_AGGREGATOR_REDIS_PASSWORD", None),
        "key_prefix": "msl",
        "users_expiration_time_in_sec": 60,
        "pending_machine_activation_timeout_in_sec": 90,
        "telegram_token_expiration_in_sec": 5 * 60,  # 5 minutes
        "machine_state_timeout_in_minutes": 60,  # 1 hour
        "history_lines_expiration_in_days": 7,
    },
    "mqtt": {
        "host": "space.makerspaceleiden.nl",
        "port": 1883,
        "log_all_messages": True,
    },
    "crm": {
        "base_url": "https://mijn.makerspaceleiden.nl/api/v1",
        "auth_type": "token",
        "api_token": os.environ["MSL_AGGREGATOR_CRM_API_TOKEN"],
    },
    "http": {
        "host": "127.0.0.1",
        "port": 5000,
        "basic_auth": {
            "realm": "MSL Aggregator",
            "username": os.environ["MSL_AGGREGATOR_BASIC_AUTH_USERNAME"],
            "password": os.environ["MSL_AGGREGATOR_BASIC_AUTH_PASSWORD"],
        },
    },
    "email": {
        "from_address": "MakerSpace BOT <noc@makerspaceleiden.nl>",
    },
    "telegram_bot": {
        "api_token": os.environ["TELEGRAM_BOT_API"],
    },
    "signal_bot": {
        "some": "config",
    },
}


if __name__ == "__main__":
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "src")
    sys.path.append(src_dirpath)
    from aggregator.main import run_aggregator

    run_aggregator(CONFIG)
