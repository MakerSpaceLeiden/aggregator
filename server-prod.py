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

    'logging': {
        'log_filepath': '/var/log/msl_aggregator.log',
        'when': 'D', 'interval': 1,  # Rotate every day
        'backup_count': 10,  # Keep 10 days of log
    },

    'mysql': {
        'host': 'localhost',
        'port': 3306,
        'database': 'mslcrm',
        'user': 'mslcrmuser',
        'password': os.environ['MSL_AGGREGATOR_MYSQL_PASSWORD'],
    },

    'redis': {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'key_prefix': 'msl',
        'users_expiration_time_in_sec': 60,
        'pending_machine_activation_timeout_in_sec': 90,
        'telegram_token_expiration_in_sec': 5 * 60,  # 5 minutes
    },

    'mqtt': {
        'host': 'space.makerspaceleiden.nl',
        'port': 1883,
        'log_all_messages': True,
    },

    'http': {
        'host': '127.0.0.1',
        'port': 5000,
        'basic_auth': {
            'realm': 'MSL Aggregator',
            'username': os.environ['MSL_AGGREGATOR_BASIC_AUTH_USERNAME'],
            'password': os.environ['MSL_AGGREGATOR_BASIC_AUTH_PASSWORD'],
        },
    },

    'check_stale_checkins': {
        # If someone is still checked in at 5am from at least midnight, consider it stale
        'crontab': '0 5 * * *',  # At 5am every day
        'stale_after_hours': 5,
    },

    'telegram_bot': {
        'api_token': os.environ['TELEGRAM_BOT_API'],
    },
}


if __name__ == '__main__':
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
    sys.path.append(src_dirpath)
    from aggregator.main import run_aggregator
    run_aggregator(CONFIG)
