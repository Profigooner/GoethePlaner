from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from agentboard.app.models import AgentRole


SAFE_OPENCODE_AGENTS = frozenset({"plan", "build"})


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    id: str
    display_name: str
    description: str
    category: str
    default_enabled: bool
    can_modify_code: bool
    can_run_commands: bool
    risk_level: str
    keywords: tuple[str, ...]
    system_prompt: str
    opencode_agent: str
    role: AgentRole

    def build_prompt(
        self,
        *,
        task: str,
        repository: str,
        planner_notes: str,
    ) -> str:
        return (
            f"You are the {self.display_name} agent in GoethePlaner.\n\n"
            f"Role\n{self.system_prompt}\n\n"
            f"Task\n{task}\n\n"
            f"Repository\n{repository}\n\n"
            f"Planner notes\n{planner_notes or 'No additional planner notes.'}\n\n"
            "Constraints\n"
            "- Preserve existing user work.\n"
            "- Do not run destructive commands.\n"
            "- Do not commit, push, or force-push.\n"
            "- Keep work focused on this role and task.\n"
            "- Report changes, verification, and remaining risks."
        )


def _definition(
    agent_id: str,
    display_name: str,
    description: str,
    category: str,
    *,
    role: AgentRole,
    keywords: Iterable[str],
    prompt: str,
    default_enabled: bool = False,
    can_modify_code: bool = True,
    can_run_commands: bool = True,
    risk_level: str = "medium",
    opencode_agent: str = "build",
) -> AgentDefinition:
    return AgentDefinition(
        id=agent_id,
        display_name=display_name,
        description=description,
        category=category,
        default_enabled=default_enabled,
        can_modify_code=can_modify_code,
        can_run_commands=can_run_commands,
        risk_level=risk_level,
        keywords=tuple(keywords),
        system_prompt=prompt,
        opencode_agent=opencode_agent,
        role=role,
    )


