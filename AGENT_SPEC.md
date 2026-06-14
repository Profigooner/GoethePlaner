# GoethePlaner Agent Specification

## Purpose

GoethePlaner uses internal professional agent identities to plan and execute
coding work. Internal agent IDs are stable product concepts; they are not passed
directly to OpenCode unless explicitly configured. The registry is the single
source of truth for permissions, risk, selection keywords, prompts, and safe
OpenCode mappings.

## Agent Definition

Each registry entry contains:

```python
AgentDefinition(
    id: str,
    display_name: str,
    description: str,
    category: str,
    default_enabled: bool,
    can_modify_code: bool,
    can_run_commands: bool,
    risk_level: str,
    keywords: tuple[str, ...],
    system_prompt: str,
    opencode_agent: str,
)
```

Risk levels are `low`, `medium`, and `high`. Risk describes the scope of an
agent's permitted work, not the quality or trustworthiness of the model.

## Available Agents

| ID | Role and selection guidance | Category | Modify | Commands | Risk | OpenCode |
| --- | --- | --- | --- | --- | --- | --- |
| `planner` | Always selected. Decomposes the task, establishes dependencies, and records planner notes. | Planning | No | No | Low | `plan` |
| `prompt_optimizer` | Clarifies ambiguous or broad tasks before planning. Enabled by default. | Planning | No | No | Low | `plan` |
| `software_architect` | Architecture, refactors, boundaries, APIs, scaling, and cross-cutting design. | Architecture | Yes | No | Medium | `build` |
| `frontend_engineer` | Desktop/web UI, UX, components, styling, accessibility, and client behavior. | Engineering | Yes | Yes | Medium | `build` |
| `backend_engineer` | APIs, services, authentication, business logic, and server behavior. | Engineering | Yes | Yes | Medium | `build` |
| `nodejs_expert` | Node.js, TypeScript, npm, Express, NestJS, and JavaScript runtime work. | Language | Yes | Yes | Medium | `build` |
| `python_expert` | Python, PySide6, FastAPI, Django, Flask, packaging, and Python tooling. | Language | Yes | Yes | Medium | `build` |
| `data_analytics` | CSV/data analysis, metrics, visualizations, transformations, and anomaly analysis. | Data | Yes | Yes | Medium | `build` |
| `ml_engineer` | ML pipelines, datasets, training, inference, evaluation, and experiments. | AI / ML | Yes | Yes | Medium | `build` |
| `cyber_security` | Threat review, authentication, secrets, permissions, and vulnerability analysis. | Security | Yes | Yes | High | `build` |
| `system_engineer` | Processes, operating systems, networking, concurrency, and runtime integration. | Systems | Yes | Yes | High | `build` |
| `database_engineer` | Schemas, migrations, SQL, indexes, data integrity, and query performance. | Data | Yes | Yes | Medium | `build` |
| `devops_engineer` | CI/CD, containers, deployment, infrastructure, and release automation. | Operations | Yes | Yes | High | `build` |
| `test_engineer` | Test design, regression coverage, test execution, and failure reporting. Runs after implementation. | Quality | Yes | Yes | Medium | `build` |
| `bug_tracker` | Reproduction, root-cause isolation, regression analysis, and targeted fixes. | Quality | Yes | Yes | Medium | `plan` by default |
| `code_reviewer` | Correctness, regression, safety, maintainability, and missing-test review. Runs after tests. | Review | No | No | Low | `plan` |
| `documentation_writer` | README, API docs, migration notes, and user/developer guidance. Runs near the end. | Documentation | Yes | No | Low | `plan` |

## Project Review Agents

Roadmap and Init are project-level review agents, not code-modifying task stages.

### Roadmap Agent

- OpenCode mapping: `plan`
- Permissions: repository read and structured response only
- Inputs: repository path, goal, target users, MVP scope, constraints, notes,
  README excerpt, detected stack, and bounded structure summary
- Outputs: Markdown roadmap, summary, observations, milestones, next tasks,
  risks, and testing strategy
- Revision input: previous draft plus user feedback
- Prohibited: file writes, destructive commands, automatic acceptance, or
  direct export

