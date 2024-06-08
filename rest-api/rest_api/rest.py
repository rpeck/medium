import os
from fastapi import FastAPI, Depends, HTTPException
import uvicorn
from dotenv import load_dotenv
from loguru import logger
from pydantic import EmailStr, ValidationError, parse_obj_as
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from rest_api.db.common import session_generator, create_tables_if_missing
from rest_api.entities.users import User, UserCreate, UserRead, UserUpdate

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           '.env')

if not os.path.isfile(dotenv_path):
    msg: str = f"Environment file {dotenv_path} not found."
    logger.error(msg)
    raise ValueError(msg)

load_dotenv(dotenv_path)

rest: FastAPI = FastAPI()

@rest.get("/")
async def root():
    return {"message": "Hello World"}


############################
# Users CRUD and search:

def validate_email(email):
    # If it's not a valid EmailStr, a ValidationError will be raised
        try:
            parse_obj_as(EmailStr, email)
        except ValidationError as e:
            msg = f"User CREATE failed: email {email} failed validation"
            logger.exception(f"{msg}: {e}")
            raise HTTPException(status_code=403, detail=msg) from e

@rest.post("/v1/users", response_model=UserRead, tags=["users"]) #  , description=openapi_docs.get_endpoint_doc("POST /api/v1/users/"))
async def create_user(*, session: Session = Depends(session_generator), user: UserCreate) -> UserRead:
    validate_email(user.email)
    try:
        db_user = User.model_validate(user)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except IntegrityError as e:
        logger.exception(f"User CREATE failed: a user with email {user.email} already exists: {e}")
        session.rollback()
        raise HTTPException(status_code=409, detail=f"User CREATE failed: a user with email {user.email} already exists") from e
    except Exception as e:
        logger.exception(f"User CREATE failed: {user}")
        session.rollback()
        raise
@rest.get("/v1/users/{id}", response_model=UserRead, tags=["users"])  # , description=openapi_docs.get_endpoint_doc("GET /api/v1/users/{user_id}"))
async def get_user_by_id(*, session: Session = Depends(session_generator), id: int) -> UserRead:
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {id}")
    return user

async def process_user_update(session: Session, id: int, user_data: UserUpdate, partial: bool):
    logger.debug(f"Processing update for user: {id}")
    db_user = session.get(User, id)
    if not db_user:
        msg: str = f"User not found: {id}"
        logger.warning(msg)
        raise HTTPException(status_code=404, detail=msg)

    if user_data.email is not None:
        validate_email(user_data.email)

    update_data = user_data.dict(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    except Exception as e:
        logger.exception(f"Exception while updating user id: {id}: {e}")
        session.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Exception while updating user id {id} with updates: {update_data}")

    return db_user


@rest.patch("/v1/users/{id}", response_model=UserRead, tags=["users"])
async def update_user(*, session: Session = Depends(session_generator), id: int, updates: UserUpdate):
    return await process_user_update(session, id, updates, partial=True)


@rest.put("/v1/users/{id}", response_model=UserRead, tags=["users"])
async def replace_user(*, session: Session = Depends(session_generator), id: int, user_data: UserUpdate):
    return await process_user_update(session, id, user_data, partial=False)

@rest.delete("/v1/users/{id}", tags=["users"]) # , description=openapi_docs.get_endpoint_doc("DELETE /api/v1/users/{user_id}"))
async def delete_user(*, session: Session = Depends(session_generator), id: int) -> UserRead:
    logger.debug(f"DELETing User: {id}")
    user = session.get(User, id)
    if not user:
        msg: str = f"User not found: {id}"
        logger.warning(msg)
        raise HTTPException(status_code=404, detail=msg)
    try:
        session.delete(user)
        session.commit()
    except Exception as e:
        logger.exception(f"Exception while DELETing User {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Exception while DELETing User: {id}") from e
    return user

# When starting the server, create the db tables if they are missing:
create_tables_if_missing()

if __name__ == "__main__":
    logger.info('Starting uvicorn server')
    uvicorn.run('rest_api:rest', host="0.0.0.0", port=8000, reload=True)
