## Installation

Install uv with standalone installers:

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# On Windows.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Initialize virtual environment and install dependencies:
```bash
# cd into repo before running this
$ uv sync
```

## Run Project

###### Usage

```bash
$ uv run where-it-went
```

## Development

Run tests:
```bash
$ uv run pytest
```

Run linter and formatter:
```bash
# linter
$ uv run ruff check --fix
# formatter
$ uv run ruff format
```

Run type checker:
```bash
$ uv run basedpyright
```

## For Vscode

Install the basedpyright extension: https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright

Install the ruff extension: https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff

Open the command palette (`Ctrl+Shift+P`) and run the `Preferences: Open User Settings (JSON)` command to open your settings config

Add this snippet to your config to format and lint your files on save:
```json
"[python]": {
  "editor.defaultFormatter": "charliermarsh.ruff",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports.ruff": "explicit"
  }
}
```