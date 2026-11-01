from abc import ABC, abstractmethod
class IAssistantProvider(ABC):
    @abstractmethod
    def ask(self, query: str, history: list[dict] | None = None, files: list[dict] | None = None, session_id: str | None = None): ...
