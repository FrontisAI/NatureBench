from __future__ import annotations

from typing import override

try:
    from harbor.environments.base import EnvironmentCapabilities
    from harbor.environments.docker.docker import DockerEnvironment
except ImportError as error:  # pragma: no cover - only without Harbor installed
    raise ImportError(
        "NatureBenchDockerEnvironment requires the optional 'harbor' dependencies"
    ) from error


class NatureBenchDockerEnvironment(DockerEnvironment):
    """Harbor local Docker environment that advertises Compose GPU support."""

    @property
    @override
    def capabilities(self) -> EnvironmentCapabilities:
        return super().capabilities.model_copy(update={"gpus": True})
