from opentelemetry import trace
import app.infrastructure.interfaces as iabc
import contextlib, typing as t, functools, inspect

F = t.TypeVar("F", bound=t.Callable[..., t.Any])

class OTELTracer(iabc.ITracer):
    def __init__(self, tracer_name: str):
        self._tracer = trace.get_tracer(tracer_name)



    @contextlib.contextmanager
    @staticmethod
    def start_span(name: str):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(name) as span:
            yield span


    @staticmethod
    def get_trace_id(span) -> str:
        ctx = span.get_span_context()
        return ctx.trace_id



    @staticmethod
    def traced(func):
        tracer = trace.get_tracer(func.__module__)

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(func.__qualname__) as span:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        raise
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(func.__qualname__) as span:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    raise
        return sync_wrapper