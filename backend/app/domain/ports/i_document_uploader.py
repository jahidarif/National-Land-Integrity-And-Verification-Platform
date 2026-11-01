from abc import ABC, abstractmethod
class IDocumentUploader(ABC):
    @abstractmethod
    def upload(self, storage_key: str, content: bytes, content_type: str) -> None: ...
