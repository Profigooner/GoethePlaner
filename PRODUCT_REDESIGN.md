# GoethePlaner Product Redesign

## Product Direction

GoethePlaner should be a compact IDE-style control center for AI coding
projects. Projects are the durable organizing concept. Roadmap, Init, tasks,
agent execution, output, tests, and problems are resources inside a project,
not unrelated dashboard tabs.

The redesign keeps the existing safe OpenCode and mock execution paths while
changing the project lifecycle and information architecture.

## Problems in the Current Workflow

The current project dialog only connects a name to an existing folder. It does
not distinguish an existing repository from a new project, analyze available
documentation, or guide a new project through Roadmap and Init before coding.

Roadmap and Init are implemented as reviewable agent drafts, but they are still
opened from project actions and displayed inside a project tab set. They are not
permanent project resources in navigation, their lifecycle state is not explicit,
and completed tasks do not produce reviewable update suggestions.

The three-column workspace duplicates task navigation in a separate rail and
keeps logs, prompts, subtasks, files, diff, tests, and review in a permanent
right-side inspector. This consumes too much horizontal space and makes the
application feel like a prototype dashboard instead of an IDE.

## Corrected Project Creation

### Existing Project

1. Ask whether the project is existing or new.
2. Select and validate the repository folder.
3. Analyze the repository without modifying it.
4. Detect documentation, language/framework markers, Git state, Roadmap state,
   and Init context.
5. Show detected project type, documents, missing important files, and suggested
   actions.
6. Let the user choose whether to import existing documentation, create a
   missing Roadmap, run Init when context is missing, or improve README.
7. Never generate, replace, or delete files during analysis or import.

### New Project

```text
Project name
  -> target folder
  -> project goal
  -> Roadmap Agent draft
  -> user review and acceptance
  -> Init Agent draft
  -> proposed-file review
  -> confirmed selected-file apply
  -> project appears in navigation
  -> first task
```

The target directory may be created, but existing non-empty directories are not
silently repurposed. The project is added to the workspace only after guided
Roadmap and Init review.

## Roadmap Lifecycle

Roadmap is a living project document with these states:

- `missing`
- `draft`
- `accepted`
- `needs_update`
- `updated_after_task`
- `user_modified`
- `imported`

Roadmap is always visible below its project. Users can view and edit it, ask the
agent to improve it, add or remove requirements, mark checklist items complete,
reorder items, regenerate through the agent review flow, import an existing
Roadmap, export an accepted Roadmap, and turn a requirement into a task.

Task completion creates a pending Roadmap update suggestion. No Roadmap content
is changed until the user accepts that suggestion.

## Init Lifecycle

Init is a living project context assembled from accepted or imported project
documents. It covers the project overview, commands, architecture, conventions,
agent instructions, limitations, important files, and current state.

Init uses these states:

- `missing`
- `draft`
- `accepted`
- `stale`
- `needs_update`
- `updated_after_task`
- `user_modified`
- `imported`

Init is always visible below its project. After task completion, GoethePlaner
creates a pending Init update suggestion based on the completion summary and
repository result. README, AGENTS, TODO, and related files are never rewritten
without file-specific review and confirmation.

## Navigation Structure

The far-left sidebar is the single project and task navigator:

```text
GoethePlaner

Projects
▾ Project
   Roadmap
   Init
   ▾ Tasks
      Task A
      Task B
      + New Task

+ New Project
Settings
```

Projects and task groups expand and collapse. Selecting a project, Roadmap,
Init, or task changes the central workspace. The separate central task rail is
removed.

## Central Workspace

### Project Overview

- Project title, repository path, source type, and detected stack
- Roadmap and Init status
- Active task count and recent results
- Pending update suggestions
- Suggested next action

### Roadmap

- Editable Roadmap content
- Agent review action
- Add, remove, complete, and reorder requirement actions
- Turn selected requirement into a task
- Import and export actions
- Pending Roadmap update suggestions with Accept and Reject

### Init

- Current project context
- Detected documentation
- README and AGENTS state
- Run Init Agent action
- Import existing context action
- Pending Init update suggestions with Accept and Reject

### Task Detail

- Title, original and optimized prompt
- Selected agents and execution graph
- Agent execution cards
- Status and progress
- Completion summary
- Accept and Reject actions
- Pending project-update notice

## Bottom Tool Windows

The permanent right inspector is removed. A horizontal splitter provides a
resizable bottom tool-window region. A bottom toolbar exposes:

```text
[ Terminal ] [ Logs ] [ Prompt ] [ Output ] [ Tests ] [ Problems ]
```

Only one tool is visible at a time. Selecting the active button again hides the
tool window. The hidden state does not reserve working space.

- **Terminal**: command-style OpenCode and test output.
- **Logs**: structured workflow and agent events.
- **Prompt**: original prompt, optimized prompt, planner notes, selected agents,
  and execution graph.
- **Output**: completion summary, generated artifacts, and changed-file list.
- **Tests**: test command, result, and streamed output.
- **Problems**: warnings, failures, missing tools, missing Git, missing docs, and
  pending update notices.

Diff and Review pages are removed from the product surface. Git inspection and
safe reject behavior remain internal. Changed-file names remain available in
Output.

## Model Changes

`Project` gains project source type, detected project type, explicit Roadmap and
Init status, imported documents, analysis results, and update suggestions.

`ProjectDocument` represents imported or generated Roadmap, Init, README, AGENTS,
TODO, and setup context with path, content, status, and timestamp.

`ProjectUpdateSuggestion` represents a pending, accepted, or rejected Roadmap or
Init change associated with an optional source task.

`Task` gains a completion summary. Existing constructors and task orchestration
remain backward compatible.

## Safety Rules

- Never overwrite README, ROADMAP, AGENTS, TODO, or other project files silently.
- Never apply Roadmap or Init suggestions without explicit user acceptance.
- Never delete user files.
- Never run destructive commands.
- Never use `shell=True`.
- Keep mock mode functional.
- Preserve the real OpenCode command and safety boundaries.
- Run long-lived agent and subprocess work outside the Qt UI thread.
- Preserve pre-existing repository changes and safe reject behavior.
- Import reads bounded text only and never writes to the repository.

## Acceptance Criteria

1. New Project asks Existing Project or New Project.
2. Existing project analysis detects supported documentation and stack markers.
3. Existing project users choose whether to import or fill missing context.
4. New projects are guided through Roadmap and Init review before first use.
5. Roadmap, Init, Tasks, and New Task appear under every project in navigation.
6. The central workspace follows the selected project resource or task.
7. The separate task rail and permanent right inspector are removed.
8. Diff and Review are not exposed as pages.
9. Terminal, Logs, Prompt, Output, Tests, and Problems are bottom tool windows.
10. The active bottom tool toggles closed and only one tool is visible.
11. Completed tasks create pending Roadmap and Init update suggestions.
12. Suggestions do not change content until accepted.
13. Roadmap requirements can be added, removed, completed, reordered, and
    converted into tasks.
14. Roadmap and Init remain accessible even when missing.
15. Mock and real OpenCode workflows remain responsive and safe.
16. Existing tests pass and focused redesign tests cover the new lifecycle.
