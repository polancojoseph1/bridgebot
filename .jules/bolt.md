## 2024-03-24 - [Optimize instance_manager.list_all O(n) to O(m)]
**Learning:** `InstanceManager.list_all()` was frequently called (21+ times in `server.py`) and did an O(N) iteration over all instances across all users just to retrieve instances for a single owner. As the total instance count across all users grows, this becomes a bottleneck, especially inside tight loops and message processing checks.
**Action:** Introduced an `_owner_to_ids` dictionary index to maintain an O(1) mapping of `owner_id` to a set of their `instance_id`s, reducing the single-owner query from O(N) over all instances to O(M) where M is the small subset of instances for that specific user.

## 2024-05-18 - [Optimize sequential await in loops to concurrent asyncio.gather]
**Learning:** Calling independent `await` statements inside a `for` loop across multiple network peers causes an O(n) blocking bottleneck on the handler, significantly slowing down features like `/collab broadcast` and `/bridgenet broadcast`.
**Action:** Always collect independent coroutines in a list and invoke them concurrently using `await asyncio.gather(*coroutines)` to change the total execution time from the sum of all calls to just the time of the slowest call.

## 2025-03-03 - [Optimize SQLite Database Initialization]
**Learning:** `server.py` was unconditionally executing `CREATE TABLE IF NOT EXISTS` commands inside `_ag_queue_task` every time a new task was queued. This caused severe I/O bottlenecks and redundant disk operations.
**Action:** Introduced a module-level `_ag_db_initialized` boolean flag so the database schema initialization (`executescript` / `CREATE TABLE` statements) only runs once per process lifecycle on the first execution.

## 2025-03-03 - [Optimize agent search by pushing filtering to SQLite]
**Learning:** `get_agent_by_name()` in `agent_registry.py` used `fetchall()` to retrieve all agents from SQLite and iterated over them in Python to find a matching agent by partial name or exact ID. This results in an O(N) memory allocation and O(N) linear search time, creating a bottleneck as the agent list grows.
**Action:** Push filtering down to SQLite using parameterized queries with `LOWER(name) LIKE ? OR LOWER(id) = ?` and `LIMIT 1` with `fetchone()` to perform the search efficiently within the database engine and drastically cut down memory usage and data transfer overhead.

## 2025-03-03 - [Optimize re.sub execution]
**Learning:** Calling `re.sub(pattern, ...)` inside a frequently-executed function with a raw string pattern forces Python to repeatedly retrieve the compiled regex from its internal cache (and compile it if evicted), introducing unnecessary overhead.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level to avoid repeated compilation and cache-lookup overhead during runtime execution.

## 2025-04-14 - [Optimize _webhook_secret_token]
**Learning:** Functions that hash a fixed secret token (like calculating SHA-256 on the Telegram bot token) shouldn't be recalculated repeatedly on every request. Since `_webhook_secret_token` is called on every incoming webhook in `server.py`, hashing on every request decreases throughput needlessly.
**Action:** Used `@functools.lru_cache` decorator on deterministic hash-generating functions that take fixed configuration constants. This saves redundant compute cycles and improves API throughput.
