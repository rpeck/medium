from typing import Annotated
import os
from fastapi import FastAPI, Depends, HTTPException, status, Body, Query
import uvicorn
from dotenv import load_dotenv

from pydantic import EmailStr, ValidationError, parse_obj_as
from sqlmodel import Session, select, exists
from sqlmodel.sql.expression import Select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql.elements import ClauseElement

from rest_api.db.common import session_generator, create_tables_if_missing
from rest_api.entities.users import User, UserCreate, UserRead, UserUpdate
from rest_api.entities.companies import Company, CompanyCreate, CompanyRead, CompanyUpdate
from rest_api.entities.search_models import SearchModel

from rest_api.helpers.api_docs_helpers import swagger_ui_parameters, MarkdownSlicer
from rest_api.helpers.examples import ExamplePayloads

from loguru import logger

from argon2 import PasswordHasher
hasher: PasswordHasher = PasswordHasher()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           '.env')

if not os.path.isfile(dotenv_path):
    msg: str = f"Environment file {dotenv_path} not found."
    logger.error(msg)
    raise ValueError(msg)

load_dotenv(dotenv_path)

current_path = os.path.realpath(__file__)
current_directory = os.path.dirname(current_path)
md_slicer: MarkdownSlicer = MarkdownSlicer()

examples = ExamplePayloads()  # NOTE: this is a dir!

rest: FastAPI = FastAPI(
    description=md_slicer.get_system_description(),
    openapi_tags=md_slicer.get_openapi_tags(),
    swagger_ui_parameters=swagger_ui_parameters(),
)

@rest.get("/", tags=["General"], description=md_slicer.get_endpoint_docs("GET /"))
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
            # TODO: we should return the same format detail payload as Pydantic, to ease error reporting in the client
            raise HTTPException(status_code=403, detail=msg) from e


@rest.post("/v1/users", response_model=UserRead, tags=["Users"], status_code=status.HTTP_201_CREATED, description=md_slicer.get_endpoint_docs("POST /v1/users"))
async def create_user(*,
                      session: Session = Depends(session_generator),
                      user: Annotated[
                          UserCreate,
                          Body(openapi_examples=examples.get_examples([
                              "user-create-john-doe",
                              "error-user-create-john-doe-company-type-error",
                              "error-user-create-john-doe-no-password",
                              "error-user-create-john-doe-unknown-company"]))
                      ]) -> User:
    validate_email(user.email)

    # check for the company_id, if it's set
    if user.company_id is not None:
        company_exists: bool = session.query(exists().where(Company.id == int(user.company_id))).scalar()  # noqa

        if not company_exists:
            # TODO: we should return the same format detail payload as Pydantic, to ease error reporting in the client
            raise HTTPException(status_code=404, detail=f"Company {user.company_id} not found for User: {user}")

    try:
        cleartext_password: str = user.password
        del user.password
        db_user = User.model_validate(user)
        db_user.hashed_password = hasher.hash(cleartext_password)
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


@rest.get("/v1/users", response_model=list[UserRead], tags=["Users"], description=md_slicer.get_endpoint_docs("GET /v1/users"))
async def get_all_users(*,
                        session: Session = Depends(session_generator),
                        start_with: int = Query(0, ge=0),
                        max_count: int = Query(default=1000, le=10000)
                        ) -> list[User]:
    users: list[User] = session.query(User).order_by(User.id).offset(start_with).limit(max_count).all()
    if not users:
        raise HTTPException(status_code=404, detail=f"Users not found: {id}")
    return users


@rest.get("/v1/users/{id}", response_model=UserRead, tags=["Users"], description=md_slicer.get_endpoint_docs("GET /v1/users/{id}"))
async def get_user_by_id(*,
                         session: Session = Depends(session_generator),
                         id: int) -> User:
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {id}")
    return user


async def process_user_update(session: Session, id: int, user_data: UserUpdate, partial: bool) -> User:
    '''
    A helper function to either update (PATCH) or replace (PUT) an existing User without changing their `id`.
    '''
    logger.debug(f"Processing update for user: {id}")
    db_user = session.get(User, id)
    if not db_user:
        msg: str = f"User not found: {id}"
        logger.warning(msg)
        raise HTTPException(status_code=404, detail=msg)

    if user_data.email is not None:
        validate_email(user_data.email)

    update_data = user_data.dict(exclude_unset=partial)

    # let the client update the password, but if they don't leave it unchanged
    if "password" in update_data and update_data["password"] is not None:
        update_data["hashed_password"] = hasher.hash(update_data["password"])
    elif "password" in update_data:
        del update_data["password"]

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


