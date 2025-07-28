#!/usr/bin/env python
import os
import sys

CONFIG = {
    "mysql": {
        "host": "localhost",
        "port": 3306,
        "database": "makerspace",
        "user": os.environ.get("MSL_AGGREGATOR_DB_USER", None),
        "password": os.environ.get("MSL_AGGREGATOR_DB_PASSWORD", None),
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
        "log_all_messages": False,
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
            "username": "user",
            "password": "pass",
        },
    },
    "check_stale_checkins": {
        # If someone is still checked in at 5am from at least midnight, consider it stale
        "crontab": "0 5 * * *",  # At 5am every day
        "stale_after_hours": 5,
    },
    "email": {
        "from_address": "MakerSpace BOT <noc@makerspaceleiden.nl>",
    },
}


if __name__ == "__main__":
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "src")
    sys.path.append(src_dirpath)
    from aggregator.main import run_aggregator

    run_aggregator(CONFIG)
