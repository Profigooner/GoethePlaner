# AgentBoard

AgentBoard is a local PySide6 desktop application for managing OpenCode-based
multi-agent coding tasks. It improves a rough task prompt, creates specialized
subtasks, runs agents without blocking the GUI, streams logs and progress, shows
Git changes, runs tests, and provides an explicit accept or reject decision.

The MVP can run entirely in mock mode, so OpenCode is optional.

## Features

- Local repository folder selection
- Deterministic prompt clarification and task planning
- Prompt Optimizer, Planner, Backend, Frontend, Tester, and Reviewer agents
- Responsive `QThread` workflow with Qt signals and slots
- Per-agent and overall progress
- Live stdout/stderr logs
- Configurable OpenCode CLI adapter
- Automatic mock fallback when OpenCode is unavailable
- Git status, changed-file, staged diff, and working-tree diff views
- Background test command execution
- Local accept action with no automatic commit or push
- Confirmed reject action that preserves the captured dirty baseline

## Requirements

- Python 3.10 or newer
- Git for repository inspection and reject support
- OpenCode only when using Auto or OpenCode mode

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Launch

```bash
source .venv/bin/activate
python -m agentboard
```

Then:

1. Select a local repository.
2. Enter a programming task.
3. Choose `Mock`, `Auto`, or `OpenCode`.
4. Select **Create Task**.
5. Review the optimized prompt, subtasks, logs, changed files, and diff.
6. Run an explicit test command if needed.
7. Accept or reject the result.

`Auto` uses OpenCode when the configured executable is available and otherwise
uses the mock runner. `OpenCode` reports an error when the executable cannot be
found. `Mock` never invokes OpenCode.

## Configuration

Configuration is read from environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `AGENTBOARD_OPENCODE_COMMAND` | OpenCode command template | `opencode run --dir {repo_path} --agent {agent_name} {prompt}` |
| `AGENTBOARD_MOCK_DELAY` | Seconds per mock progress step | `0.2` |
| `AGENTBOARD_TEST_COMMAND` | Initial test command shown in the UI | Empty |

Supported OpenCode command placeholders are:

- `{repo_path}`
- `{agent_name}`
- `{prompt}`

Example:

```bash
export AGENTBOARD_OPENCODE_COMMAND='opencode run --dir {repo_path} --agent {agent_name} {prompt}'
export AGENTBOARD_TEST_COMMAND='python -m unittest discover -v'
python -m agentboard
```

Command templates and test commands are parsed into argument arrays and executed
with `shell=False`.

## Safety

- AgentBoard does not store API keys.
- It does not commit, push, reset a repository, or run a shell.
- Accept only records a local decision.
- A Git baseline is captured before executable agents start.
- Reject restores tracked paths to that baseline.
- Files created after the baseline are moved to
  `<system temp>/agentboard-rejected/<task-id>/` instead of being deleted.
- Pre-existing untracked and modified files are restored to their captured
  content.

Do not edit the same files outside AgentBoard while a task is running. Concurrent
edits made after baseline capture cannot be distinguished from agent changes.

## Tests

```bash
source .venv/bin/activate
python -m unittest discover -v
```

The suite covers models, configuration, prompt planning, runner selection, Git
inspection, baseline restoration, test streaming, the complete mock workflow,
and offscreen Qt window construction.

## Architecture

```text
agentboard/
  main.py
  app/
    ui/       PySide6 widgets only
    core/     Workflow, OpenCode, Git, and test services
    models/   Qt-independent task and agent state
    utils/    Configuration and logging
tests/
ROADMAP.md
```

See [ROADMAP.md](ROADMAP.md) for implementation order, boundaries, milestone
status, and safety decisions.