AGENT_DEFINITIONS = (
    _definition(
        "planner",
        "Planner",
        "Decomposes tasks, selects specialists, and defines execution order.",
        "Planning",
        role=AgentRole.PLANNER,
        keywords=("plan", "scope", "milestone", "decompose", "requirements"),
        prompt=(
            "Analyze the request, identify dependencies and risks, select the "
            "smallest effective agent team, and produce an execution plan."
        ),
        default_enabled=True,
        can_modify_code=False,
        can_run_commands=False,
        risk_level="low",
        opencode_agent="plan",
    ),
    _definition(
        "prompt_optimizer",
        "Prompt Optimizer",
        "Clarifies the task, constraints, and completion criteria.",
        "Planning",
        role=AgentRole.PROMPT_OPTIMIZER,
        keywords=("clarify", "prompt", "ambiguous", "requirements"),
        prompt=(
            "Rewrite the request into a precise implementation brief without "
            "changing its intent or inventing unrelated requirements."
        ),
        default_enabled=True,
        can_modify_code=False,
        can_run_commands=False,
        risk_level="low",
        opencode_agent="plan",
    ),
    _definition(
        "software_architect",
        "Software Architect",
        "Designs boundaries, APIs, refactors, and cross-cutting architecture.",
        "Architecture",
        role=AgentRole.SOFTWARE_ARCHITECT,
        keywords=(
            "architecture",
            "architect",
            "refactor",
            "design system",
            "scalability",
            "service boundary",
            "migration",
        ),
        prompt=(
            "Inspect architecture and propose coherent boundaries, contracts, "
            "migration steps, and implementation tradeoffs."
        ),
        can_run_commands=False,
    ),
    _definition(
        "frontend_engineer",
        "Frontend Engineer",
        "Implements user interfaces, interactions, styling, and accessibility.",
        "Engineering",
        role=AgentRole.FRONTEND_ENGINEER,
        keywords=(
            "frontend",
            "ui",
            "ux",
            "dashboard",
            "component",
            "react",
            "vue",
            "css",
            "pyside",
            "desktop interface",
        ),
        prompt=(
            "Implement maintainable user-facing interfaces and interactions "
            "that follow the repository's design and component conventions."
        ),
    ),
    _definition(
        "backend_engineer",
        "Backend Engineer",
        "Implements APIs, services, authentication, and business logic.",
        "Engineering",
        role=AgentRole.BACKEND_ENGINEER,
        keywords=(
            "backend",
            "api",
            "server",
            "service",
            "authentication",
            "login",
            "endpoint",
            "business logic",
        ),
        prompt=(
            "Implement focused server-side behavior, APIs, services, and "
            "business rules while preserving compatibility and security."
        ),
    ),
    _definition(
        "nodejs_expert",
        "Node.js Expert",
        "Handles Node.js, TypeScript, npm, Express, and NestJS work.",
        "Language",
        role=AgentRole.NODEJS_EXPERT,
        keywords=(
            "node.js",
            "nodejs",
            "typescript",
            "javascript",
            "npm",
            "express",
            "nestjs",
        ),
        prompt=(
            "Diagnose and implement Node.js or TypeScript changes using the "
            "project's runtime, package, and asynchronous programming patterns."
        ),
    ),
    _definition(
        "python_expert",
        "Python Expert",
        "Handles Python applications, packaging, frameworks, and tooling.",
        "Language",
        role=AgentRole.PYTHON_EXPERT,
        keywords=(
            "python",
            "pyside6",
            "fastapi",
            "django",
            "flask",
            "pytest",
            "pip",
        ),
        prompt=(
            "Implement idiomatic Python changes with type hints, focused tests, "
            "and compatibility with the repository's supported runtime."
        ),
    ),
    _definition(
        "data_analytics",
        "Data Analytics",
        "Handles datasets, CSV analysis, metrics, visualizations, and anomalies.",
        "Data",
        role=AgentRole.DATA_ANALYTICS,
        keywords=(
            "csv",
            "data",
            "analytics",
            "metric",
            "visualization",
            "chart",
            "sales",
            "anomaly",
            "pandas",
        ),
        prompt=(
            "Analyze data requirements, implement transparent transformations "
            "and visualizations, and validate metrics and anomaly logic."
        ),
    ),
    _definition(
        "ml_engineer",
        "ML Engineer",
        "Handles ML pipelines, training, datasets, inference, and evaluation.",
        "AI / ML",
        role=AgentRole.ML_ENGINEER,
        keywords=(
            "machine learning",
            "model",
            "training",
            "dataset",
            "pytorch",
            "tensorflow",
            "sklearn",
            "inference",
            "evaluation",
        ),
        prompt=(
            "Inspect and improve machine-learning pipelines, datasets, training "
            "code, inference, evaluation, and experiment reproducibility."
        ),
    ),
    _definition(
        "cyber_security",
        "Cyber Security",
        "Reviews threats, authentication, permissions, secrets, and vulnerabilities.",
        "Security",
        role=AgentRole.CYBER_SECURITY,
        keywords=(
            "security",
            "vulnerability",
            "threat",
            "owasp",
            "permission",
            "secret",
            "injection",
            "xss",
            "csrf",
        ),
        prompt=(
            "Perform a defensive security review, identify concrete risks, and "
            "propose or implement narrowly scoped mitigations with evidence."
        ),
        risk_level="high",
    ),
    _definition(
        "system_engineer",
        "System Engineer",
        "Handles processes, networking, concurrency, OS, and runtime integration.",
        "Systems",
        role=AgentRole.SYSTEM_ENGINEER,
        keywords=(
            "system",
            "process",
            "thread",
            "concurrency",
            "network",
            "socket",
            "linux",
            "daemon",
            "runtime",
        ),
        prompt=(
            "Implement or review process, operating-system, networking, and "
            "concurrency behavior with explicit safety and lifecycle handling."
        ),
        risk_level="high",
    ),
    _definition(
        "database_engineer",
        "Database Engineer",
        "Handles schemas, migrations, SQL, indexes, and query performance.",
        "Data",
        role=AgentRole.DATABASE_ENGINEER,
        keywords=(
            "database",
            "sql",
            "postgres",
            "mysql",
            "sqlite",
            "schema",
            "migration",
            "index",
            "query",
        ),
        prompt=(
            "Design and implement safe database changes with integrity, "
            "migration, indexing, rollback, and query-performance considerations."
        ),
    ),
    _definition(
        "devops_engineer",
        "DevOps Engineer",
        "Handles CI/CD, containers, deployments, and release automation.",
        "Operations",
        role=AgentRole.DEVOPS_ENGINEER,
        keywords=(
            "devops",
            "ci",
            "cd",
            "github actions",
            "docker",
            "container",
            "deploy",
            "kubernetes",
            "release",
        ),
        prompt=(
            "Improve CI, container, deployment, and release configuration "
            "without publishing, deploying, or changing remote infrastructure."
        ),
        risk_level="high",
    ),
    _definition(
        "test_engineer",
        "Test Engineer",
        "Designs regression coverage, runs tests, and reports failures.",
        "Quality",
        role=AgentRole.TEST_ENGINEER,
        keywords=("test", "tests", "coverage", "qa", "regression", "verify"),
        prompt=(
            "Add focused regression tests, run the relevant safe test commands, "
            "and report failures and coverage gaps without hiding them."
        ),
    ),
    _definition(
        "bug_tracker",
        "Bug Tracker",
        "Reproduces bugs, isolates root causes, and defines targeted fixes.",
        "Quality",
        role=AgentRole.BUG_TRACKER,
        keywords=(
            "bug",
            "fix",
            "broken",
            "error",
            "crash",
            "regression",
            "debug",
            "issue",
        ),
        prompt=(
            "Reproduce the failure, isolate the root cause, identify regression "
            "risk, and recommend the smallest evidence-backed correction."
        ),
        opencode_agent="plan",
    ),
    _definition(
        "code_reviewer",
        "Code Reviewer",
        "Reviews correctness, regressions, safety, and missing tests.",
        "Review",
        role=AgentRole.CODE_REVIEWER,
        keywords=("review", "audit", "quality", "maintainability"),
        prompt=(
            "Review the completed change for correctness, regressions, unsafe "
            "behavior, maintainability problems, and missing verification."
        ),
        can_modify_code=False,
        can_run_commands=False,
        risk_level="low",
        opencode_agent="plan",
    ),
    _definition(
        "documentation_writer",
        "Documentation Writer",
        "Writes README, API, migration, and user/developer documentation.",
        "Documentation",
        role=AgentRole.DOCUMENTATION_WRITER,
        keywords=(
            "documentation",
            "docs",
            "readme",
            "guide",
            "migration notes",
            "api docs",
        ),
        prompt=(
            "Update concise, accurate user and developer documentation for the "
            "implemented behavior without inventing unsupported capabilities."
        ),
        can_run_commands=False,
        risk_level="low",
        opencode_agent="plan",
    ),
)


