import app.domain.exceptions as domexc
import app.application.exceptions as appexc
from fastapi.responses import JSONResponse


def register_exception_handlers(app):

    @app.exception_handler(appexc.AuthBaseException)
    async def auth_exception_handler(request, exc: appexc.AuthBaseException):
        mapping = {
            appexc.CredentialsException: 401,
            appexc.InvalidTokenError: 401,
            appexc.TokenExpiredException: 401,
            appexc.LoggedOutException: 403,
        }
        status = mapping.get(type(exc), 500)
        return JSONResponse({"detail": str(exc)}, status_code=status)


    @app.exception_handler(domexc.BaseUserException)
    async def user_exception_handler(request, exc: domexc.BaseUserException):
        mapping = {
            domexc.UserValueError: 422,
            domexc.UserDoesNotExist: 404,
            domexc.UserAlreadyExists: 409,
            domexc.UserIntegrityError: 409,
        }
        status = mapping.get(type(exc), 500)
        return JSONResponse({"detail": str(exc)}, status_code=status)


    @app.exception_handler(domexc.AccessException)
    async def access_exception_handler(request, exc: domexc.AccessException):
        mapping = {
            domexc.ActionNotAllowedForRole: 403,
        }
        status = mapping.get(type(exc), 500)
        return JSONResponse({"detail": str(exc)}, status_code=status)