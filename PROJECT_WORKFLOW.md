# GoethePlaner Project Workflow

## Product Structure

```text
Project
  -> Roadmap
  -> Init Plan
  -> Tasks
    -> Planner
    -> Selected Specialized Agents
      -> Parallel Execution
      -> Logs / Diffs / Tests / Review / Final Result
```

## 1. Project Creation

1. The user selects **New Project**.
2. GoethePlaner collects a project name, repository folder, and optional goal.
3. The repository path is validated without changing files.
4. An in-memory `Project` is created with empty roadmap, init plan, and task
   history.
5. The project dashboard becomes active.

Persistence is intentionally deferred. Closing the app clears in-memory state.

## 2. Project Roadmap Generation

1. The user selects **Generate Roadmap**.
2. A background worker performs read-only repository inspection:
   - Top-level structure.
   - Existing README excerpt when available.
   - Common language and framework marker files.
   - Existing task history and project goal.
3. `RoadmapGenerator` produces a deterministic Markdown roadmap containing:
   - Project summary.
   - Architecture guess.
   - Suggested milestones.
   - Recommended next tasks.
   - Risk areas.
   - Testing strategy.
   - Agent recommendations.
4. The roadmap is saved to `Project.roadmap` and displayed in the project
   inspector.
5. Export suggests `ROADMAP.generated.md` only after explicit user action and
   asks for confirmation before replacing an existing export.

## 3. Project Init Generation

1. The user selects **Generate Init**.
2. `InitGenerator` performs read-only repository inspection.
3. It produces:
   - A safe initialization plan.
   - Candidate files that could be created.
   - Files that already exist.
   - Warnings and setup recommendations.
4. The plan is saved to `Project.init_plan` and displayed in the project
   inspector.
5. No files are created or overwritten during generation.
6. **Apply Selected Files** shows every candidate and requires explicit
   confirmation. It creates only allowlisted missing paths using exclusive file
   creation; existing paths are skipped.

## 4. Task Creation and Planning

1. The user selects **New Task**.
2. The dialog collects title, prompt, and execution mode.
3. The user selects **Plan Task**.
4. The prompt optimizer creates a clarified prompt locally.
5. The rule-based `AgentSelector` generates:
   - Planner notes.
   - Recommended agents.
   - Optional agents.
   - Disabled/high-risk agents.
   - Per-agent selection reasons.
   - Execution graph preview.
6. The user reviews permissions and risk levels, then enables or disables
   agents.
7. **Run Selected Agents** creates the task and starts the worker thread.

`planner` is mandatory. At least one executable or review agent must remain
selected.

## 5. Execution

### Ordered prerequisites

1. Prompt Optimizer, when selected.
2. Planner.

These stages finalize the optimized prompt, planner notes, and executable
subtasks.

### Implementation stage

- Mock mode runs selected implementation and analysis agents concurrently.
- Progress and logs are emitted independently for each agent.
- Overall progress is computed from completed agent units.
- Real OpenCode mode runs sequentially in the shared repository.
- Parallel real code modification is not enabled without isolated worktrees or
  branches.

### Final stages

1. Test Engineer after implementation.
2. Code Reviewer after tests.
3. Documentation Writer near the end.
4. Final summary and repository inspection.

## 6. Review and Final Result

The task detail view shows:

- Original and optimized prompts.
- Planner notes and selected-agent rationale.
- Execution graph.
- Agent status, progress, activity, logs, timing, permissions, risk, and result.
- Changed files and Git diff.
- Test output.
- Review result.

The user may:

- **Accept**: records the local decision only.
- **Reject**: restores the captured pre-task Git baseline and archives new files
  instead of deleting them.

GoethePlaner never commits, pushes, force-pushes, or merges automatically.

## Concurrency and Safety

- All orchestration runs outside the Qt UI thread.
- Mock parallelism is bounded and cooperative.
- Subprocesses use argument arrays with `shell=False`.
- Real code-modifying agents never run concurrently in the same working
  directory.
- Roadmap and init generation are read-only.
- Existing project files are never overwritten without explicit confirmation.
- User changes present before a task are preserved by the Git baseline.
