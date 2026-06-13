from __future__ import annotations

import os
import shlex
from dataclasses import dataclass


DEFAULT_OPENCODE_TEMPLATE = (
    "opencode run --dir {repo_path} --agent {agent_name} {prompt}"
)


@dataclass(frozen=True, slots=True)
class AppConfig:
    opencode_command_template: str = DEFAULT_OPENCODE_TEMPLATE
    mock_step_delay: float = 0.2
    test_command: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "AppConfig":
        template = os.getenv(
            "AGENTBOARD_OPENCODE_COMMAND", DEFAULT_OPENCODE_TEMPLATE
        ).strip()
        delay_text = os.getenv("AGENTBOARD_MOCK_DELAY", "0.2")
        test_text = os.getenv("AGENTBOARD_TEST_COMMAND", "")

        try:
            delay = max(0.0, float(delay_text))
        except ValueError:
            delay = 0.2

        return cls(
            opencode_command_template=template or DEFAULT_OPENCODE_TEMPLATE,
            mock_step_delay=delay,
            test_command=tuple(shlex.split(test_text)) if test_text else (),
        )

