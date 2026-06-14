# AgentBoard Roadmap

## Purpose

AgentBoard is a local PySide6 desktop application for coordinating OpenCode-based
multi-agent coding workflows. It accepts a repository and a rough task, improves
the prompt, plans subtasks, runs specialized agents, streams progress and logs,
shows repository changes, runs tests, and lets the user accept or reject the
result.

This file is the implementation contract for the MVP. Work proceeds in the order
below. A stage is marked complete only after its code and verification are done.

## Architecture

```text
agentboard/
  main.py                    Application entry point
  app/
    ui/                      Qt widgets and presentation logic
    core/                    Workflow, process, git, and test services
    models/                  Typed task, agent, and event state
    utils/                   Configuration and logging helpers
tests/                       Unit tests for non-visual behavior
```

### Layer responsibilities

- `app/ui`: Displays state and emits user intent. It must not construct shell
  commands or perform blocking repository/process work.
- `app/core/task_manager.py`: Owns workflow state transitions and coordinates
  optimizer, planner, dispatcher, review, git inspection, and tests.
- `app/core/opencode_runner.py`: Centralizes command construction and streams
  OpenCode output. It is the only module that knows the CLI command shape.
- `app/core/agent_dispatcher.py`: Runs planned agents sequentially in a worker
  thread for the MVP and translates runner callbacks into workflow events.
- `app/core/git_manager.py`: Provides read-only status/diff operations plus a
  deliberately scoped reject operation that restores only changes captured by
  the current task.
- `app/core/test_runner.py`: Runs a configured test command without a shell and
  streams output.
- `app/models`: Contains serializable task, subtask, agent, status, and event
  types. Models do not import Qt.
- `app/utils/config.py`: Loads environment-based command configuration. Secrets
  are never stored in source.

### Concurrency model

- The main Qt thread handles widgets only.
- A `QThread`-hosted workflow worker performs optimization, planning, agent
  execution, git inspection, and test execution.
- Worker-to-UI communication uses Qt signals carrying immutable snapshots or
  simple values.
- Subprocess output is read incrementally so logs remain live.
- Cancellation is cooperative. The active runner can terminate its own child
  process; no broad process-kill commands are used.

### Safety boundaries

- Commands are represented as argument lists and run with `shell=False`.
- Repository paths are validated before execution.
- API keys and credentials are never hardcoded or logged.
- AgentBoard never deletes files.
- Git inspection is read-only.
- Reject is disabled unless a task baseline was captured, and it only restores
  paths changed by the task. Pre-existing user changes are preserved.
- Accept records the decision in the UI; it does not commit or push.
- Mock mode is the default fallback when OpenCode is unavailable.

## Coding Rules

1. Keep UI, orchestration, process execution, repository operations, and models
   separate.
2. Keep blocking work out of the main Qt thread.
3. Use Qt signals/slots for cross-thread updates.
4. Keep OpenCode command construction centralized and configurable.
5. Use type hints and small focused functions.
6. Prefer standard-library facilities and simple Qt widgets.
7. Add comments only for non-obvious behavior or safety constraints.
8. Do not run destructive commands automatically.
9. Preserve pre-existing repository changes.
10. Add focused tests for command construction, planning, state, and git parsing.

## Implementation Stages

### Stage 1: Roadmap

- [x] Define architecture, concurrency, safety, milestones, and implementation
  order in `ROADMAP.md`.

### Stage 2: Project foundation

- [x] Create the package structure, `requirements.txt`, and entry point.
- [x] Add configuration and logging helpers.
- [x] Add task, agent, subtask, and event models.

Verification: modules compile and model/config tests pass.

### Stage 3: Minimal desktop shell and task input

- [x] Create the main window and dashboard.
- [x] Add repository picker, task prompt input, mode selection, and Create Task.
- [x] Add task history sidebar and output tabs.

Verification: application starts when PySide6 is installed; UI construction can
be smoke-tested offscreen.

### Stage 4: Mock workflow and real-time UI

