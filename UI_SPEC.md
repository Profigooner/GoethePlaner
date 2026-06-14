# GoethePlaner UI Specification

## Product Intent

GoethePlaner is a compact IDE-style control center for AI coding projects. The
UI prioritizes stable project navigation, a large central workspace, and
on-demand runtime detail. It must not return to a crowded dashboard with a
separate task rail and permanent right inspector.

## Information Architecture

```text
Project Tree
  Project
    Roadmap
    Init
    Tasks
      Task
      + New Task

Central Workspace
  Project Overview | Roadmap | Init | Task Detail

Bottom Tools
  Terminal | Logs | Prompt | Output | Tests | Problems
```

Roadmap and Init are first-class resources even when missing. Tasks are owned by
their project and appear only in the project tree.

## Stable Regions

### Left Project Tree

- Fixed width around 260-300 px.
- Product identity and New Project action at the top.
- Expandable projects with Roadmap, Init, Tasks, task rows, and New Task.
- Lifecycle status appears beside Roadmap and Init.
- Settings remains at the bottom.

### Project Header

- Project name, repository path, and active/idle status.
- Compact Roadmap and Init status badges.
- Shortcuts to Roadmap, Init, and New Task.

### Central Workspace

The workspace uses one `QStackedWidget`.

- **Project Overview**: identity, source type, detected stack, lifecycle status,
  active tasks, recent task results, pending updates, and next action.
- **Roadmap**: editable Markdown, lifecycle status, agent/import/export actions,
  requirement controls, task conversion, and pending suggestions.
- **Init**: current context, detected/imported documents, agent/import actions,
  and pending suggestions.
- **Task Detail**: prompt, status, progress, agent cards, completion summary,
  pending-update notice, and local accept/reject.

### Bottom Tool Windows

A vertical splitter places a hidden/resizable tool region below the workspace.
The toolbar is always visible.

- Selecting a tool opens it.
- Selecting the active tool hides it.
- Selecting another tool replaces the current tool.
- Only one tool is visible.
- Hiding the tool returns its height to the central workspace.

Tools:

- **Terminal**: command-style workflow, OpenCode, and test output.
- **Logs**: structured source-aware events with filter, search, and clear.
- **Prompt**: original and optimized prompt, planner notes, selected agents, and
  execution graph.
- **Output**: completion summary, agent assignments, and changed-file names.
- **Tests**: command input, run action, result, and streamed output.
- **Problems**: warnings, failures, missing prerequisites, and pending update
  reminders.

Diff and Review are not product pages in this phase.

## Project Creation Dialog

The first control asks Existing Project or New Project.

Existing:

- Project name and repository folder.
- Analyze Project action.
- Read-only summary of detected type, stack, documentation, missing files,
  Roadmap state, Init state, and suggested actions.
- Choices to import docs, create a missing Roadmap, run Init, and review README.

New:

- Project name, target parent folder, and required goal.
- Guided setup mode.
- Roadmap and Init onboarding enabled by default.

## Roadmap Interaction

- Edit and Save.
- Ask Agent through the existing review dialog.
- Add or remove requirement.
- Mark current item complete.
- Move current item up or down.
- Turn current item into a task.
- Import and export.
- Accept or reject one pending suggestion at a time.

All direct edits change in-memory project context. Repository files change only
through explicit export or confirmed Init apply.

## Visual Language

Retain the dark blue glass system:

- Background: `#080D17`
- Elevated background: `#0B1220`
- Panel: `#0F1828`
- Alternate panel: `#142033`
- Border: `#263750`
- Accent: `#2F81F7`
- Violet: `#8B5CF6`
- Success: `#34D399`
- Warning: `#F59E0B`
- Error: `#F87171`

Use thin borders, restrained status color, 8-13 px radii, system sans-serif
text, and monospace console text. Avoid decorative cards where a stable region
or list is clearer.

## Responsive Rules

- Minimum window size remains `1280x720`.
- The sidebar remains fixed while the central area expands.
- Agent cards use two columns when the task workspace is at least 760 px and one
  column below that.
- The bottom tool defaults to roughly one third of available height when opened.
- Long project and task labels elide in the tree and expose full text by tooltip.

## Safety and Responsiveness

- Analysis and import never write files.
- Roadmap/Init agent calls remain in background `QThread` workers.
- Task and test execution remain off the UI thread.
- Suggestion acceptance changes only in-memory context.
- Existing document replacement remains path-specific and confirmed.
- No destructive controls are introduced.