### Init Agent

- OpenCode mapping: `plan`
- Permissions: repository read and structured response only
- Inputs: repository path, init goal, README excerpt, detected stack, bounded
  structure summary, and existing conventions
- Outputs: complete proposed file contents, observations, and setup notes
- Revision input: previous proposals plus user feedback
- Prohibited: direct `/init` writes, setup execution, migrations, or unconfirmed
  repository changes

Both agents use strict JSON output contracts. GoethePlaner hydrates Init
proposals with current content and unified diffs before review. Mock mode uses
the same draft and revision contract.

After coding tasks complete, GoethePlaner creates deterministic pending Roadmap
and Init update suggestions from the task completion summary. These suggestions
are not code-modifying agent stages, do not write files, and require explicit
acceptance in the project resource view.

The concrete system prompts live in
`agentboard/app/core/agent_registry.py`. Every prompt states the internal role,
scope, task, repository, constraints, and expected result. Prompt text
supplements the safe OpenCode mapping.

## Selection Rules

The first selector is deterministic and rule based:

1. `planner` is always selected.
2. `prompt_optimizer` is selected by default.
3. Registry keywords are matched against normalized task title and prompt.
4. Domain rules add combinations that keyword scores alone may miss:
   - Node.js bug tasks add `nodejs_expert`, `backend_engineer`, and
     `bug_tracker`.
   - CSV/data/dashboard tasks add `data_analytics` and often
     `frontend_engineer`.
   - ML tasks add `ml_engineer` and `python_expert`.
   - Security tasks add `cyber_security` and `backend_engineer`.
5. `test_engineer` and `code_reviewer` are selected for implementation,
   debugging, data, ML, security, database, systems, and operations work.
6. The selector returns selected IDs, optional IDs, risky IDs, per-agent
   reasons, planner notes, and a concise overall reason.
7. The user can enable or disable any optional agent before execution.

The selector never calls an LLM and does not inspect secrets or execute code.

## OpenCode Mapping Strategy

Only configured safe OpenCode agent names may enter the command:

- Planning and review roles map to `plan`.
- Implementation and command-running roles map to `build`.
- `bug_tracker` maps to `plan` by default; implementation can be delegated to a
  selected engineering agent.
- Unknown internal mappings fall back to `plan`.
- Custom OpenCode agents require explicit configuration before use.

Example execution message:

```text
You are the ML Engineer agent in GoethePlaner.

Role:
Handle machine-learning pipelines, datasets, training code, inference,
evaluation, and experiments.

Task:
...

Repository:
...

Constraints:
- Preserve existing user work.
- Do not run destructive commands.
- Keep changes focused.

Expected result:
Summarize findings, changes, verification, and remaining risks.
```

## Execution Graph

```text
Prompt Optimizer (optional)
        |
        v
Planner (always)
        |
        v
Parallel implementation / analysis agents
        |
        v
Test Engineer (optional)
        |
        v
Code Reviewer (optional)
        |
        v
Documentation Writer (optional)
        |
        v
Final summary
```

### Parallel Rules

- Mock mode runs implementation/analysis agents concurrently using bounded
  Python worker threads.
- Planning and prompt optimization remain ordered prerequisites.
- Test, review, and documentation stages run after implementation.
- Real OpenCode mode runs code-modifying agents sequentially in the selected
  repository until isolated worktrees are implemented.
- Read-only planning/review roles may still be staged separately, but the first
  real-mode release favors a single sequential execution stream.
- Cancellation is cooperative and propagates to every active mock worker or the
  current OpenCode subprocess.

## Result Aggregation

Each agent run stores status, progress, activity, logs, timing, and result
summary. The orchestrator aggregates:

1. Selected agents and planner rationale.
2. Successful, failed, and cancelled agent results.
3. Test outcome and review summary.
4. Repository changes and Git diff.
5. Final task status and remaining risks.

One failed implementation agent marks the workflow failed after active parallel
workers finish or cancel. Review and documentation do not run after a failed
implementation stage. No automatic merge, commit, push, or destructive cleanup
is performed.
