from app.common.exceptions import AppBaseException

class DomainLayerException(AppBaseException):
    '''Base for domain layer'''



### Access related
class AccessException(AppBaseException):
    '''Base for all exceptions related to access issues'''

class ActionNotAllowedForRole(AccessException):
    """Raised when action is not allowed for current user"""

### Model related
class ModelIntegrityError:
    '''Base for integrity violation exceptons. Use as adapter for repositories' integrity exceptions'''
    def __init__(self, *args, orig: Exception|None = None):
        super().__init__(*args)
        self.orig = orig

class VersionError: ...

####### Users

class BaseUserException(DomainLayerException):
    '''Base for user Exceptions'''

class UserValueError(BaseUserException):
    '''Use within User Domain model methods as ValueError'''

class UserDoesNotExist(BaseUserException):
    '''Raised when user does not exist''' 

class UserIntegrityError(BaseUserException, ModelIntegrityError):
    '''Raised when user model integrity gets violated'''

class UserAlreadyExists(UserIntegrityError):
    '''Raised when user with such ID/Username already exists'''

