from abc import ABC, abstractmethod
class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...
