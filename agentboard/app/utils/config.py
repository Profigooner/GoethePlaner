from __future__ import annotations

import json
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
    opencode_custom_agents: tuple[tuple[str, str], ...] = ()

    @property
    def custom_agent_map(self) -> dict[str, str]:
        return dict(self.opencode_custom_agents)

    @classmethod
    def from_env(cls) -> "AppConfig":
        template = os.getenv(
            "AGENTBOARD_OPENCODE_COMMAND", DEFAULT_OPENCODE_TEMPLATE
        ).strip()
        delay_text = os.getenv("AGENTBOARD_MOCK_DELAY", "0.2")
        test_text = os.getenv("AGENTBOARD_TEST_COMMAND", "")
        custom_agents_text = os.getenv(
            "AGENTBOARD_OPENCODE_AGENT_MAP", ""
        ).strip()

        try:
            delay = max(0.0, float(delay_text))
        except ValueError:
            delay = 0.2

        custom_agents: tuple[tuple[str, str], ...] = ()
        if custom_agents_text:
            try:
                decoded = json.loads(custom_agents_text)
                if isinstance(decoded, dict):
                    custom_agents = tuple(
                        (str(key), str(value))
                        for key, value in decoded.items()
                        if str(key).strip() and str(value).strip()
                    )
            except (TypeError, ValueError):
                custom_agents = ()

        return cls(
            opencode_command_template=template or DEFAULT_OPENCODE_TEMPLATE,
            mock_step_delay=delay,
            test_command=tuple(shlex.split(test_text)) if test_text else (),
            opencode_custom_agents=custom_agents,
        )
