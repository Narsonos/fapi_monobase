import contextlib

class DummySpanContext:
    def __init__(self, trace_id:int=15, span_id:int=15, is_valid:bool=True):
        self.trace_id = trace_id
        self.span_id = span_id
        self.is_valid = is_valid

class DummySpan:
    def __init__(self, name='name'):
        self.name = name

    def get_span_context(self):
        return DummySpanContext()
    
    def record_exception(self, arg):
        return arg

class DummyTraceProvider:
    def __init__(self, name:str='default'):
        self.name = name

    def get_current_span(self):
        self.span = DummySpan()
        return self.span
    
    @contextlib.contextmanager
    def start_as_current_span(self, name, *args, **kwargs):
        self.span = DummySpan(name)
        yield self.span