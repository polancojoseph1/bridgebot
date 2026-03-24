import asyncio
import time
import httpx
import uvicorn
import threading
import sys
from setup_wizard_ui import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=7892, log_level="warning")

async def test():
    # Start server in thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    await asyncio.sleep(2) # Wait for server to start

    async with httpx.AsyncClient() as client:
        start_time = time.time()

        # Fire both concurrently
        task1 = asyncio.create_task(client.post("http://127.0.0.1:7892/api/restart-wa-bridge"))
        await asyncio.sleep(0.1) # Let the restart start

        # Fire a quick config request
        config_start = time.time()
        task2 = asyncio.create_task(client.get("http://127.0.0.1:7892/api/config"))

        await task2
        config_time = time.time() - config_start

        await task1
        restart_time = time.time() - start_time

        print(f"BASELINE_CONFIG_TIME={config_time:.3f}")
        print(f"BASELINE_RESTART_TIME={restart_time:.3f}")

if __name__ == "__main__":
    asyncio.run(test())