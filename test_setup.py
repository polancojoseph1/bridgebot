import subprocess
result = subprocess.run(["python3", "-m", "py_compile", "setup_wizard_ui.py"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
