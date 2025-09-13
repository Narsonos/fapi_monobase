from app.common.exceptions import AppBaseException

class CustomDatabaseException(AppBaseException):
    """Base for exceptions raised manually in database-related functions"""
    pass

class TableNameIsTooLong(CustomDatabaseException):
    """If table name that is generated automatically based off of .xlsx sheet and file name is too long"""
    pass

class UnsupportedDialectException(CustomDatabaseException):
    """Can be used to show that chosen SQL dialect is not supported by the function"""
    pass