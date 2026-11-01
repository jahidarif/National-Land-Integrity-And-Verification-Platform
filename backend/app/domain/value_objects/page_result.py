from dataclasses import dataclass
from typing import Generic, TypeVar
T = TypeVar("T")
@dataclass(frozen=True)
class PageResult(Generic[T]):
    page: int
    pageSize: int
    totalCount: int
    totalPages: int
    hasPrevious: bool
    hasNext: bool
    items: list[T]
