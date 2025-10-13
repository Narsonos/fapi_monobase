import pytest, logging, io, json
import app.infrastructure.telemetry.logs as logs
from app.common.config import Config
import tests.mocks as m

def test_logger_configuring(): #missing lines only
    Config.JSON_LOGS = 1
    logger = logs.configure_logger('123')
    assert isinstance(logger.handlers[0].formatter, logs.OTLPJsonFormatter)
    Config.JSON_LOGS = 0
    logger = logs.configure_logger('123')
    assert isinstance(logger.handlers[0].formatter, logging.Formatter)






def test_otlp_span_context(monkeypatch):
    Config.JSON_LOGS = 1
    log_stream = io.StringIO()
    
    logger = logs.configure_logger('123', log_stream)
    logger.handlers[0].formatter._trace_provider = m.DummyTraceProvider()
    logger.info("123")
    

    value = log_stream.getvalue()
    value:dict = json.loads(value)

    trace_id = value.get('trace_id')
    span_id = value.get('span_id')
    assert trace_id == f"{'0'*31}f"
    assert span_id == f"{'0'*15}f"


