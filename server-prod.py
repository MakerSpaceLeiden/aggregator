#!/usr/bin/env python
import os
import sys


CONFIG = {
    # 'daemon': {
    #     'work_dir': '/Users/stefano',
    #     'umask': 0o022,
    #     'pidfile_path': '/Users/stefano/aggregator_pidfile',
    #     'uid': 501,
    #     'gid': 20,
    # },

    # 'logging': {
    #     'log_filepath': '/Users/stefano/aggregator_log.txt',
    #     'max_bytes': 1 * 1024 * 1024,  # 1 Mb
    #     'backup_count': 10,
    # },

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
        'expiration_time_in_sec': 60,
    },

    'mqtt': {
        'host': 'space.makerspaceleiden.nl',
        'port': 1883,
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
}


if __name__ == '__main__':
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
    sys.path.append(src_dirpath)
    from aggregator.main import run_aggregator
    run_aggregator(CONFIG)
