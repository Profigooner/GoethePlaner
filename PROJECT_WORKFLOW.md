# GoethePlaner Project Workflow

## Product Structure

```text
Project
  -> Roadmap
  -> Init
  -> Tasks
    -> Planner and selected agents
      -> Bottom tools
      -> Completion summary
      -> Roadmap and Init update suggestions
```

## 1. Project Creation

### Existing Project

1. Select Existing Project and a repository folder.
2. Analyze the repository without changing files.
3. Detect README, ROADMAP, ROADMAP.generated, AGENTS, AGENT, CLAUDE, TODO,
   pyproject, package, and requirements files.
4. Detect common language and framework markers.
5. Show existing documentation, missing important files, Roadmap state, Init
   state, Git state, and suggested actions.
6. Let the user choose whether to import documents, create a missing Roadmap,
   run Init, or review README improvements.
7. Import copies bounded text into in-memory project context only.

### New Project

1. Select New Project, name, target parent folder, and required goal.
2. Create the target directory only when it does not exist or is empty.
3. Run the Roadmap Agent in the selected mode.
4. Require user review and acceptance.
5. Run the Init Agent.
6. Require proposal selection, overwrite approval where applicable, and
   confirmed apply.
7. Add the project to navigation after guided setup is accepted.

## 2. Navigation

Each project is expandable and always contains Roadmap, Init, Tasks, and New
Task. Selecting an item changes the central workspace. There is no separate task
rail.

## 3. Roadmap Lifecycle

Roadmap states are missing, imported, draft, accepted, needs-update,
updated-after-task, and user-modified.

The user can edit, add/remove/complete/reorder requirements, import, export, ask
the agent to revise, and turn a requirement into a task. Agent output remains a
draft until accepted. Export never silently replaces a file.

## 4. Init Lifecycle

Init states are missing, imported, draft, accepted, stale, needs-update,
updated-after-task, and user-modified.

Init context is assembled from imported or accepted README, AGENTS, AGENT,
CLAUDE, TODO, setup, architecture, convention, command, limitation, and current
state content. Agent proposals remain read-only until the user confirms selected
files. Existing targets require explicit path approval and stale-file checks.

## 5. Task Planning and Execution

1. Create a task under the selected project.
2. Enter title, prompt, and execution mode.
3. Review optimized prompt, planner notes, selected agents, permissions, risk,
   and execution graph.
4. Run selected agents in a worker thread.
5. Mock implementation agents may run in parallel.
6. Real OpenCode agents run sequentially in the shared repository.
7. Test, review, and documentation stages retain dependency ordering.

## 6. Task Detail and Bottom Tools

Task Detail shows prompt, status, progress, agent cards, completion summary, and
accept/reject actions.

Terminal, Logs, Prompt, Output, Tests, and Problems are on-demand bottom tools.
Only one is open at a time. Diff and Review pages are removed; changed-file names
remain in Output and safe Git baseline behavior remains internal.

## 7. Completion Updates

After a task completes:

1. Build a completion summary from agent results.
2. Create a pending Roadmap suggestion.
3. Create a pending Init suggestion.
4. Mark both resources as needs-update.
5. Show suggestions in the corresponding central views.
6. Apply or reject each suggestion only after explicit user action.

Accepting a suggestion updates in-memory project context. It does not rewrite
ROADMAP, README, AGENTS, or another repository document. Repository updates
still require the dedicated export or Init proposal review flow.

## Safety

- Never use `shell=True`.
- Never delete user files.
- Never overwrite project documents silently.
- Never apply Roadmap or Init updates automatically.
- Preserve pre-existing Git changes.
- Reject restores only the captured task baseline and archives new files.
- Keep analysis, imports, and draft generation read-only.
- Keep long-running work outside the Qt UI thread.
