from datetime import datetime,date
import logging
import re

logger = logging.getLogger('app')




####################
# Common utilities #
####################

def json_serializer(obj):
    #add conversions for non-serializable stuff here
    if isinstance(obj,(datetime,date)):
        return obj.isoformat()
    raise TypeError(f"{type(obj)} is not serializable!")

