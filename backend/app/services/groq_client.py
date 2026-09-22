"""Shared, thread-safe Groq client selection."""

from __future__ import annotations

from threading import Lock
from typing import Callable, Dict, Tuple

from groq import Groq

from app.config import settings


class GroqClientPool:
    """Select Groq API keys in round-robin order for each API request."""

    def __init__(
        self,
        api_keys: tuple[str, ...],
        client_factory: Callable[..., Groq] = Groq,
    ) -> None:
        self._api_keys = api_keys
        self._client_factory = client_factory
        self._next_index = 0
        self._lock = Lock()
        self._clients: Dict[Tuple[str, float, int], Groq] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self._api_keys)

    def get_client(self, *, timeout: float, max_retries: int) -> Groq | None:
        """Return the next configured client, advancing the rotation safely."""
        with self._lock:
            if not self._api_keys:
                return None

            api_key = self._api_keys[self._next_index]
            self._next_index = (self._next_index + 1) % len(self._api_keys)
            client_key = (api_key, timeout, max_retries)
            client = self._clients.get(client_key)

            if client is None:
                client = self._client_factory(
                    api_key=api_key,
                    base_url="https://api.groq.com",
                    timeout=timeout,
                    max_retries=max_retries,
                )
                self._clients[client_key] = client

            return client


groq_client_pool = GroqClientPool(settings.groq_api_keys)


def get_groq_client(*, timeout: float = 60.0, max_retries: int = 2) -> Groq | None:
    """Get the next Groq client in the configured round-robin rotation."""
    return groq_client_pool.get_client(timeout=timeout, max_retries=max_retries)


def has_groq_api_keys() -> bool:
    return groq_client_pool.is_configured
