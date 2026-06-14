# Product Correction: Agent-Driven Roadmap and Init Review

## What Was Wrong

The previous Roadmap and Init features were local template generators. They
inspected a few repository markers, assembled deterministic Markdown, and
immediately stored the result on the project. This created the appearance of an
agent workflow without actually asking OpenCode to analyze the repository,
supporting user feedback, or separating draft generation from acceptance.

Init also proposed generic missing files rather than agent-authored file
contents. Its apply step could create templates, but users could not review a
real proposal or diff before choosing what to write.

## Corrected User Workflow

### Roadmap

```text
Project goal and constraints
  -> read-only OpenCode planning agent
  -> roadmap draft
  -> user review
  -> accept, revise, regenerate, or cancel
  -> export only after acceptance
```

The Roadmap Agent receives the repository path, goal, target users, MVP scope,
technical constraints, notes, README context, detected stack, and a bounded
structure summary. It returns a practical roadmap plus a reasoning summary,
repository observations, milestones, next tasks, risks, and testing strategy.
Feedback is sent with the previous draft and produces a revised draft while
preserving feedback history.

### Init

```text
Project init goal
  -> read-only OpenCode /init-style agent
  -> proposed file contents
  -> file and diff review
  -> accept selected files, revise, regenerate, export, or cancel
  -> confirmed apply of selected files only
```

The Init Agent must inspect the repository before proposing README, AGENTS,
setup, workflow, test, architecture, convention, or optional configuration
files. Draft generation never writes to the repository.

## Required UI Changes

- Dashboard actions become `New Task`, `Create Roadmap`, and `Run Init Agent`.
- Roadmap opens a dialog with goal, target users, MVP scope, constraints, notes,
  execution mode, agent output tabs, feedback, logs, and review actions.
- Init opens a dialog with goal, execution mode, proposed-file checkboxes,
  content preview, unified diff, feedback, logs, and review actions.
- Long-running calls execute in background workers and stream command, progress,
  stdout, stderr, and failure diagnostics.
- The UI states that generated content is a draft and nothing is saved or
  applied without explicit acceptance.

## Required Model Changes

- `RoadmapDraft`: project ownership, user goal, draft content, feedback history,
  status, timestamps, reasoning summary, repository observations, milestones,
  next tasks, risks, testing strategy, and agent diagnostics.
- `InitDraft`: project ownership, user goal, proposed files, feedback history,
  status, timestamps, and agent diagnostics.
- `ProposedFile`: relative path, proposed and existing content, status, selected
  state, and unified diff preview.
- Projects retain current drafts and accepted roadmap/init state separately.

## Required OpenCode Integration Changes

- Add dedicated Roadmap and Init generation and revision methods.
- Use the safe `plan` agent for all draft calls.
- Build prompts from bounded repository context and require structured JSON.
- Use `opencode run` when direct interactive `/init` use is not suitable.
- Mock mode returns realistic repository-aware drafts and changes them in
  response to feedback.
- Real mode exposes the exact argument-safe command and captures stdout and
  stderr without `shell=True`.

## Safety Rules

- Never overwrite an existing file silently.
- Never save or export a roadmap before explicit acceptance.
- Never write files during Init draft or revision.
- Apply only user-selected Init proposals after a confirmation step.
- Updating an existing Init target requires explicit overwrite confirmation for
  that path.
- Reject absolute paths, parent traversal, and paths outside the repository.
- Never run destructive commands, use `shell=True`, commit, push, or force push.
- Keep the UI responsive and make failures diagnosable.

## Acceptance Criteria

1. Roadmap generation requires a user goal and calls an agent workflow.
2. A generated roadmap remains a draft until accepted.
3. Feedback produces a revised draft with retained history.
4. Roadmap export defaults to `ROADMAP.generated.md` and never silently replaces
   an existing file.
5. Init returns proposed file contents and diffs without writing files.
6. README and AGENTS content are proposed after repository inspection.
7. Users can select proposals and apply only those files after confirmation.
8. Existing targets require path-specific overwrite confirmation.
9. Init feedback produces a revised proposal with retained history.
10. Mock and real OpenCode modes use the same review contract.
11. Agent calls run outside the Qt UI thread and stream diagnostics.
12. Existing task orchestration and safety behavior continue to pass tests.
