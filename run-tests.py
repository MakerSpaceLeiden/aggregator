#!/usr/bin/env python
import sys
import unittest

from pathlib import Path

def main():
    """Set up environment and use unit tests built-in discovery."""
    src_dir = Path(__file__).parent / 'src'
    sys.path.insert(0, str(src_dir))

    from aggregator.clock import set_local_timezone_to_utc
    set_local_timezone_to_utc()

    # Use unittest
    sys.argv = [
        'unittest', 'discover',
        '-s', str(src_dir),
        '-p', '*_tests.py',
        '-t', str(src_dir),
        '-v'
    ]

    unittest.main(module=None)

if __name__ == '__main__':
    main()
