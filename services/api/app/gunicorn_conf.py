# gunicorn_conf.py
import multiprocessing
import logging

bind = "0.0.0.0:8000"

workers = max(2, multiprocessing.cpu_count())

worker_class = "uvicorn.workers.UvicornWorker"

loglevel = "info"
accesslog = None #middleware logs it   
errorlog = "-"   
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

class ExcludeAioHttpFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith("Unclosed connection")

asyncio_logger = logging.getLogger("asyncio")
asyncio_logger.addFilter(ExcludeAioHttpFilter())

timeout = 30      
graceful_timeout = 30

reload = False


