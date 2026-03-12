# Qwen Coder Runner

## Setup

```bash
npm install -g @qwen-code/qwen-code
qwen  # opens browser — log in with your qwen.ai account
```

## .env settings

```env
CLI_RUNNER=qwen
# CLI_COMMAND=qwen            # auto-detected
# BOT_NAME=Qwen               # auto-detected
```

## Features

| Feature | Status |
|---------|--------|
| Streaming responses | Yes |
| Tool use (file read/write, shell) | Yes |
| Chrome browser integration | No |
| Voice messages | Yes (with ffmpeg) |
| Image generation | Yes (with `GEMINI_API_KEY`) |
| Multi-instance | Yes |

## Pricing

**1000 free requests per day** via qwen.ai OAuth — no credit card required.

Paid tiers available at [qwen.ai](https://qwen.ai).

## Authentication

Qwen Coder uses browser-based OAuth via qwen.ai. Run `qwen` once to authenticate. The token is stored locally (similar to Gemini/Claude). Re-run `qwen` if your session expires.

## Subprocess flags

```bash
qwen --yolo --output-format stream-json "<prompt>"
```

`--yolo` auto-approves tool calls. `--output-format stream-json` enables streaming.

## Troubleshooting

- **"qwen: command not found"** — reinstall: `npm install -g @qwen-code/qwen-code`
- **Auth expired** — run `qwen` in terminal to re-authenticate
- **Rate limit hit** — 1000 requests/day on free tier; check your usage at qwen.ai
