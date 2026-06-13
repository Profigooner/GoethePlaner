from __future__ import annotations

import re


class PromptOptimizer:
    def optimize(self, prompt: str, repository_name: str) -> str:
        cleaned = re.sub(r"[ \t]+", " ", prompt.strip())
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        if not cleaned:
            raise ValueError("The task prompt cannot be empty.")

        return (
            f"Objective\n{cleaned}\n\n"
            f"Repository\n{repository_name}\n\n"
            "Implementation requirements\n"
            "- Inspect the existing code and follow its established patterns.\n"
            "- Keep changes focused on the requested behavior.\n"
            "- Preserve existing user work and avoid destructive commands.\n"
            "- Add or update focused tests for changed behavior.\n"
            "- Report changed files, verification performed, and remaining risks.\n\n"
            "Completion criteria\n"
            "- The requested behavior is implemented end to end.\n"
            "- Relevant tests pass, or failures are clearly explained.\n"
            "- The final diff contains no unrelated changes."
        )

