"""
Shared display preferences for all bot instances.
Stored in MEMORY_DIR/user_preferences.db so all bots (Claude, Gemini, Codex) share the same settings.
"""
import os
import sqlite3
import logging
import config

logger = logging.getLogger("bridge.display_prefs")

_DB_PATH = os.path.join(os.path.expanduser(str(config.MEMORY_DIR)), "user_preferences.db")
_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id     INTEGER PRIMARY KEY,
                show_tools  INTEGER NOT NULL DEFAULT 1,
                show_thoughts INTEGER NOT NULL DEFAULT 1,
                updated_at  REAL NOT NULL DEFAULT (unixepoch())
            )
        """)
        _conn.commit()
        logger.info(f"Display prefs DB at {_DB_PATH}")
    return _conn


def get_display_prefs(user_id: int) -> dict:
    """Return show_tools and show_thoughts for user. Defaults to config values."""
    try:
        row = _get_conn().execute(
            "SELECT show_tools, show_thoughts FROM user_preferences WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return {"show_tools": bool(row[0]), "show_thoughts": bool(row[1])}
    except Exception as e:
        logger.error(f"get_display_prefs error: {e}")
    return {
        "show_tools": config.DISPLAY_SHOW_TOOLS,
        "show_thoughts": config.DISPLAY_SHOW_THOUGHTS,
    }


def set_display_prefs(user_id: int, show_tools: bool = None, show_thoughts: bool = None) -> dict:
    """Update one or both preferences. Returns new state."""
    current = get_display_prefs(user_id)
    new_tools = show_tools if show_tools is not None else current["show_tools"]
    new_thoughts = show_thoughts if show_thoughts is not None else current["show_thoughts"]
    try:
        _get_conn().execute(
            """INSERT INTO user_preferences (user_id, show_tools, show_thoughts, updated_at)
               VALUES (?, ?, ?, unixepoch())
               ON CONFLICT(user_id) DO UPDATE SET
                   show_tools = excluded.show_tools,
                   show_thoughts = excluded.show_thoughts,
                   updated_at = excluded.updated_at""",
            (user_id, int(new_tools), int(new_thoughts))
        )
        _get_conn().commit()
    except Exception as e:
        logger.error(f"set_display_prefs error: {e}")
    return {"show_tools": new_tools, "show_thoughts": new_thoughts}
