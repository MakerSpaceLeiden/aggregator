#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
    sys.path.append(src_dirpath)
    from aggregator.http_server import run_http_server
    run_http_server()
