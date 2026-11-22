"""Retrieval interfaces and implementations."""

from .base import RetrieverProtocol
from .retriever import Passage, Retriever

__all__ = ["Passage", "Retriever", "RetrieverProtocol"]
