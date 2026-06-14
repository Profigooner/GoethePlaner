# Nightly Log

## June 14, 2026 - Production Project Workflow and IDE-style UI

### Completed

- Added `PRODUCT_REDESIGN.md` and Stage 12 to the roadmap.
- Added explicit project resource status, project documents, repository
  analysis, task completion summaries, and update suggestion models.
- Added read-only detection for project docs, Python/Node markers, common
  frameworks, Git state, missing Roadmap, and missing agent context.
- Reworked New Project into Existing Project and New Project paths.
- Added guided Roadmap and Init onboarding for new projects.
- Replaced project cards plus the task rail with one expandable project tree.
- Added first-class Project Overview, Roadmap, Init, and Task Detail views.
- Added Roadmap edit, requirement, completion, reorder, import, export, agent,
  and task-conversion actions.
- Removed the permanent right inspector and removed Diff and Review pages.
- Added resizable Terminal, Logs, Prompt, Output, Tests, and Problems bottom
  tools with single-tool toggle behavior.
- Added post-task Roadmap and Init suggestions that remain unapplied until user
  acceptance.
- Preserved mock, OpenCode, Git baseline, test, accept, reject, and agent review
  workflows.

### Safety

- Existing project analysis and import do not write files.
- Task completion never rewrites project documents.
- Suggestion acceptance changes in-memory context only.
- Roadmap export and Init apply retain existing confirmations and stale checks.

### Verification

- 49 tests pass, including focused analysis, project tree, bottom tools, removed
  panels, Roadmap modification, and unapplied suggestion coverage.
- Python compilation and whitespace checks pass.
- A populated `1500x920` offscreen render was inspected.

## June 14, 2026 - Agent-Driven Roadmap and Init Review

### Completed

- Added `PRODUCT_CORRECTION.md` and Stage 11 to the roadmap.
- Replaced deterministic project templates with Roadmap and Init agent services.
- Added `RoadmapDraft`, `InitDraft`, `ProposedFile`, statuses, feedback history,
  timestamps, diagnostics, and accepted project state.
- Added bounded repository context, safe `plan` prompts, strict JSON parsing,
  and repository-aware mock drafts.
- Added dedicated OpenCode generation and revision methods.
- Added exact command logging plus separate stdout and stderr capture.
- Added Roadmap and Init review dialogs with background workers.
- Added roadmap acceptance, revision, regeneration, and accepted-only export.
- Added Init proposal selection, content and diff preview, revision,
  regeneration, draft export, and confirmed selected-file apply.
- Added path validation, explicit overwrite approval, and stale-file detection.
- Updated dashboard actions to `Create Roadmap` and `Run Init Agent`.

### Verification

- 41 unit, integration, workflow, agent, safety, and offscreen Qt tests pass.
- Existing coding-task orchestration, Git baseline, test, accept, and reject
  behavior remains covered.

### Safety

- Draft calls do not modify the repository.
- Roadmaps cannot be exported before acceptance.
- Init apply requires explicit confirmation and writes selected files only.
- Existing Init targets require explicit approval and unchanged reviewed content.
- Subprocesses remain argument-list based with `shell=False`.

## June 14, 2026 - UI/UX Redesign

### Completed

- Created `UI_SPEC.md` with the visual language, layout, tokens, spacing,
  typography, component inventory, hierarchy, and implementation order.
- Generated and saved the design reference at `docs/ui-concept.png`.
- Added a backward-compatible in-memory `Project` model.
- Added project ownership and update timestamps to tasks.
- Extended agent state with task ownership, logs, result, and timing fields.
- Added project navigation, New Project, and New Task flows.
- Replaced the permanent repository/task form with a project-first dashboard.
- Added task cards with status, progress, agent count, summary, and update time.
- Redesigned agent cards with activity, live log preview, elapsed time, result,
  semantic status, and thin progress indicators.
- Added a persistent inspector for logs, prompt, subtasks, changed files, diff,
  tests, and review.
- Added centralized theme tokens and application QSS.
- Added glass panels, semantic badges, progress pills, empty states, hover
  states, selected states, and focused creation dialogs.
- Renamed the visible desktop product to GoethePlaner while retaining the
  internal package name for compatibility.
- Saved the verified implementation screenshot at
  `docs/goetheplaner-dashboard.png`.

### Main Changed Files

