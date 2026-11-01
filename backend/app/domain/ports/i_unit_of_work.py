from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar
T = TypeVar("T")
class IUnitOfWork(ABC):
    @abstractmethod
    def run(self, work: Callable[[], T], conflict_message: str | None = None) -> T: ...
