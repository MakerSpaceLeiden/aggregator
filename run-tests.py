#!/usr/bin/env python
import os
import sys


if __name__ == '__main__':
    src_dirpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
    sys.path.append(src_dirpath)
    import unittest
    from aggregator.clock import set_local_timezone_to_utc
    set_local_timezone_to_utc()
    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner()
    package_directories = [os.path.join(src_dirpath, 'aggregator')]
    test_suites = [test_loader.discover(pkg_dir, pattern='*_tests.py', top_level_dir=src_dirpath) for pkg_dir in package_directories]
    combined_suite = unittest.TestSuite()
    for suite in test_suites:
        combined_suite.addTest(suite)
    result = test_runner.run(combined_suite)

    # Debug output to validate result object
    print("\nTest Result Debug Info:")
    print(f"Type: {type(result)}")
    print(f"wasSuccessful(): {result.wasSuccessful()}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    exit_code = 0 if result.wasSuccessful() else 1
    print(f"Exit code: {exit_code}")
    sys.exit(exit_code)
