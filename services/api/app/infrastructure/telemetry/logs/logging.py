import logging, sys
import os, pathlib
from pythonjsonlogger.json import JsonFormatter
from app.common.config import Config
from opentelemetry import trace

class CustomJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['pid'] = os.getpid()
        log_record['service'] = Config.APP_NAME
        log_record['env'] = Config.MODE
        log_record['message'] = record.getMessage()
        


class OTLPJsonFormatter(CustomJsonFormatter):
    def __init__(self,*args, trace_provider=None, **kwargs): 
        '''Such an init with DI provides us an easy way to test this class witout OT'''
        super().__init__(**kwargs)
        self._trace_provider = trace_provider or trace

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        span = self._trace_provider.get_current_span()
        if span.get_span_context().is_valid:
            log_record['trace_id'] = format(span.get_span_context().trace_id, '032x')
            log_record['span_id'] = format(span.get_span_context().span_id, '016x')
            

       
current_dir = pathlib.Path(__file__).parent

def configure_logger(name: str, stream=sys.stdout):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    stream_handler = logging.StreamHandler(stream)

    if Config.JSON_LOGS == 1:
        formatter = OTLPJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )

    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

def init_loggers():
    """Use this func to add or edit list of used loggers"""
    applogger = configure_logger('app')                      
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False

    
