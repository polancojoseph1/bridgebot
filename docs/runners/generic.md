# Generic CLI Runner

## When to use

Use `CLI_RUNNER=generic` when you want to wrap any command-line tool that accepts a text prompt — local LLMs, custom scripts, or any AI CLI not officially supported.

## .env settings

```env
CLI_RUNNER=generic
CLI_COMMAND=your-binary        # the command to run
# BOT_NAME=MyBot              # display name in Telegram
```

## How it works

The bridge calls:
```bash
<CLI_COMMAND> "<prompt>"
```

The prompt is passed as the last positional argument. The bridge captures stdout and sends it to Telegram.

## Requirements for your CLI

- Accepts the prompt as the last argument (or via stdin — see below)
- Writes the response to stdout
- Exits with code 0 on success

## Stdin mode

If your tool reads from stdin instead of a positional argument, wrap it in a shell script:

```bash
#!/bin/bash
# my-ai-wrapper.sh
echo "$1" | my-ai-tool --interactive
```

Then set `CLI_COMMAND=my-ai-wrapper.sh`.

## Examples

### Local Ollama model

```bash
#!/bin/bash
# ollama-wrapper.sh
curl -s http://localhost:11434/api/generate \
  -d "{\"model\": \"llama3.2\", \"prompt\": \"$1\", \"stream\": false}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
```

```env
CLI_RUNNER=generic
CLI_COMMAND=./ollama-wrapper.sh
```

### Any shell command

```bash
#!/bin/bash
# my-tool.sh
my-ai-cli respond "$1"
```

## Limitations

- Streaming (partial output in real-time) is not available for generic runners
- Tool use / file access depends entirely on your CLI's own capabilities
- `/model` switching does not apply
