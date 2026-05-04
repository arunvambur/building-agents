# core/renderers/base.py

from abc import ABC, abstractmethod

class Renderer(ABC):

    @abstractmethod
    def supports(self, format: str) -> bool:
        pass

    @abstractmethod
    def render(self, spec: dict, data):
        pass