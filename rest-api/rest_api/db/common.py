from typing import Optional

from datetime import datetime

from environs import Env

from sqlalchemy import Engine
from sqlmodel import SQLModel, Session, create_engine, Session as SQLModelSession
from contextlib import contextmanager

from loguru import logger

def _db_url() -> str:

    # NOTE: for PostgreSQL, the URL will look something like:
    # f"postgresql://username:password@hostname/database_name"
    #
    # Use "sqlite://" for an in-memory db
    env: Env = Env()
    env_var: Optional[str] = env.str("DATABASE_URL", None)
    if env_var is not None:
        return env_var

    # Use SQLite in /tmp, so we can examine it:
    now = datetime.now()
    iso_date = now.isoformat()
    return f"sqlite:////tmp/test-{iso_date.replace('/', '_')}.sqlite"

_engine: Engine = create_engine(url=_db_url(), pool_pre_ping=True)

def session_generator():
    '''
    Return a Session in a way that's compatible with the FastAPI Depends() functionality.

    For use with Depends(), see: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/

    Note that return does not support the context manager protocol for use with `with` statements.
    See: https://stackoverflow.com/questions/75118223/working-with-generator-context-manager-in-fastapi-db-session
    '''
    with Session(_engine) as session:
        yield session

@contextmanager
def create_session() -> Session:
    '''
    Context manager to remove boilerplate when creating and using a session.
    See: https://stackoverflow.com/a/29805305/14573842
    '''
    session = SQLModelSession(_engine, expire_on_commit=False)
    try:
        yield session
    except Exception as e:
        logger.exception(e)
        session.rollback()
        raise
    finally:
        session.close()

def create_tables_if_missing() -> None:
    from rest_api.entities.users import test_user_1

    logger.info(f"Creating tables in {_engine}...")
    SQLModel.metadata.create_all(_engine, checkfirst=True)

    with create_session() as session:
        logger.info("Adding test records to db...")
        session.add(test_user_1)
        session.commit()
