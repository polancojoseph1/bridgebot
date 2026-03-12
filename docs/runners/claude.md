# Claude Code Runner

## Setup

```bash
npm install -g @anthropic-ai/claude-code
claude  # authenticate — opens browser for Anthropic login
```

## .env settings

```env
CLI_RUNNER=claude
# CLI_COMMAND=claude          # auto-detected
# BOT_NAME=Claude             # auto-detected
```

## Features

| Feature | Status |
|---------|--------|
| Streaming responses | Yes |
| Tool use (file read/write, shell) | Yes |
| Chrome browser integration | Yes (`CHROME_ENABLED=true`) |
| Voice messages | Yes (with ffmpeg) |
| Image generation | Yes (with `GEMINI_API_KEY`) |
| Multi-instance | Yes |

## Chrome integration

Claude Code can control a Chrome browser tab. Set in `.env`:
```env
CHROME_ENABLED=true
```

Toggle live with `/chrome` in Telegram.

## Model switching

```
/model sonnet    → claude-sonnet-4-5-20251022
/model opus      → claude-opus-4-6
```

## Authentication

Claude Code uses Anthropic's browser-based OAuth. Run `claude` once to authenticate. The token is stored in `~/.claude/`. No API key is needed unless you set up an enterprise API key.

## Subprocess flags

The runner calls:
```bash
claude -p "<prompt>" --output-format stream-json [--model <model>]
```

`-p` puts Claude in non-interactive "print" mode. `--output-format stream-json` streams JSON events so the bridge can show partial responses in real time.

## Troubleshooting

- **"claude: command not found"** — reinstall: `npm install -g @anthropic-ai/claude-code`
- **Stuck processes** — use `/kill` in Telegram, or `pkill -f "claude -p"`
- **Auth expired** — run `claude` in terminal to re-authenticate
