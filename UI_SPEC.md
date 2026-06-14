# GoethePlaner UI Specification

## Design Source

The visual source of truth is [docs/ui-concept.png](docs/ui-concept.png), generated
for this redesign on June 14, 2026. The implementation should preserve its
information hierarchy, dark glass palette, density, typography rhythm, and
three-column working layout while using practical PySide6 widgets.

## Product Hierarchy

```text
Project
  -> Task
    -> Agent runs
      -> Logs, prompts, subtasks, changed files, diff, tests, review
```

- A project owns a repository path and an in-memory task collection.
- A task belongs to exactly one project.
- A task owns prompt state, subtasks, agent state, repository output, tests, and
  review decisions.
- Agent runs expose role, status, progress, activity, recent logs, elapsed time,
  and result.

## Visual Language

GoethePlaner is a calm desktop control center for long-running coding work. It
uses layered dark surfaces, restrained translucency, thin internal highlights,
and blue-violet accents. Glass treatment establishes depth without reducing text
contrast.

Principles:

1. Keep the workspace dense enough for developer work but never cramped.
2. Use open rails and large regional panels instead of wrapping every element in
   a card.
3. Reserve strong blue for selection and primary actions.
4. Use semantic color only for real status.
5. Keep progress visible at project, task, and agent levels.
6. Prefer stable layouts while agents update to avoid visual jumping.
7. Use shadows only on top-level floating surfaces and active cards.

## Layout Structure

Target desktop size: `1440x900` compact working design, with the concept rendered
at `1586x992`. At compact height, the agent area scrolls vertically while keeping
both agent columns fully visible.

The app shell contains four stable regions:

1. **Sidebar**: fixed 220-250 px.
   - Product mark and name.
   - `+ New Project` primary action.
   - Projects, Recent, Settings, About navigation.
   - Project list with selected, active, and idle states.
   - Local workspace identity footer.
2. **Task rail**: 240-300 px inside the central workspace.
   - Compact project header spans task rail and detail.
   - Task list with title, timestamp, status, progress, summary, and agent count.
   - Archived-task affordance at the bottom.
3. **Task detail**: minimum 500 px.
   - Task title and status.
   - Original prompt summary.
   - Overall progress.
   - Two-column agent grid.
4. **Inspector**: 350-460 px.
   - Logs, Prompt, Subtasks, Changed Files, Diff, Tests, Review tabs.
   - Persistent Accept and Reject action footer.

The three work columns use `QSplitter` so users can resize them. At narrow window
widths the inspector remains usable and the task rail contracts before the task
detail.

## Color Tokens

| Token | Value | Use |
| --- | --- | --- |
| `BACKGROUND` | `#080D17` | Window base |
| `BACKGROUND_ELEVATED` | `#0B1220` | Subtle radial/linear background layer |
| `SIDEBAR` | `rgba(8, 15, 27, 238)` | Sidebar rail |
| `PANEL` | `rgba(15, 24, 40, 232)` | Primary glass panels |
| `PANEL_ALT` | `rgba(20, 31, 50, 222)` | Cards and inputs |
| `PANEL_HOVER` | `rgba(27, 42, 66, 238)` | Hovered rows/cards |
| `BORDER` | `rgba(151, 169, 199, 40)` | Hairline borders |
| `BORDER_STRONG` | `rgba(93, 139, 224, 105)` | Active card borders |
| `TEXT_PRIMARY` | `#F5F7FB` | Headings and primary content |
| `TEXT_SECONDARY` | `#A8B3C7` | Body and metadata |
| `TEXT_MUTED` | `#6F7E95` | Disabled and tertiary text |
| `ACCENT` | `#2F81F7` | Selection and primary actions |
| `ACCENT_HOVER` | `#4A93FA` | Primary action hover |
| `ACCENT_PRESSED` | `#2469C7` | Primary action pressed |
| `VIOLET` | `#8B5CF6` | Planning/prompt agent identity |
| `SUCCESS` | `#34D399` | Done, accepted, active |
| `WARNING` | `#F59E0B` | Waiting and warnings |
| `ERROR` | `#F87171` | Failed, reject |
| `CONSOLE` | `#07101D` | Logs/diff/test console |

## Spacing System

Base unit: 4 px.

| Token | Value |
| --- | --- |
| `XS` | 4 px |
| `SM` | 8 px |
| `MD` | 12 px |
| `LG` | 16 px |
| `XL` | 20 px |
| `2XL` | 24 px |
| `3XL` | 32 px |

- Window outer spacing: 12 px.
- Top-level panel gap: 10-12 px.
- Panel inner padding: 16 px.
- Card padding: 12 px.
- Form control height: 36-40 px.
- Sidebar row height: 42 px.
- Agent card minimum height: 178 px.

## Radius and Elevation

- Small controls: 7 px.
- Inputs and buttons: 8 px.
- Cards: 10 px.
- Top-level panels: 13 px.
- Use `QGraphicsDropShadowEffect` only for the selected task card, modal-like
  empty states, and the main primary action when useful.
- Qt does not provide native cross-platform backdrop blur. Use high-opacity
  translucent fills, layered gradients, and subtle borders instead of expensive
  custom blur.

## Typography

Font stack:

1. `SF Pro Display` / `SF Pro Text` when available on macOS.
2. `Inter` when installed.
3. Qt system sans-serif fallback.

Monospace:

1. `SF Mono`.
2. `Menlo`.
3. Qt system fixed font.

Scale:

| Role | Size | Weight |
| --- | --- | --- |
| Product title | 20 px | 700 |
| Project title | 25 px | 700 |
| Task title | 20 px | 650 |
| Section title | 15 px | 650 |
| Card title | 14 px | 650 |
| Body | 13 px | 400 |
| Metadata | 11-12 px | 400-500 |
| Button | 13 px | 600 |
| Console | 11-12 px | 400 |

