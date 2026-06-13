# Nightly Log

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
