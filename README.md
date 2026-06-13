# GoethePlaner

GoethePlaner is a local PySide6 control center for OpenCode-based multi-agent
coding work. Projects connect local repositories, tasks describe desired code
changes, and specialized agents optimize prompts, plan work, implement changes,
run tests, and review results without blocking the desktop UI.

The application can run entirely in mock mode, so OpenCode is optional.

![GoethePlaner project dashboard](docs/goetheplaner-dashboard.png)

The visual implementation follows [UI_SPEC.md](UI_SPEC.md). The generated design
reference is available at [docs/ui-concept.png](docs/ui-concept.png).

## Workflow

```text
Project
  -> Tasks
    -> Prompt Optimizer, Planner, Backend, Frontend, Tester, Reviewer
      -> Logs, Prompt, Subtasks, Changed Files, Diff, Tests, Review
```

1. Create a project and select its local repository.
2. Create a task inside the selected project.
3. Choose `Auto`, `Mock`, or `OpenCode`.
4. Monitor overall and per-agent progress.
5. Inspect logs, optimized prompt, subtasks, changed files, diff, and tests.
6. Accept or reject the generated result.

Projects and tasks are stored in memory in the current release.

## Features

- Dark translucent project-first desktop dashboard
- In-memory project navigation and task collections
- Focused New Project and New Task dialogs
- Prompt Optimizer, Planner, Backend, Frontend, Tester, and Reviewer agents
- Per-agent activity, progress, log preview, elapsed time, and result state
- Responsive `QThread` workflow with Qt signals and slots
- Live stdout/stderr logs with source-aware colors
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

The Python package retains the internal `agentboard` name for compatibility, but
the desktop product name is GoethePlaner.

## Execution Modes

- `Auto`: uses OpenCode when the configured executable is available and
  otherwise uses the mock runner.
- `Mock`: runs a simulated local workflow and never invokes OpenCode.
- `OpenCode`: requires the configured OpenCode executable and reports a clear
  error when it is unavailable.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `AGENTBOARD_OPENCODE_COMMAND` | OpenCode command template | `opencode run --dir {repo_path} --agent {agent_name} {prompt}` |
| `AGENTBOARD_MOCK_DELAY` | Seconds per mock progress step | `0.2` |
| `AGENTBOARD_TEST_COMMAND` | Initial test command shown in the UI | Empty |

Supported OpenCode command placeholders:

- `{repo_path}`
- `{agent_name}`
- `{prompt}`

Example:

```bash
export AGENTBOARD_TEST_COMMAND='python -m unittest discover -v'
python -m agentboard
```

Command templates and test commands are parsed into argument arrays and executed
with `shell=False`.

## Safety

- GoethePlaner does not store API keys.
- It does not commit, push, reset a repository, or run a shell.
- Accept only records a local decision.
- A Git baseline is captured before executable agents start.
- Reject restores tracked paths to that baseline.
- Files created after the baseline are moved to
  `<system temp>/agentboard-rejected/<task-id>/` instead of being deleted.
- Pre-existing untracked and modified files are restored to their captured
  content.

Do not edit the same files outside GoethePlaner while a task is running.
Concurrent edits made after baseline capture cannot be distinguished from agent
changes.

## Tests

```bash
source .venv/bin/activate
QT_QPA_PLATFORM=offscreen python -m unittest discover -v
```

The suite covers models, project ownership, dialogs, configuration, prompt
planning, runner selection, Git inspection, baseline restoration, test
streaming, complete mock workflows, and headless Qt window construction.

## Architecture

```text
agentboard/
  main.py
  app/
    ui/
      theme.py          Centralized design tokens and QSS
      components.py     Glass panels, badges, progress, empty states
      sidebar.py        Project navigation
      task_card.py      Task rail cards
      agent_card.py     Live agent execution cards
      dialogs.py        New Project and New Task flows
      task_dashboard.py Main screen composition
    core/               Workflow, OpenCode, Git, and test services
    models/             Project, task, agent, and event state
    utils/              Configuration and logging
tests/
```

See [ROADMAP.md](ROADMAP.md) for milestones and safety boundaries.

