import time
from config import is_cli_available, CLI_RUNNER, BOT_NAME

_start_time: float = 0.0
_message_count: int = 0
_last_message_time: float | None = None


def init() -> None:
    global _start_time
    _start_time = time.time()


def record_message() -> None:
    global _message_count, _last_message_time
    _message_count += 1
    _last_message_time = time.time()


def get_health() -> dict:
    uptime = time.time() - _start_time if _start_time else 0
    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 1),
        "message_count": _message_count,
        "last_message_time": _last_message_time,
    }


def get_status() -> dict:
    info = get_health()
    info["cli_runner"] = CLI_RUNNER
    info["bot_name"] = BOT_NAME
    info["cli_available"] = is_cli_available()
    return info
