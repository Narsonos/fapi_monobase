from app.common.exceptions import AppBaseException

class DomainLayerException(AppBaseException):
    '''Base for domain layer'''
    


###############
#   USER EXC  #
###############

class BaseUserException(DomainLayerException):
    '''Base for user Exceptions'''

class UserDoesNotExist(BaseUserException):
    '''Raised when user does not exist''' 

class UserAlreadyExists(BaseUserException):
    '''Raised when user with such ID/Username already exists'''
    