Avoid uppercase except compact rail labels such as `TASKS` and `PROJECTS`, which
use muted color and modest letter spacing.

## Components

### Foundation

- `GlassPanel`: reusable framed surface with panel variants.
- `StatusBadge`: semantic compact status display.
- `ProgressPill`: thin progress track with optional numeric label.
- `ToolbarButton`: primary, secondary, ghost, and danger variants.
- `EmptyState`: title, explanation, and optional action.

### Project Navigation

- `Sidebar`
- `NavigationRow`
- `ProjectList`
- `ProjectCard`
- `NewProjectDialog`

Project cards show name, abbreviated repository path, active task count through
metadata, a status dot, and selected state.

### Task Workspace

- `ProjectHeader`
- `TaskList`
- `TaskCard`
- `NewTaskDialog`
- `TaskDetail`

Task cards show title, prompt summary, status, progress, assigned-agent count,
and updated time. Task creation belongs to the selected project.

### Agent Execution

- `AgentCard`
- Responsive `AgentGrid`: two columns at the concept width and one full-width
  column when the task detail becomes narrower than 540 px.

Agent cards show:

- Agent name and role.
- Status badge.
- Thin progress line and numeric value.
- Current activity.
- Last two log lines.
- Elapsed time.
- Result badge or summary when terminal.

The grid keeps all six default agents visible as parallel work units. Workflow
execution remains unchanged even where the current MVP dispatches executable
agents sequentially.

### Inspector

- `LogConsole`
- `PromptInspector`
- `SubtaskList`
- `ChangedFilesView`
- `DiffViewer`
- `TestConsole`
- `ReviewView`

The inspector uses a top-aligned tab bar, dark content area, and a stable action
footer. On constrained Qt widths, `Subtasks` and `Changed Files` may appear as
`Tasks` and `Files` with full labels in tooltips. Console surfaces use monospace
typography and source-aware colors.

## Interaction States

- Hover: slightly brighter surface and border.
- Selected: blue border, faint blue internal fill, and stronger title contrast.
- Focus: 1 px accent border without disruptive glow.
- Disabled: muted text and 45% surface opacity.
- Running: blue status and progress.
- Done/accepted: green.
- Waiting: amber for agent status, gray for neutral queued state.
- Failed/rejected: red.
- Cancelled: amber-red neutral treatment.

## Empty States

1. No projects: explain that a project connects a local repository, then show
   `New Project`.
2. Project with no tasks: show the project path and `New Task`.
3. No task selected: retain the task rail and show a compact selection prompt.
4. No logs/diff/tests: show quiet placeholder copy without large illustrations.

## Dialog Flows

### New Project

- Project name.
- Repository path.
- Browse button.
- Cancel / Create Project.
- Validate directory existence before creation.

### New Task

- Task title.
- Prompt.
- Execution mode.
- Default agent summary.
- Cancel / Create & Run.

The existing repository selection and execution controls move into these dialogs
instead of consuming permanent workspace space.

## Data Model Direction

- Add `Project` with `id`, `name`, `repo_path`, timestamps, and tasks.
- Add `project_id`, explicit title compatibility, and `updated_at` to `Task`.
- Extend agent state toward an `AgentRun` persistence shape with task ownership,
  activity, log preview, result, and timestamps.
- Keep constructors backward compatible with existing core and tests.
- Store projects and tasks in memory for this phase.

## Implementation Plan

1. Add theme tokens, stylesheet generation, and reusable primitives.
2. Add backward-compatible `Project` and agent-run-ready model fields.
3. Implement project sidebar and project creation dialog.
4. Implement project header, task rail, task cards, and task creation dialog.
5. Recompose task detail and inspector while preserving existing public widget
   attributes used by `MainWindow` and tests.
6. Redesign agent cards and route event lines into each agent's preview.
7. Polish logs, prompt, subtasks, files, diff, tests, review, and empty states.
8. Render representative states at `1440x900` and concept-native `1586x992`,
   compare against the concept, and fix visible drift.
9. Run all unit, integration, workflow, and headless Qt tests.

## Intentional Qt Adaptations

- No true backdrop blur; layered translucent QSS surfaces replace it.
- Standard Qt text glyphs or simple geometric marks replace concept-only icon
  art where no matching project icon set exists.
- Native window controls remain platform-managed.
- The task/agent layout may become scrollable at smaller heights while retaining
  the same hierarchy.
# Advanced Planning Addendum

The Stage 10 orchestration upgrade retains the project-first workspace and adds
two focused planning surfaces.

## Project planning state

- The project header exposes New Task, Generate Roadmap, Generate Init, Open
  Roadmap, and Open Settings actions.
- The center workspace shows Roadmap, Init Plan, and Suggested Tasks tabs when
  no task is selected.
- Generated plans use read-only editors. Init candidates use explicit
  checkboxes and a confirmed Apply Selected Files action.
- The task rail remains visible so recent and active task context is preserved.

## Task Plan dialog

- Page one captures title, original prompt, and execution mode.
- Page two repeats the original prompt and shows the optimized prompt, planner
  notes, recommended/optional/risky groups, permissions, risk, rationale, and
  execution graph.
- Planner remains mandatory. Other agents can be manually enabled or disabled.
- The agent list scrolls independently so the execution graph and primary Run
  Selected Agents action remain visible.

## Runtime agent cards

- Cards use the registry display name and category rather than a fixed legacy
  role lookup.
- Permissions, risk, selection reason, live activity, progress, logs, elapsed
  time, and result summary are visible.
- Mock implementation cards can show Running simultaneously. Real OpenCode
  cards advance sequentially in the shared repository.
