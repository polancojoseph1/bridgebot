with open("setup_wizard_ui.py", "r") as f:
    content = f.read()

# Add missing import Request in FastAPI
if "from fastapi import FastAPI, Request" not in content:
    content = content.replace("from fastapi import FastAPI", "from fastapi import FastAPI, Request\nfrom slowapi import Limiter\nfrom slowapi.util import get_remote_address")

with open("setup_wizard_ui.py", "w") as f:
    f.write(content)
