#Fastapi/Asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
from contextlib import asynccontextmanager

#Project files
from app.common.config import Config
import app.common.logs as logs
from app.infrastructure.dependencies import DatabaseManager, CacheManager
from app.application.dependencies import UserRepoDependency, PasswordHasher, CurrentUserDependency
import app.application.exceptions as appexc
import app.presentation.routers as routers
import app.presentation.schemas as schemas

#Misc
import datetime
import tzlocal # type: ignore
import os

#Logging
import logging
import loguru # type: ignore





###################
#       App       #
###################

@asynccontextmanager
async def lifespan(app: FastAPI, user_repo: UserRepoDependency):
    logger.info(f'[APP: Startup] Startup began...')

    #Cache
    await CacheManager.wait_for_startup()
    await CacheManager.initialize_data_structures()

    #Database
    await DatabaseManager.wait_for_startup(attempts=Config.DB_WAIT_MAX_RETRIES, interval_sec=Config.DB_WAIT_INTERVAL_SECONDS)
    await DatabaseManager.initialize_data_structures()
    
    #Default_admin
    await user_repo.ensure_admin_exists(PasswordHasher())

    logger.info(f'[APP: Startup] Startup finished!')
    yield
    await CacheManager.close()
    await DatabaseManager.close()
    
    

logs.init_loggers()
logger = logging.getLogger('app')

app = FastAPI(
    title = f'{Config.APP_NAME} commit {Config.GIT_COMMIT}',
    keep_blank_values_in_query_string=True,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": None,
        "displayRequestDuration":True
    },
    lifespan=lifespan, 
    root_path=f"/{Config.APP_NAME}"
)

app.include_router(routers.AuthRouter)
app.include_router(routers.UserRouter)



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

########################################
#        GETTING USER PROFILE          #
########################################

@app.get("/me")
async def whoami(current_user:CurrentUserDependency) -> schemas.UserDTO:
    return current_user


########################
#  Shutdowns & Health  #
########################


# система завершения работы
active_requests = 0
shutdown_event = asyncio.Event()

@app.get("/")
@app.get("/health",include_in_schema=False)
async def read_root():
    """Indicates if the server is alive"""
    
    if shutdown_event.is_set():
        return JSONResponse(status_code=500,content={})
    else:
        return

def handle_shutdown_signal():
    asyncio.ensure_future(initiate_shutdown())

async def initiate_shutdown():
    global shutdown_event
    shutdown_event.clear()
    shutdown_event.set()

    async def _wait_for_requests():
        while active_requests > 0:
            await asyncio.sleep(0.1)

    async def wait_for_requests_to_finish():
        try:
            await asyncio.wait_for(_wait_for_requests(), timeout=10*60)
        except asyncio.TimeoutError:
            print("Выключаемся")
        finally:
            os._exit(0)
    
    await wait_for_requests_to_finish()

import signal
signal.signal(signal.SIGINT, lambda sig, frame: handle_shutdown_signal())
signal.signal(signal.SIGTERM, lambda sig, frame: handle_shutdown_signal())
# система завершения работы

@app.middleware("http")
async def add_logging_middleware(request: Request, call_next):
    try:
        global active_requests
        active_requests += 1

        response = await call_next(request)

        return response
        
    except Exception as e:
        loguru.logger.exception(e)
        return JSONResponse(
            status_code=500,
            content={'successful':False,'detail':'Необработанная ошибка'}
        )
    finally:
        active_requests -= 1



@app.get("/check")
def check(request: Request):
    """Shows how the request is seen by the server + some time info"""

    tz = tzlocal.get_localzone()
    server_dt = datetime.datetime.now(tz)

    response = {
        "headers": dict(request.headers),
        "base_url": str(request.base_url),
        "hostname": str(request.client.host),
        "real_ip": request.headers.get('X-Real-IP',"X-Real-IP is missing"),
        "forwarded_for": request.headers.get('X-Forwarded-For', "X-Forwarded-For is missing"),
        "server_date": {
            "TZ":tz.key,
            "tnname": server_dt.strftime("%Z"),
            "h_tztime": server_dt.utcoffset().total_seconds() / 3600,
            "m_tztime": server_dt.utcoffset().total_seconds() / 60,
            "datetime": server_dt.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "m_timestamp": int(server_dt.timestamp() * 1000),
            "s_timestamp": int(server_dt.timestamp())
        }

    }
    return JSONResponse(content=response)
