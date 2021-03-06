#!/usr/bin/env python
import os
import sys


CONFIG = {
    'mysql': {
        'host': 'localhost',
        'port': 3306,
        'database': 'makerspace',
        'user': os.environ.get('MSL_AGGREGATOR_DB_USER', None),
        'password': os.environ.get('MSL_AGGREGATOR_DB_PASSWORD', None),
    },

    'redis': {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'key_prefix': 'msl',
        'users_expiration_time_in_sec': 60,
        'pending_machine_activation_timeout_in_sec': 90,
        'telegram_token_expiration_in_sec': 5 * 60,  # 5 minutes
        'machine_state_timeout_in_minutes': 60,  # 1 hour
        'history_lines_expiration_in_days': 7,
    },

    'mqtt': {
        'host': 'space.makerspaceleiden.nl',
        'port': 1883,
        'log_all_messages': False,
    },

    'http': {
        'host': '127.0.0.1',
        'port': 5000,
        'basic_auth': {
            'realm': 'MSL Aggregator',
            'username': 'user',
            'password': 'pass',
        },
    },

    'check_stale_checkins': {
        # If someone is still checked in at 5am from at least midnight, consider it stale
        'crontab': '0 5 * * *',  # At 5am every day
        'stale_after_hours': 5,
    },

    'email': {
        'from_address': 'MakerSpace BOT <noc@makerspaceleiden.nl>',
    },

    # 'telegram_bot': {
    #     'api_token': os.environ['TELEGRAM_BOT_API'],
    # },

    # 'signal_bot': {
    # },

    'chores': {
        'timeframe_in_days': 90,
        'warnings_check_window_in_hours': 2,  # Window to check for warnings to be sent (i.e. if server is down for longer, warnings might be lost)
        'message_users_seen_no_later_than_days': 14,
    }
}


if __name__ == '__main__':
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
    sys.path.append(src_dirpath)
    from aggregator.main import run_aggregator
    run_aggregator(CONFIG)
