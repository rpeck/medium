from rest_api.db.common import create_test_entities
from rest_api.entities.search_models import SearchModel
from rest_api.entities.users import User
from rest_api.entities.companies import Company


test_users: list[SearchModel] = [
    User(email="rpeck@rpeck.com", first_name="Raymond", last_name="Peck", company_id=1),
    User(**{"type": "User", "first_name": "John", "last_name": "Doe", "company_id": 1000000042,
            "email": "John.Doe@company1000000042.com"}),
    User(**{"type": "User", "first_name": "John", "last_name": "Doe", "company_id": 1,
            "email": "John.Doe@munsters.com"}),
    User(**{"type": "User", "first_name": "John", "last_name": "Schmoe", "email": "John.Schmoe@company.com"}),
    User(**{"type": "User", "first_name": "Jane", "last_name": "Doe", "company_id": 1000000024,
            "email": "Jane.Doe@company1000000024.com"}),
]

test_companies: list[SearchModel] = [
    Company(name="Munsters, Inc", address="1313 Mockingbird Lane"),
    Company(**{"type": "Company ", "name": "Acme", "id": 1000000042}),
    Company(**{"type": "Company ", "name": "Tyrell Corporation", "id": 1000000024}),
]

def add_test_entities_john_doe(session):
    create_test_entities(session=session, entities=test_users)

def validate_john_doe_1000000042(user: User):
    assert isinstance(user, User)
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.email == "John.Doe@company1000000042.com"
    assert user.company_id == 1000000042
    assert user.id is not None and user.id > 1

def validate_john_doe_1(user: User):
    assert isinstance(user, User)
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.email == "John.Doe@munsters.com"
    assert user.company_id == 1
    assert user.id is not None and user.id > 1

def validate_raymond_peck_1(user: User):
    assert isinstance(user, User)
    assert user.first_name == "Raymond"
    assert user.last_name == "Peck"
    assert user.company_id == 1
    assert user.id == 1

def validate_john_schmoe_none(user: User):
    assert isinstance(user, User)
    assert user.first_name == "John"
    assert user.last_name == "Schmoe"
    assert user.company_id is None

def validate_jane_doe_1000000024(user: User):
    assert isinstance(user, User)
    assert user.first_name == "Jane"
    assert user.last_name == "Doe"
    assert user.company_id == 1000000024

def add_test_entities_acme_tyrell(session):
    create_test_entities(session=session, entities=test_companies)

def validate_acme_1000000042(company):
    assert isinstance(company, Company)
    assert company.id == 1000000042
    assert company.name == "Acme"

def validate_tyrell_1000000024(company):
    assert isinstance(company, Company)
    assert company.id == 1000000024
    assert company.name == "Tyrell"
