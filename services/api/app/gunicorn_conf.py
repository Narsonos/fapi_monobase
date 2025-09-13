# gunicorn_conf.py
import multiprocessing
import logging

# Хост и порт
bind = "0.0.0.0:8000"

# Кол-во воркеров: по числу CPU, но минимум 2
workers = max(2, multiprocessing.cpu_count())

# Тип воркера для FastAPI/ASGI
worker_class = "uvicorn.workers.UvicornWorker"

# Логирование
loglevel = "info"
accesslog = "-"   # лог запросов в stdout
errorlog = "-"    # лог ошибок в stdout
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Убрать спам от asyncio о незакрытых соединениях
class ExcludeAioHttpFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith("Unclosed connection")

asyncio_logger = logging.getLogger("asyncio")
asyncio_logger.addFilter(ExcludeAioHttpFilter())

# Таймауты
timeout = 30       # стандартный таймаут работы воркера
graceful_timeout = 30

# Авто-reload только для девелопмента (если нужно)
reload = False

# Можно явно включить HTTP протокол httptools
# (Gunicorn + UvicornWorker использует uvicorn, а он сам подхватывает httptools)
