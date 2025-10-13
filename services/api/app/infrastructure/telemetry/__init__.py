from opentelemetry import trace as otel_trace, metrics as otel_metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
import os
from app.common.config import Config




def setup_opentelemetry(app):
    resource = Resource.create({
        "service.name": Config.OTEL_SERVICE_NAME,
        "process.pid": os.getpid(),
        "service.instance.id": f"worker-{os.getpid()}",
        })

    metric_exporter = OTLPMetricExporter(endpoint=Config.OTEL_GRPC_ENDPOINT, insecure=True)
    span_exporter = OTLPSpanExporter(endpoint=Config.OTEL_GRPC_ENDPOINT, insecure=True)
    default_span_processor = BatchSpanProcessor(span_exporter)
    
    reader = PeriodicExportingMetricReader(
        exporter=metric_exporter, 
        export_interval_millis=15000
    )

    tracer = TracerProvider(resource=resource)
    meter = MeterProvider(resource=resource, metric_readers=[reader])
    otel_metrics.set_meter_provider(meter)
    otel_trace.set_tracer_provider(tracer)

    tracer.add_span_processor(default_span_processor)

    FastAPIInstrumentor.instrument_app(app, exclude_spans=['receive', 'send'])
    LoggingInstrumentor().instrument(set_logging_format=False)

    
