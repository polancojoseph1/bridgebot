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

## 2025-05-01 - [Resolve N+1 query patterns in agent skills retrieval]
**Learning:** `build_skills_prompt` iteratively called `get_skill(name)` for every skill required by an agent, leading to an O(N) database query bottleneck (the N+1 query problem) due to executing a separate SQLite `SELECT` query per skill name requested.
**Action:** Implemented a batch retrieval function `get_skills` using an `IN` clause with parameterized placeholders (`','.join('?' * len(ids))`). Paired this with a local dictionary lookup inside `build_skills_prompt` to transform O(N) database lookups into a single query and achieve O(1) in-memory retrieval during assembly.

## 2025-05-29 - [Optimize InstanceManager O(N log N) sorting bottleneck]
**Learning:** Checking instance properties across all active instances globally (e.g. `_is_any_processing()`, `_total_queue_size()`, or looking up agents by ID) using `instances.list_all()` introduces an unnecessary O(N log N) sorting overhead because `list_all()` returns a sorted list of instances. Using `iter_all()` which returns an unsorted list avoids this. It is also CRITICAL that `iter_all()` returns a `list()` snapshot (like `list(self._instances.values())`) and not an iterator, to prevent `RuntimeError: dictionary changed size during iteration` if an asyncio yield point happens inside the iteration loop.
**Action:** Use `instances.iter_all()` instead of `list_all()` for global iteration operations where order doesn't matter, and always ensure it returns a snapshot list to allow safe `await`ing during the loop.
