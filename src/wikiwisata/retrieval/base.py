"""Kontrak retrieval yang dipakai bagian Ian dan Elias."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Passage:
    """Satu potongan dokumen yang dikembalikan retriever."""

    passage_id: str
    doc_id: str
    rev_id: int
    title: str
    section: str
    text: str
    score: float = 0.0
    rank: int = 0
    lastedit: str | None = None
    lat: float | None = None
    lon: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class Retriever(Protocol):
    """Antarmuka yang harus dipenuhi implementasi Elias."""

    index_hash: str

    def search(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[Passage]:
        """Kembalikan passage paling relevan untuk query."""
        ...