- [x] Implement prompt optimization and deterministic task planning.
- [x] Implement agent cards and overall progress.
- [x] Implement a mock runner with streamed logs, progress, and cancellation.
- [x] Run the workflow in a `QThread`.
- [x] Display optimized prompt, subtasks, logs, and final review state.

Verification: an end-to-end mock task reaches completion without blocking the UI.

### Stage 5: OpenCode integration

- [x] Add configurable `OpenCodeRunner` command construction.
- [x] Stream stdout/stderr and support cooperative cancellation.
- [x] Detect OpenCode availability and fall back to mock mode.
- [x] Route agent execution through a runner-neutral dispatcher.

Verification: command construction and unavailable-command fallback tests pass.

### Stage 6: Repository inspection and tests

- [x] Capture a repository baseline before agent execution.
- [x] Add git status, changed-file, and diff inspection.
- [x] Add configurable test command execution with streamed output.
- [x] Refresh repository and test views after agent execution.

Verification: git integration tests use a temporary repository and preserve
pre-existing changes.

### Stage 7: Accept/reject workflow

- [x] Add Accept Changes and Reject Changes actions.
- [x] Keep accept non-destructive and local.
- [x] Restore only task-created modifications on reject.
- [x] Require confirmation before reject and explain preserved baseline changes.

Verification: reject tests prove baseline changes remain untouched.

### Stage 8: Documentation and release verification

- [x] Write setup, launch, configuration, OpenCode, mock-mode, and safety
  documentation in `README.md`.
- [x] Add unit tests and a headless UI smoke test.
- [x] Run compilation and tests.
- [x] Review project structure and update this roadmap with final status.

Verification: the documented launch path works and the complete test suite passes.

## Milestones

| Milestone | Definition | Status |
| --- | --- | --- |
| M1 Foundation | Structure, models, config, and minimal window | Complete |
| M2 Mock MVP | Responsive simulated multi-agent workflow | Complete |
| M3 OpenCode | Configurable real CLI runner with fallback | Complete |
| M4 Repository tools | Diff, changed files, tests, accept/reject | Complete |
| M5 MVP complete | Documentation and verification complete | Complete |

## Current Status

- Active stage: Stage 12 complete
- Last completed stage: Stage 12, Production-grade Project Workflow and
  IDE-style UI Redesign
- Stage 12 completed: June 14, 2026

## Stage 9: UI/UX Redesign

The redesign follows [UI_SPEC.md](UI_SPEC.md) and
[docs/ui-concept.png](docs/ui-concept.png).

### Phase 9.1: Specification

- [x] Inspect the existing UI, architecture, roadmap, and README.
- [x] Render the existing desktop UI as a baseline.
- [x] Generate a complete desktop design concept.
- [x] Define design tokens, hierarchy, components, and implementation order in
  `UI_SPEC.md`.

### Phase 9.2: Models and project navigation

- [x] Add a backward-compatible `Project` model and task ownership fields.
- [x] Add in-memory project selection and task collections.
- [x] Implement the New Project dialog and sidebar navigation.

### Phase 9.3: Workspace architecture

- [x] Replace the permanent task form with a project header and New Task dialog.
- [x] Add a task rail with reusable task cards.
- [x] Compose the task detail and persistent inspector regions.

### Phase 9.4: Visual system and components

- [x] Add centralized theme tokens and application QSS.
- [x] Add glass panels, status badges, toolbar buttons, and empty states.
- [x] Redesign agent cards with activity, log preview, elapsed time, and result.
- [x] Polish logs, prompts, subtasks, files, diff, tests, and review views.

### Phase 9.5: Verification and documentation

- [x] Preserve all mock, OpenCode, worker, Git, test, accept, and reject flows.
- [x] Add project/navigation/dialog coverage.
- [x] Run unit, integration, workflow, and offscreen UI tests.
- [x] Render and compare desktop screenshots at target sizes.
- [x] Update README and `NIGHTLY_LOG.md`.

### Redesign Milestone

