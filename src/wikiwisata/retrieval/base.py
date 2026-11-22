"""Kontrak retrieval yang dipakai bagian Ian dan Elias."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from wikiwisata.retrieval.retriever import Passage


@runtime_checkable
class RetrieverProtocol(Protocol):
    """Antarmuka yang harus dipenuhi implementasi retriever."""

    def index_hash(self) -> str:
        """Kembalikan hash indeks yang dipakai."""
        ...

    def search(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[Passage]:
        """Kembalikan passage paling relevan untuk query."""
        ...
