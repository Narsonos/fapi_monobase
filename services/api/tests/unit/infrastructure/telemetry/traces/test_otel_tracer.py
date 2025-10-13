import pytest, asyncio
import tests.mocks as mocks

@pytest.fixture
def get_otel_tracer(monkeypatch):
    import app.infrastructure.telemetry.traces.otel_tracer as m
    
    monkeypatch.setattr(m.trace, 'get_tracer', mocks.DummyTraceProvider)
    return m.OTELTracer #here we return the class, since most of methods are static

def test_otel_start_span_and_get_id(get_otel_tracer):
    tracer_cls = get_otel_tracer
    tracer_instance = tracer_cls('abc')
    assert isinstance(tracer_instance._tracer, mocks.DummyTraceProvider)
    assert tracer_instance._tracer.name == 'abc'

    with tracer_cls.start_span('123') as span:
        assert isinstance(span, mocks.DummySpan)
        assert span.name == '123'
        assert tracer_cls.get_trace_id(span) == 15

@pytest.mark.asyncio
async def test_otel_traced_decorator(get_otel_tracer):
    tracer_cls = get_otel_tracer
    
    async def foo(arg:int, err=False):
        if err:
            raise ValueError()
        return arg * 2
    
    def bar(arg:int, err=False):
        if err:
            raise ValueError()
        return arg * 3
    
    wrapped_foo = tracer_cls.traced(foo)
    x = 4
    assert await wrapped_foo(x) == x*2
    with pytest.raises(ValueError):
        await wrapped_foo(x, err=True)
    
    wrapped_bar = tracer_cls.traced(bar)
    assert wrapped_bar(x) == x*3
    with pytest.raises(ValueError):
        wrapped_bar(x, err=True)