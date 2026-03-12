# Codex CLI Runner (OpenAI)

## Setup

```bash
npm install -g @openai/codex
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=sk-...
# Or add to your .env:
# OPENAI_API_KEY=sk-...
```

## .env settings

```env
CLI_RUNNER=codex
OPENAI_API_KEY=sk-your-key-here
# CLI_COMMAND=codex           # auto-detected
# BOT_NAME=Codex              # auto-detected
```

## Features

| Feature | Status |
|---------|--------|
| Streaming responses | Yes |
| Tool use | Yes |
| Chrome browser integration | No |
| Voice messages | Yes (with ffmpeg) |
| Image generation | Yes (with `GEMINI_API_KEY`) |
| Multi-instance | Yes |

## Authentication

Codex CLI uses an OpenAI API key. Unlike Claude and Gemini, there is no browser OAuth — just set `OPENAI_API_KEY` in your environment or `.env` file.

## Subprocess flags

```bash
codex exec --json "<prompt>"
```

## Cost

Codex CLI uses the OpenAI API. You are billed per token at OpenAI's standard rates. There is no free tier.

## Troubleshooting

- **"codex: command not found"** — reinstall: `npm install -g @openai/codex`
- **Authentication errors** — verify `OPENAI_API_KEY` is set and valid
- **Rate limits** — reduce concurrent instances or add a `CLI_TIMEOUT` buffer
