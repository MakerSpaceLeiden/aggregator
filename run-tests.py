#!/usr/bin/env python
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    """Set up environment and run tests with optional coverage analysis."""
    parser = argparse.ArgumentParser(
        description="Run tests with optional coverage analysis"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage analysis"
    )

    args = parser.parse_args()

    src_dir = Path(__file__).parent / "src"

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)

    # Set timezone before running tests
    setup_timezone(src_dir, env)

    if args.coverage:
        run_tests_with_coverage(src_dir, env, args)
    else:
        run_tests_without_coverage(src_dir, env)


def setup_timezone(src_dir, env):
    """Set up timezone configuration."""
    sys.path.insert(0, str(src_dir))
    try:
        from aggregator.clock import set_local_timezone_to_utc

        set_local_timezone_to_utc()
    except ImportError:
        print("Warning: Could not import timezone setup")


def run_tests_with_coverage(src_dir, env, args):
    """Run tests with coverage analysis using coverage run."""
    print("Running tests with coverage analysis...")

    # Build pytest command with coverage
    cmd = [
        "pytest",
        str(src_dir),
        "--cov=" + str(src_dir),
        f"--ignore={src_dir}/*/tests/",  # Ignore test directories from coverage
    ]

    result = subprocess.run(cmd, env=env)

    if result.returncode != 0:
        print("Tests failed!")
        sys.exit(result.returncode)

    # Generate coverage report
    print("\n" + "=" * 50)
    print("COVERAGE REPORT")
    print("=" * 50)

    subprocess.run(["coverage", "report", "--show-missing"])


def run_tests_without_coverage(src_dir, env):
    """Run tests without coverage analysis."""
    cmd = [
        "pytest",
        str(src_dir),
        "-v",
    ]

    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
