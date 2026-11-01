from abc import ABC, abstractmethod
class IDocumentReader(ABC):
    @abstractmethod
    def read(self, storage_key: str) -> bytes: ...
