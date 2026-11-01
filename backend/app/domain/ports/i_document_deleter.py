from abc import ABC, abstractmethod
class IDocumentDeleter(ABC):
    @abstractmethod
    def delete(self, storage_key: str) -> None: ...