| Milestone | Definition | Status |
| --- | --- | --- |
| M6 Premium desktop UI | Project-first glass dashboard with verified workflows | Complete |

### Redesign Verification

- 18 unit, integration, workflow, and offscreen Qt tests pass.
- Python compilation and whitespace checks pass.
- The concept-sized `1586x992` render uses two agent columns.
- The compact `1440x900` render switches to one readable agent column.
- Final implementation screenshot: `docs/goetheplaner-dashboard.png`.
- Completed: June 14, 2026.

## Stage 10: Advanced Agent Planning and Project Orchestration

This phase follows [AGENT_SPEC.md](AGENT_SPEC.md) and
[PROJECT_WORKFLOW.md](PROJECT_WORKFLOW.md).

### Phase 10.1: Architecture contracts

- [x] Inspect the current workflow, UI, models, tests, and project documents.
- [x] Define the professional agent registry, permissions, risk, prompts,
  OpenCode mapping, execution rules, and aggregation in `AGENT_SPEC.md`.
- [x] Define project creation, roadmap, init, planning, execution, and review in
  `PROJECT_WORKFLOW.md`.

### Phase 10.2: Registry and planner selection

- [x] Add the centralized `AgentDefinition` registry.
- [x] Add deterministic rule-based agent selection with reasons.
- [x] Enforce safe built-in OpenCode mappings.

### Phase 10.3: Models and project generators

- [x] Add project goal, roadmap, and init-plan state.
- [x] Add task planner notes, selected agents, and agent-run state.
- [x] Add read-only template-based roadmap and init generators.

### Phase 10.4: Planning and project UI

- [x] Add a task Plan step with recommended, optional, and risky agents.
- [x] Show permissions, risk, selection reason, and execution graph.
- [x] Add Generate Roadmap and Generate Init project actions and views.

### Phase 10.5: Staged execution

- [x] Run prompt optimization and planning before specialized agents.
- [x] Run safe mock implementation agents in parallel.
- [x] Run real OpenCode agents sequentially with safe internal mapping.
- [x] Run test, review, and documentation stages in dependency order.
- [x] Aggregate final results and preserve cancellation behavior.

### Phase 10.6: Verification and handoff

- [x] Add registry, selector, model, generator, parallel execution, and mapping
  tests.
- [x] Preserve all existing tests and safety behavior.
- [x] Update README, UI specification, and nightly log.
- [x] Render and inspect the new planning/project states.

| Milestone | Definition | Status |
| --- | --- | --- |
| M7 Advanced orchestration | Planner-selected agents, project plans, and safe staged execution | Complete |

### Advanced Orchestration Verification

- 32 unit, integration, workflow, orchestration, and offscreen Qt tests pass.
- Mock implementation agents overlap while tests and review respect dependency
  order.
- Real OpenCode execution remains sequential in the shared working directory.
- Internal roles map to `plan` or `build` unless explicitly configured.
- Roadmap and init generation are read-only; init apply uses exclusive creation.
- Project planning and task Plan views were rendered and visually inspected.
- Completed: June 14, 2026.

## Stage 11: Agent-driven Roadmap and Init Review Workflow

This phase corrects the template-based project generators described in
[PRODUCT_CORRECTION.md](PRODUCT_CORRECTION.md).

### Phase 11.1: Product and safety contract

- [x] Document why immediate template generation was the wrong product model.
- [x] Define agent draft, review, revision, acceptance, export, and apply
  boundaries.
- [x] Make overwrite protection and read-only draft behavior explicit.

### Phase 11.2: Draft models and OpenCode integration

- [x] Add `RoadmapDraft`, `InitDraft`, and `ProposedFile` models.
- [x] Add safe Roadmap and Init agent prompts with bounded repository context.
- [x] Add real OpenCode structured-output parsing and realistic mock behavior.
- [x] Capture exact commands, stdout, stderr, progress, and diagnostics.

### Phase 11.3: Roadmap review workflow

- [x] Replace one-click generation with goal and constraints input.
- [x] Show roadmap content, reasoning, observations, milestones, tasks, risks,
  tests, and logs.
