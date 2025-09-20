import logging
import logging.handlers
import os, pathlib

current_dir = pathlib.Path(__file__).parent

def configure_logger(name: str, stream_level=logging.DEBUG, file_level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    if stream_level <= logging.CRITICAL:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(stream_level)
        stream_handler.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
        logger.addHandler(stream_handler)

    if file_level <= logging.CRITICAL:
        debug_handler = logging.handlers.RotatingFileHandler(
            filename = current_dir / f'{name}.log',
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )
        debug_handler.setLevel(file_level)
        debug_handler.setFormatter(logging.Formatter('%(asctime)s :[%(name)s] %(message)s'))
        logger.addHandler(debug_handler)
    return logger

def init_loggers():
    """Use this func to add or edit list of used loggers"""
    applogger = configure_logger('app')                      
    storage = configure_logger('app.storage')          
    queue_logger = configure_logger('app.queue')
    queue_logger.propagate = False 
    storage.propagate = False
    applogger.propagate = False

    
