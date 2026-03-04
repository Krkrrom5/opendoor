from abc import ABC, abstractmethod
from typing import Generator

class BaseLLM(ABC):
    @abstractmethod
    def send(self, messages: list, stream: bool = True) -> Generator:
        pass
    @abstractmethod
    def is_available(self) -> bool:
        pass
