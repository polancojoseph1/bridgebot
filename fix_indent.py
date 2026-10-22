with open("setup_wizard_ui.py", "r") as f:
    content = f.read()

content = content.replace("from slowapi import Limiter\nfrom slowapi.util import get_remote_address", "    from slowapi import Limiter\n    from slowapi.util import get_remote_address")
with open("setup_wizard_ui.py", "w") as f:
    f.write(content)
