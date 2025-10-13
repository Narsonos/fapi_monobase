from abc import ABC, abstractmethod
import typing as t


F = t.TypeVar("F", bound=t.Callable[..., t.Any])

class ITracer(ABC):
    @abstractmethod
    def start_span(self, name: str):
        """Returns span context maanger"""

    @staticmethod
    def get_trace_id(span) -> str:
        """Extracts trace_id from the span"""

    
    @staticmethod
    @abstractmethod
    def traced(span_name: str | None = None) -> t.Callable[[F], F]:
        """
        Decorator that wraps a function in a tracing span.
        Implementations must support both sync and async functions.
        """