class AgentRegistry:
    def __init__(
        self, definitions: Iterable[AgentDefinition] = AGENT_DEFINITIONS
    ) -> None:
        definitions = tuple(definitions)
        self._definitions = {
            definition.id: definition for definition in definitions
        }
        if len(self._definitions) != len(definitions):
            raise ValueError("Agent IDs must be unique.")

    def all(self) -> tuple[AgentDefinition, ...]:
        return tuple(self._definitions.values())

    def get(self, agent_id: str) -> AgentDefinition:
        try:
            return self._definitions[agent_id]
        except KeyError as exc:
            raise KeyError(f"Unknown agent: {agent_id}") from exc

    def contains(self, agent_id: str) -> bool:
        return agent_id in self._definitions

    def by_category(self, category: str) -> tuple[AgentDefinition, ...]:
        return tuple(
            item
            for item in self._definitions.values()
            if item.category == category
        )


def safe_opencode_agent(
    definition: AgentDefinition,
    custom_agents: Mapping[str, str] | None = None,
) -> str:
    custom = (custom_agents or {}).get(definition.id)
    if custom:
        return custom
    if definition.opencode_agent in SAFE_OPENCODE_AGENTS:
        return definition.opencode_agent
    return "plan"


DEFAULT_AGENT_REGISTRY = AgentRegistry()
