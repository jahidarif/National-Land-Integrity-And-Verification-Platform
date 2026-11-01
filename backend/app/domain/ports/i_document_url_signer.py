from abc import ABC, abstractmethod
class IDocumentUrlSigner(ABC):
    @abstractmethod
    def sign(self, storage_key: str, filename: str, content_type: str) -> str: ...