- [x] Support feedback revision, regeneration, acceptance, and safe export.

### Phase 11.4: Init review workflow

- [x] Replace generic init templates with repository-aware file proposals.
- [x] Show selectable files, status, content preview, and unified diff.
- [x] Support feedback revision, regeneration, draft export, and confirmed apply.
- [x] Require explicit confirmation before updating every existing target.

### Phase 11.5: Verification and handoff

- [x] Add focused model, prompt, revision, export, apply, mock, and UI tests.
- [x] Preserve the existing task workflow and complete test suite.
- [x] Update README, agent specification, project workflow, UI specification,
  and nightly log.
- [x] Run tests, compilation, and whitespace checks.

| Milestone | Definition | Status |
| --- | --- | --- |
| M8 Agent-reviewed project planning | OpenCode-backed roadmap and init drafts with human acceptance gates | Complete |

### Agent Review Verification

- 41 unit, integration, workflow, agent, safety, and offscreen Qt tests pass.
- Python compilation and whitespace checks pass.
- Populated Roadmap and Init review dialogs were rendered and inspected.
- Existing coding-task, Git baseline, test, accept, and reject workflows remain
  covered.
- Completed: June 14, 2026.

## Stage 12: Production-grade Project Workflow and IDE-style UI Redesign

This phase follows [PRODUCT_REDESIGN.md](PRODUCT_REDESIGN.md).

### Phase 12.1: Product and lifecycle contract

- [x] Document the corrected creation, Roadmap, Init, task-completion, navigation,
  tool-window, model, and safety contracts.
- [x] Define explicit acceptance criteria.

### Phase 12.2: Project analysis and onboarding

- [x] Distinguish existing and new project creation.
- [x] Analyze documentation and language/framework markers without writes.
- [x] Add guided Roadmap and Init onboarding for new projects.
- [x] Add explicit import and missing-context choices for existing projects.

### Phase 12.3: Project lifecycle models

- [x] Add project documents, lifecycle status, analysis state, completion
  summaries, and update suggestions.
- [x] Keep current project, task, draft, mock, and OpenCode contracts compatible.

### Phase 12.4: IDE navigation and workspace

- [x] Replace project cards and the task rail with one project/resource/task tree.
- [x] Add project overview, Roadmap, Init, and task detail workspace views.
- [x] Make Roadmap and Init permanently accessible under every project.

### Phase 12.5: Bottom tool windows

- [x] Remove the permanent right-side inspector.
- [x] Remove Diff and Review pages from the product surface.
- [x] Add resizable Terminal, Logs, Prompt, Output, Tests, and Problems tools.
- [x] Enforce one visible bottom tool and same-button hide behavior.

### Phase 12.6: Living Roadmap and Init

- [x] Add Roadmap edit, requirement, completion, reorder, import, export, agent
  revision, and task-conversion actions.
- [x] Generate Roadmap and Init suggestions after task completion.
- [x] Require explicit acceptance or rejection for every suggestion.

### Phase 12.7: Verification and handoff

- [x] Add focused project analysis, tree navigation, tool-window, lifecycle, and
  suggestion tests.
- [x] Preserve existing orchestration, Git, test, mock, and OpenCode coverage.
- [x] Update README, UI specification, project workflow, and nightly log.
- [x] Run the complete offscreen test suite, compilation, and whitespace checks.

| Milestone | Definition | Status |
| --- | --- | --- |
| M9 Production project workflow | Guided onboarding, living project context, IDE navigation, and bottom tools | Complete |

### Production Redesign Verification

- 49 unit, integration, workflow, lifecycle, safety, and offscreen Qt tests pass.
- Python compilation and whitespace checks pass.
- Existing mock, OpenCode mapping, staged execution, Git baseline, test, accept,
  reject, Roadmap Agent, and Init Agent behavior remains covered.
- A populated `1500x920` render was inspected with the project tree, Roadmap
  workspace, pending suggestions, and bottom tool strip.
- Completed: June 14, 2026.