@rest.patch("/v1/users/{id}", response_model=UserRead, tags=["Users"], description=md_slicer.get_endpoint_docs("PATCH /v1/users/{id}"))
async def update_user(*,
                      session: Session = Depends(session_generator),
                      id: int,
                      updates: Annotated[
                          UserUpdate,
                          Body(openapi_examples=examples.get_examples([
                              "user-update-jane"
                              ])
                          )]
                      ) -> User:
    return await process_user_update(session, id, updates, partial=True)


@rest.put("/v1/users/{id}", response_model=UserRead, tags=["Users"])
async def replace_user(*,
                       session: Session = Depends(session_generator),
                       id: int,
                       user_data: Annotated[
                          UserUpdate,
                          Body(openapi_examples=examples.get_examples([
                              "user-create-john-doe",
                              "error-user-create-john-doe-company-type-error",
                              "error-user-create-john-doe-no-password",
                              "error-user-create-john-doe-unknown-company"]))
                      ]) -> User:
    return await process_user_update(session, id, user_data, partial=False)


@rest.delete("/v1/users/{id}", tags=["Users"], status_code=status.HTTP_204_NO_CONTENT, description=md_slicer.get_endpoint_docs("DELETE /v1/users/{id}"))
async def delete_user(*, session: Session = Depends(session_generator), id: int) -> None:
    logger.debug(f"DELETEing User: {id}")
    user = session.get(User, id)
    if not user:
        msg: str = f"User not found: {id}"
        logger.warning(msg)
        raise HTTPException(status_code=404, detail=msg)
    try:
        session.delete(user)
        session.commit()
    except Exception as e:
        logger.exception(f"Exception while DELETEing User {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Exception while DELETing User: {id}") from e
    return

@rest.post("/v1/users/search", tags=["Users"], response_model=list[UserRead], description=md_slicer.get_endpoint_docs("POST /v1/users/search"))
async def search_users (*,
                        session: Session = Depends(session_generator),
                        query: Annotated[
                            SearchModel,
                            Body(openapi_examples=examples.get_examples([]))  # TODO!
                        ]):
    logger.debug(f"Searching users with expression: {query.dict(exclude_unset=True)}")

    condition: ClauseElement = query.render_condition()
    try:
        s: Select = select(User).where(condition)  # type: ignore
        results = session.exec(s).all()
        return results
    except SQLAlchemyError as e:
        logger.exception(f"Error occurred during database operation for search tree: {query.dict(exclude_unset=True)}; SQL condition was: {condition.compile(session)}")
        raise HTTPException(500, detail="Internal Server Error occurred")


############################
# Companies CRUD and search:

@rest.post("/v1/companies", response_model=CompanyRead, tags=["Companies"], status_code=status.HTTP_201_CREATED, description=md_slicer.get_endpoint_docs("POST /v1/companies"))
async def create_company(*,
                         session: Session = Depends(session_generator),
                         company: Annotated[
                             CompanyCreate,
                             Body(openapi_examples=[
                                 "company-create-acme",
                                 "error-company-create-no-name",
                                 "error-user-create-john-doe-company-type-error",
                                 "error-user-create-john-doe-unknown-company"
                             ])
                         ]) -> CompanyRead:
    try:
        db_company = Company.model_validate(company)
        session.add(db_company)
        session.commit()
        session.refresh(db_company)
        return db_company
    except IntegrityError as e:
        logger.exception(f"Company CREATE failed: a company with name {company.name} already exists: {e}")
        session.rollback()
        raise HTTPException(status_code=409, detail=f"Company CREATE failed: a company with name {company.name} already exists") from e
    except Exception as e:
        logger.exception(f"Company CREATE failed: {company}")
        session.rollback()
        raise

