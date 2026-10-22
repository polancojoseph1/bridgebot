import re

with open("setup_wizard_ui.py", "r") as f:
    content = f.read()

# Add Limiter and Request import
content = content.replace("from fastapi import FastAPI", "from fastapi import FastAPI, Request\nfrom slowapi import Limiter\nfrom slowapi.util import get_remote_address")

# Initialize Limiter
content = content.replace("app = FastAPI(title=\"Bridgebot Setup\", docs_url=None, redoc_url=None)", "app = FastAPI(title=\"Bridgebot Setup\", docs_url=None, redoc_url=None)\n_limiter = Limiter(key_func=get_remote_address)\napp.state.limiter = _limiter")


# Add @limiter to routes and Request to signatures
routes = [
    ("def get_config():", "@_limiter.limit(\"30/minute\")\ndef get_config(request: Request):"),
    ("def save_config(req: SaveRequest):", "@_limiter.limit(\"30/minute\")\ndef save_config(request: Request, req: SaveRequest):"),
    ("def detect_qwen():", "@_limiter.limit(\"30/minute\")\ndef detect_qwen(request: Request):"),
    ("def clear_config(req: SaveRequest):", "@_limiter.limit(\"30/minute\")\ndef clear_config(request: Request, req: SaveRequest):"),
    ("def generate_bc_key():", "@_limiter.limit(\"30/minute\")\ndef generate_bc_key(request: Request):"),
    ("def bc_info():", "@_limiter.limit(\"30/minute\")\ndef bc_info(request: Request):"),
    ("async def wa_status():", "@_limiter.limit(\"30/minute\")\nasync def wa_status(request: Request):"),
    ("async def wa_qr_proxy():", "@_limiter.limit(\"30/minute\")\nasync def wa_qr_proxy(request: Request):"),
    ("def save_wa_config(req: WaSaveRequest):", "@_limiter.limit(\"30/minute\")\ndef save_wa_config(request: Request, req: WaSaveRequest):"),
    ("async def wa_pairing_code():", "@_limiter.limit(\"30/minute\")\nasync def wa_pairing_code(request: Request):"),
    ("async def restart_wa_bridge():", "@_limiter.limit(\"30/minute\")\nasync def restart_wa_bridge(request: Request):"),
    ("def get_wa_config():", "@_limiter.limit(\"30/minute\")\ndef get_wa_config(request: Request):"),
    ("def serve_ui():", "@_limiter.limit(\"30/minute\")\ndef serve_ui(request: Request):")
]

for old, new in routes:
    content = content.replace(old, new)

with open("setup_wizard_ui.py", "w") as f:
    f.write(content)
