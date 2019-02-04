#!/usr/bin/env python
import os
import sys


if __name__ == '__main__':
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
    sys.path.append(src_dirpath)
    import unittest
    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner()
    test_suite = test_loader.discover(src_dirpath, pattern='*_tests.py')
    test_runner.run(test_suite)
