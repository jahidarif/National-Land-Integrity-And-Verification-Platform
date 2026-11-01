from abc import ABC, abstractmethod
class IPasswordVerifier(ABC):
    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool: ...
