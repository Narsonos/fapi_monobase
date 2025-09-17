from app.common.exceptions import AppBaseException

class CustomStorageException(AppBaseException):
    """Base for exceptions raised manually in storage services (databases, caches)"""

### Databases
class DatabaseException(CustomStorageException): ...

class DatabaseQueryException(DatabaseException): ...

class TableNameIsTooLong(DatabaseQueryException):
    """If table name that is generated automatically based off of .xlsx sheet and file name is too long"""

class UnsupportedDialectException(DatabaseQueryException):
    """Can be used to show that chosen SQL dialect is not supported by the function"""

### Startup
class StorageBootError(CustomStorageException):
    '''Storage service failed to boot within given time'''

class StorageNotInitialzied(CustomStorageException):
    '''Storage service has been booted successfully, yet seems not to be initialized entirely'''