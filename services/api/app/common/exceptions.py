from fastapi import HTTPException, status
import traceback

def format_exception_string(e: Exception,source:str = "APP", comment: str = ""): #For loggers
    return f'[{source}: Exception] {comment}\n\nTraceback:\n{traceback.format_exception(e)}'

class AppBaseException(Exception):
    """Global base exception"""
    pass

class CustomDatabaseException(AppBaseException):
    """Base for exceptions raised manually in database-related functions"""
    pass

class TableNameIsTooLong(CustomDatabaseException):
    """If table name that is generated automatically based off of .xlsx sheet and file name is too long"""
    pass

class UnsupportedDialectException(CustomDatabaseException):
    """Can be used to show that chosen SQL dialect is not supported by the function"""
    pass

class SQLException(CustomDatabaseException):
    '''Base for exceptions raised by JSON-SQL constructions'''
    def __init__(self, detail: dict):
        self.detail = detail

    def get_http_exception(self):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=self.detail
        )

class ValueNotAllowed(SQLException):
    '''Raised mostly when some is not in ENUM'''
    pass



#HTTP Exceptions
CredentialsException = lambda: HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail={'error':"Could not validate credentials"},
		headers={"WWW-Authenticate":"Bearer"}
	)

TokenExpiredException = lambda: HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail={'error':"AccessToken expired"},
		headers={"WWW-Authenticate":"Bearer"}
	)

LoggedOutException = lambda: HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail={'error':"Token is valid but User logged out"},
		headers={"WWW-Authenticate":"Bearer"}
	)

UnsupportedImageType = lambda: HTTPException(
		status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
		detail={'error':"Something is wrong with the image type or Content-type header! PNG, JPEG, JPG"}
	)

MoreThanOneRequest = lambda: HTTPException(
		status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
		detail={"error":"This operation allows 1 request being processed at once"}
	)

UserAlreadyExistsError = lambda: HTTPException(
        status_code=status.HTTP_409_CONFLICT, 
        detail={"error":f"User with this username already exists!"}
    )

UserDoesNotExist = lambda: HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, 
        detail={"error":f"User does not exist!"}
    )

NotAllowed = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"error":'You do not have enough rights for this operation!'}
)
