"""tg-cli-bridge CLI — install and manage bot instances as macOS LaunchAgents."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>server:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>{port}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{project_dir}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>{home}</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>{project_dir}/.venv/lib/python{pyver}/site-packages</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>{log}</string>
    <key>StandardErrorPath</key>
    <string>{err}</string>
</dict>
</plist>
"""


def _python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def cmd_install(args) -> None:
    name = args.name
    port = args.port
    project_dir = Path(__file__).parent.resolve()
    python = sys.executable
    home = str(Path.home())
    pyver = _python_version()

    logs_dir = Path.home() / "Library" / "Logs" / "tg-cli-bridge"
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    logs_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    label = f"tg-cli-bridge.{name}"
    plist_path = agents_dir / f"{label}.plist"
    log_path = logs_dir / f"{name}.log"
    err_path = logs_dir / f"{name}.err.log"

    plist = PLIST_TEMPLATE.format(
        label=label,
        python=python,
        port=port,
        project_dir=str(project_dir),
        home=home,
        pyver=pyver,
        log=str(log_path),
        err=str(err_path),
    )
    plist_path.write_text(plist)
    print(f"Wrote plist: {plist_path}")

    result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Loaded: {label}")
        print(f"Logs:   {log_path}")
        print(f"        {err_path}")
        print(f"\nTo unload:  launchctl unload {plist_path}")
        print(f"To restart: launchctl unload {plist_path} && sleep 2 && launchctl load {plist_path}")
    else:
        print(f"launchctl load failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def cmd_uninstall(args) -> None:
    name = args.name
    label = f"tg-cli-bridge.{name}"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"

    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

    if plist_path.exists():
        plist_path.unlink()
        print(f"Removed: {plist_path}")
    else:
        print(f"Plist not found: {plist_path}")

    print(f"Uninstalled: {label}")


def cmd_list(args) -> None:
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    plists = sorted(agents_dir.glob("tg-cli-bridge.*.plist"))
    if not plists:
        print("No tg-cli-bridge instances installed.")
        return
    print(f"{'NAME':<20} {'PLIST'}")
    for p in plists:
        name = p.stem.removeprefix("tg-cli-bridge.")
        print(f"{name:<20} {p}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tg-cli-bridge",
        description="Manage tg-cli-bridge bot instances as macOS LaunchAgents",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    install_p = sub.add_parser("install", help="Install a named bot instance as a LaunchAgent")
    install_p.add_argument("--name", required=True, help="Instance name (e.g. claude, gemini)")
    install_p.add_argument("--port", default="8585", help="Port to run uvicorn on (default: 8585)")

    uninstall_p = sub.add_parser("uninstall", help="Remove a named LaunchAgent instance")
    uninstall_p.add_argument("--name", required=True, help="Instance name to remove")

    sub.add_parser("list", help="List installed tg-cli-bridge LaunchAgent instances")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install(args)
    elif args.command == "uninstall":
        cmd_uninstall(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
