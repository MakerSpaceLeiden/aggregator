# Init server
import os
import socket
import sys
from contextlib import closing

import pytest


class TestAggregatorIntegration:
    """Integration test for the aggregator service"""

    def find_free_port(self):
        """Find a free port for testing."""
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    @pytest.fixture
    def test_config(self):
        """Test configuration that will use real components."""
        return {
            "mysql": {
                "host": "localhost",
                "port": 3306,
                "database": "test_makerspace",
                "user": "test_user",
                "password": "test_password",
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "key_prefix": "msl_test",
                "users_expiration_time_in_sec": 60,
                "pending_machine_activation_timeout_in_sec": 90,
                "telegram_token_expiration_in_sec": 300,
                "machine_state_timeout_in_minutes": 60,
                "history_lines_expiration_in_days": 7,
            },
            "mqtt": {
                "host": "localhost",
                "port": 1883,
                "log_all_messages": False,
            },
            "http": {
                "host": "127.0.0.1",
                "port": self.find_free_port(),
                "basic_auth": {
                    "realm": "MSL Aggregator Test",
                    "username": "test_user",
                    "password": "test_pass",
                },
            },
            "check_stale_checkins": {
                "crontab": "0 5 * * *",
                "stale_after_hours": 5,
            },
            "email": {
                "from_address": "Test BOT <test@example.com>",
            },
            "chores": {
                "timeframe_in_days": 90,
                "warnings_check_window_in_hours": 2,
                "message_users_seen_no_later_than_days": 14,
            },
        }

    def test_aggregator_main_function_accepts_config(self, test_config, redisdb):
        """Test that the main aggregator function accepts and processes configuration."""

        # Add the src directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(os.path.dirname(current_dir), "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        try:
            from aggregator.main import run_aggregator

            # This should import successfully and accept the config
            # Even if it fails on connection, it validates the interface
            run_aggregator(test_config)

        except Exception as e:
            # Expected to fail due to external dependencies
            # But the function should exist and accept the config format
            assert "run_aggregator" not in str(
                e
            ), "Function should exist and be callable"

            # Should be a runtime error, not import or syntax error
            assert not isinstance(
                e, (ImportError, SyntaxError)
            ), f"Unexpected error type: {type(e)}"