@rest.get("/v1/companies", response_model=list[CompanyRead], tags=["Companies"], description=md_slicer.get_endpoint_docs("GET /v1/companies"))
async def get_all_users(*,
                        session: Session = Depends(session_generator),
                        start_with: int = Query(0, ge=0),
                        max_count: int = Query(default=1000, le=10000)
                        ) -> list[Company]:
    companies: list[Company] = session.query(Company).order_by(Company.id).offset(start_with).limit(max_count).all()
    if not companies:
        raise HTTPException(status_code=404, detail=f"Companies not found: {id}")
    return companies


@rest.get("/v1/companies/{id}", response_model=CompanyRead, tags=["Companies"], description=md_slicer.get_endpoint_docs("GET /v1/companies/{id}"))
async def get_company_by_id(*, session: Session = Depends(session_generator), id: int) -> CompanyRead:
    company = session.get(Company, id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company not found: {id}")
    return company


async def process_company_update(session: Session, id: int, company_data: CompanyUpdate, partial: bool):
    '''
    A helper function to either update (PATCH) or replace (PUT) an existing Company without changing its `id`.
    '''
    logger.debug(f"Processing update for company: {id}")
    db_company = session.get(Company, id)
    if not db_company:
        msg: str = f"Company not found: {id}"
        logger.warning(msg)
        raise HTTPException(status_code=404, detail=msg)

    update_data = company_data.dict(exclude_unset=partial)

    for key, value in update_data.items():
        setattr(db_company, key, value)

    try:
        session.add(db_company)
        session.commit()
        session.refresh(db_company)
    except Exception as e:
        logger.exception(f"Exception while updating company id: {id}: {e}")
        session.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Exception while updating company id {id} with updates: {update_data}")

    return db_company


@rest.patch("/v1/companies/{id}", response_model=CompanyRead, tags=["Companies"])
async def update_company(*,
                         session: Session = Depends(session_generator),
                         id: int,
                         updates: Annotated[
                             CompanyUpdate,
                             Body(openapi_examples=[
                                 "company-update-yoyodyne",
                             ])
                         ]) -> Company:

    return await process_company_update(session, id, updates, partial=True)


@rest.put("/v1/companies/{id}", response_model=CompanyRead, tags=["Companies"])
async def replace_company(*,
                          session: Session = Depends(session_generator),
                          id: int,
                          company_data: Annotated[
                             CompanyUpdate,
                             Body(openapi_examples=[
                                 "company-create-acme",
                                 "error-company-create-no-name",
                                 "error-user-create-john-doe-company-type-error",
                                 "error-user-create-john-doe-unknown-company"
                             ])
                         ]) -> CompanyRead:

    return await process_company_update(session, id, company_data, partial=False)


@rest.delete("/v1/companies/{id}", tags=["Companies"], status_code=status.HTTP_204_NO_CONTENT, description=md_slicer.get_endpoint_docs("DELETE /v1/companies/{id}"))
async def delete_company(*, session: Session = Depends(session_generator), id: int) -> None:
    logger.debug(f"DELETEing Company: {id}")
    company = session.get(Company, id)
    if not company:
        msg: str = f"Company not found: {id}"
        logger.warning(msg)
        raise HTTPException(status_code=404, detail=msg)
    try:
        session.delete(company)
        session.commit()
    except Exception as e:
        logger.exception(f"Exception while DELETEing Company {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Exception while DELETing Company: {id}") from e
    return

@rest.post("/v1/companies/search", tags=["Companies"], response_model=list[CompanyRead], description=md_slicer.get_endpoint_docs("POST /v1/companies/search"))
async def search_companies (*,
                        session: Session = Depends(session_generator),
                        query: Annotated[
                            SearchModel,
                            Body(openapi_examples=examples.get_examples([]))  # TODO!
                        ]):
    logger.debug(f"Searching companies with expression: {query.dict(exclude_unset=True)}")

    condition: ClauseElement = query.render_condition()
    try:
        s: Select = select(Company).where(condition)  # type: ignore
        results = session.exec(s).all()
        return results
    except SQLAlchemyError as e:
        logger.exception(f"Error occurred during database operation for search tree: {query.dict(exclude_unset=True)}; SQL condition was: {condition.compile(session)}")
        raise HTTPException(500, detail="Internal Server Error occurred")


# When starting the server, create the db tables if they are missing:
create_tables_if_missing()

if __name__ == "__main__":
    logger.info('Starting uvicorn server')
    uvicorn.run('rest_api.rest:rest', host="0.0.0.0", port=8000, reload=True)