- `UI_SPEC.md`
- `ROADMAP.md`
- `README.md`
- `agentboard/main.py`
- `agentboard/app/models/project.py`
- `agentboard/app/models/task.py`
- `agentboard/app/models/agent.py`
- `agentboard/app/ui/theme.py`
- `agentboard/app/ui/components.py`
- `agentboard/app/ui/sidebar.py`
- `agentboard/app/ui/task_card.py`
- `agentboard/app/ui/agent_card.py`
- `agentboard/app/ui/dialogs.py`
- `agentboard/app/ui/task_dashboard.py`
- `agentboard/app/ui/main_window.py`
- `agentboard/app/ui/log_viewer.py`
- `agentboard/app/ui/diff_viewer.py`
- `tests/test_models_config.py`
- `tests/test_workflow_and_ui.py`

### Verification

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -v`
- `.venv/bin/python -m compileall -q agentboard tests`
- `git diff --check`
- 18 tests passed.
- Populated UI render at `1586x992`
- Compact desktop render at `1440x900`
- Visual comparison against `docs/ui-concept.png`

### Visual Fidelity Ledger

| Comparison point | Concept evidence | Final render evidence | Resolution |
| --- | --- | --- | --- |
| Product hierarchy | Sidebar, task rail, task detail, inspector | Same four stable regions | Matched |
| Palette and surfaces | Midnight background, blue-violet glass panels | Centralized dark QSS with subtle radial depth | Matched within Qt constraints |
| Agent anatomy | Six cards with role, state, progress, activity, logs, time | Same fields and two-column concept layout | Matched |
| Inspector | Seven tabs, log controls, console, action footer | Seven tabs, source/search/clear controls, console, fixed footer | Matched |
| Task/project metadata | Project status, task progress, agent count | Active-task count, status dot, task status/progress/agent count | Matched |
| Compact layout | Not shown in the concept | One full-width agent column at `1440x900` | Intentional responsive adaptation |
| Glass blur | Native-style frosted backdrop | Layered translucent fills and borders | Intentional Qt adaptation |

Above-the-fold copy uses only product and workflow labels from the request or the
design concept. No marketing copy, decorative badges, or unrelated metrics were
added.

### Known Limitations

- Projects and tasks are in-memory only and reset when the app closes.
- Qt does not provide portable native backdrop blur, so the glass treatment uses
  layered translucent surfaces and borders.
- Inspector tabs use the compact labels `Tasks` and `Files` at desktop width;
  full names are available in tooltips.
- Agent work units are visually parallel, while the current MVP dispatcher still
  runs executable subtasks sequentially.
- No real OpenCode task was started during visual QA; command construction,
  availability, fallback, and the existing runner tests remain covered.

## June 14, 2026 - Advanced Agent Planning and Orchestration

### Completed

- Added `AGENT_SPEC.md` and `PROJECT_WORKFLOW.md`.
- Added a centralized registry with 17 professional agent definitions,
  permissions, risk levels, prompts, keywords, and safe OpenCode mappings.
- Added deterministic planner selection for language, UI, backend, data, ML,
  security, database, operations, testing, debugging, review, and docs work.
- Added a two-step task Plan dialog with original and optimized prompts,
  planner notes, recommendation reasons, manual selection, and graph preview.
- Extended project, task, and agent-run state for goals, plans, selections,
  execution metadata, permissions, risk, results, and timing.
- Added read-only roadmap and init generators plus confirmed, exclusive creation
  for selected missing init files.
- Added project Roadmap, Init Plan, and Suggested Tasks views and actions.
- Replaced the fixed six-agent worker with selected staged orchestration.
- Added parallel mock implementation execution and sequential shared-directory
  OpenCode execution.
- Ordered Test Engineer, Code Reviewer, and Documentation Writer after
  implementation.
- Added safe `plan`/`build` mapping with optional explicit JSON configuration.

### Verification

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -v`
- `.venv/bin/python -m compileall -q agentboard tests`
- `git diff --check`
- 32 tests passed.
- Rendered and inspected the populated project planning dashboard.
- Rendered and inspected the styled task Plan dialog.

### Safety

- No automatic roadmap or init writes.
- Existing init files are skipped even when selected.
- Exports require explicit replacement confirmation.
- Real OpenCode code-modifying stages remain sequential.
- No shell execution, commit, push, force push, or destructive command was
  introduced.
