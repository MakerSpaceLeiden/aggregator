import base64
from unittest.mock import Mock

import pytest
from mock import AsyncMock

from aggregator.http_server import create_app


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for the Quart app."""
    # Mock message queue
    input_message_queue = Mock()
    input_message_queue.get_next_message = AsyncMock()

    # Mock aggregator
    aggregator = Mock()
    aggregator.get_tags = AsyncMock(return_value=[])
    aggregator.get_space_state_for_json = AsyncMock(return_value={"state": "open"})
    aggregator.get_chores_for_json = AsyncMock(return_value={"chores": []})

    # Mock worker input queue
    worker_input_queue = Mock()
    worker_input_queue.add_task_with_result_future = AsyncMock()

    # Mock logger
    logger = Mock()
    mock_request_logger = Mock()
    mock_request_logger.info = Mock()
    mock_request_logger.error = Mock()
    logger.getLoggerWithRandomReqId = Mock(return_value=mock_request_logger)
    logger.exception = Mock()

    # Basic auth config
    basic_auth = {
        "username": "test_user",
        "password": "test_pass",
        "realm": "test_realm",
    }

    return {
        "input_message_queue": input_message_queue,
        "aggregator": aggregator,
        "worker_input_queue": worker_input_queue,
        "logger": logger,
        "basic_auth": basic_auth,
    }


@pytest.fixture
def app(mock_dependencies):
    """Create a test Quart app."""
    return create_app(**mock_dependencies)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def auth_headers(mock_dependencies):
    """Create basic auth headers."""
    credentials = f"{mock_dependencies['basic_auth']['username']}:{mock_dependencies['basic_auth']['password']}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded_credentials}"}


@pytest.mark.asyncio
async def test_root_route_success(client):
    """Test GET request to root route returns correct response."""
    response = await client.get("/")

    assert response.status_code == 200
    assert response.mimetype == "text/plain"

    response_text = await response.get_data(as_text=True)
    assert response_text == "MSL Aggregator"
