from __future__ import annotations

from agentboard.app.models import (
    AgentStatus,
    Project,
    ProjectUpdateSuggestion,
    SuggestionStatus,
    Task,
)


class ProjectUpdateService:
    def create_for_completed_task(
        self, project: Project, task: Task
    ) -> tuple[ProjectUpdateSuggestion, ProjectUpdateSuggestion]:
        task.completion_summary = task.completion_summary or self._summary(task)
        existing = {
            item.target: item
            for item in project.update_suggestions
            if (
                item.source_task_id == task.id
                and item.status == SuggestionStatus.PENDING.value
            )
        }
        roadmap = existing.get("roadmap")
        if roadmap is None:
            roadmap = ProjectUpdateSuggestion(
                project_id=project.id,
                source_task_id=task.id,
                target="roadmap",
                suggested_change=(
                    "## Completed Work\n\n"
                    f"- [x] {task.title}\n"
                    f"  - {task.completion_summary}"
                ),
            )
            project.add_update_suggestion(roadmap)
        init = existing.get("init")
        if init is None:
            init = ProjectUpdateSuggestion(
                project_id=project.id,
                source_task_id=task.id,
                target="init",
                suggested_change=(
                    f"## Project State Update: {task.title}\n\n"
                    f"{task.completion_summary}\n\n"
                    "Review repository changes for new commands, architecture "
                    "decisions, conventions, important files, and limitations "
                    "before updating README or AGENTS."
                ),
            )
            project.add_update_suggestion(init)
        return roadmap, init

    @staticmethod
    def _summary(task: Task) -> str:
        completed = [
            agent.name
            for agent in task.agents
            if agent.status == AgentStatus.DONE
        ]
        failed = [
            agent.name
            for agent in task.agents
            if agent.status == AgentStatus.FAILED
        ]
        parts = [f"Task completed with {len(completed)} successful agent stage(s)."]
        if completed:
            parts.append("Completed: " + ", ".join(completed) + ".")
        if failed:
            parts.append("Failed: " + ", ".join(failed) + ".")
        return " ".join(parts)
