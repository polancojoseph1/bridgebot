import os
import pytest
import respx
import httpx

# Set dummy env vars to prevent config loading errors if router imports config indirectly
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:AAtesttoken")
os.environ.setdefault("ALLOWED_USER_ID", "12345678")
os.environ.setdefault("CLI_RUNNER", "generic")
os.environ.setdefault("CLI_COMMAND", "echo")

from router import route_message, OLLAMA_URL

@pytest.fixture
def instances():
    return [
        {"id": 1, "title": "First Instance"},
        {"id": 2, "title": "Second Instance"},
        {"id": 3, "title": "Third Instance"}
    ]

@pytest.mark.asyncio
async def test_route_message_fewer_than_two_instances():
    # 0 instances
    assert await route_message("hello", []) is None
    # 1 instance
    assert await route_message("hello", [{"id": 1, "title": "Only Instance"}]) is None

@pytest.mark.asyncio
@respx.mock
async def test_route_message_explicit_reference(instances):
    # Mock the Ollama URL to return a specific instance ID
    respx.post(OLLAMA_URL).mock(return_value=httpx.Response(200, json={"response": "2"}))

    result = await route_message("Talk to the second instance", instances)
    assert result == 2

@pytest.mark.asyncio
@respx.mock
async def test_route_message_no_explicit_reference(instances):
    # Mock the Ollama URL to return 'none'
    respx.post(OLLAMA_URL).mock(return_value=httpx.Response(200, json={"response": "none"}))

    result = await route_message("Just a general question", instances)
    assert result is None

@pytest.mark.asyncio
@respx.mock
async def test_route_message_invalid_instance_id(instances):
    # Mock the Ollama URL to return an ID not in the instances list
    respx.post(OLLAMA_URL).mock(return_value=httpx.Response(200, json={"response": "99"}))

    result = await route_message("Talk to instance 99", instances)
    assert result is None

@pytest.mark.asyncio
@respx.mock
async def test_route_message_timeout_exception(instances):
    # Mock a timeout exception
    # httpx.TimeoutException requires a 'request' argument in modern versions
    mock_request = httpx.Request("POST", OLLAMA_URL)
    respx.post(OLLAMA_URL).mock(side_effect=httpx.TimeoutException("Timeout", request=mock_request))

    result = await route_message("This will timeout", instances)
    assert result is None

@pytest.mark.asyncio
@respx.mock
async def test_route_message_other_exception(instances):
    # Mock a generic exception (e.g., 500 server error)
    respx.post(OLLAMA_URL).mock(return_value=httpx.Response(500))

    result = await route_message("This will error out", instances)
    assert result is None

@pytest.mark.asyncio
@respx.mock
async def test_route_message_empty_response(instances):
    # Mock an empty response string
    respx.post(OLLAMA_URL).mock(return_value=httpx.Response(200, json={"response": " "}))

    result = await route_message("Empty response", instances)
    assert result is None

@pytest.mark.asyncio
@respx.mock
async def test_route_message_response_with_text_and_number(instances):
    # Mock a response that contains text and a valid instance number
    respx.post(OLLAMA_URL).mock(return_value=httpx.Response(200, json={"response": "I think it's 3 based on your input"}))

    result = await route_message("Talk to the third instance", instances)
    assert result == 3
