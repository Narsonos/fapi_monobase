#Inspired by: michaeloliverx@github

#################################
# Base: Sets up all shared envs #
#################################
FROM python:3.12-slim AS base

#Python settings
    #No buffering for stdout/stderr -> Logs appear instantly
ENV PYTHONBUFFERED=1 \              
    #No pycache -> We rebuild it anyways, so it's useless
    PYTHONDONTWRITEBYTECODE=1\
    #Allows library cache
    PIP_NO_CACHE_DIR=off \
    #Prevents PIP from spamming "new version exists for package X"
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    #Increased timeout for slower networks
    PIP_DEFAULT_TIMEOUT=100 \
#Poetry settings
    #Aug 2025
    POETRY_VERSION=2.1.4 \
    POETRY_HOME="/root/.local" \
    #.venv will be put in project for better caching
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    #disabling interaction for docker/ci automation
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/app" \
    VENV_PATH="/app/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

#################################
# Builder: Builds envs and deps #
#################################
FROM base AS builder

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
       curl \
       build-essential

RUN pip install --no-cache-dir pipx
RUN pipx install poetry==$POETRY_VERSION
RUN pipx ensurepath

WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-ansi --without dev --no-root


#######################################
# Dev_base: Get all dev dependencies  #
#######################################
FROM builder AS dev_base 

ENV FASTAPI_ENV=dev
WORKDIR $PYSETUP_PATH

#Copy Poetry and venv from builder stage
COPY --from=builder $PYSETUP_PATH $PYSETUP_PATH
COPY --from=builder /root/.local/bin/poetry /root/.local/bin/poetry
#All content of Dockerfile parent directory will be copied
COPY . .
RUN poetry install --no-ansi --no-root
WORKDIR /app

##########################
####### Test: runs tests #
##########################
FROM dev_base AS dev
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--proxy-headers"]


###########################
####### Dev: runs FastAPI #
###########################
FROM dev_base AS test
CMD ["poetry", "run", "pytest"]

##################################
# Prod: Minimalistic and light   #
##################################
FROM base AS prod

ENV FASTAPI_ENV=prod
WORKDIR /app

COPY --from=builder $VENV_PATH $VENV_PATH
COPY ./app /app/

ENV PATH="$PYSETUP_PATH/.venv/bin:$PATH"
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "-c", "gunicorn_conf.py"]