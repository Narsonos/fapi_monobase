from .otel_tracer import *
from app.common.config import Config

TracerType = OTELTracer
def get_tracer():
    return TracerType(f'{Config.APP_NAME}')