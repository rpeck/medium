import pytest

# use jsondiff to compare dictionaries, because we want to disregard key order
from jsondiff import diff  # type: ignore[import-untyped]
from sqlmodel import Session
from pydantic import ValidationError, parse_obj_as

from rest_api.entities.search_models import (SearchModel,
                                             AndSearchModel, OrSearchModel, NotSearchModel,
                                             UserSearchModel, CompanySearchModel,
                                             entities_for_search_model)
from rest_api.entities.users import User
from rest_api.entities.companies import Company
from rest_api.helpers.examples import ExamplePayloads

from tests.common import EndpointTestFixtures
from tests.helpers.entities_helpers import add_test_entities_john_doe, add_test_entities_acme_tyrell
from tests.helpers.entities_helpers import (validate_raymond_peck_1, validate_john_doe_1, validate_john_doe_1000000042, validate_john_schmoe_none, validate_jane_doe_1000000024,
                                            validate_acme_1000000042, validate_tyrell_1000000024)

from loguru import logger

class TestSearchEntitySerializationDeserialization(EndpointTestFixtures):
    # Successful serialization and deserialization test
    def test_user_search_model(self, examples: ExamplePayloads):
        payload = examples.get_example_value("user-search-simple")
        model = UserSearchModel(**payload)
        assert not diff(model.dict(exclude_unset=True), payload)

        # If invalid data provided, should raise ValidationError
        with pytest.raises(ValidationError):
            UserSearchModel(**{"type": "User", "invalid_field": "John"})


    # Complex query deserialization and serialization test
    def test_complex_expression(self, examples: ExamplePayloads):
        user_search_1 = UserSearchModel(type="User", first_name="John")
        user_search_2 = UserSearchModel(type="User", last_name="Smith")
        not_search = NotSearchModel(type="Not", child=user_search_1)
        or_search = OrSearchModel(type="Or", children=[not_search, user_search_2])
        company_search = UserSearchModel(type="User", company_id=1000000042)
        and_search = AndSearchModel(type="And", children=[company_search, or_search])

        # The AST as a dict
        serialized = and_search.dict(exclude_unset=True)

        # Deserialize it back to a Pydantic object
        deserialized = AndSearchModel(**serialized)

        # Both objects should be the same
        assert not diff(serialized, deserialized.dict(exclude_unset=True))

    def test_complex_expression_with_dict(self, examples: ExamplePayloads):
        payload = examples.get_example_value("user-search-and-of-or")
        model = AndSearchModel(**payload)

        assert not diff(model.dict(exclude_unset=True), payload)


    def test_complex_expression_with_model(self, examples: ExamplePayloads):
        user_search_1 = UserSearchModel(type='User', first_name="John")
        not_search = NotSearchModel(type='Not', child=user_search_1)
        user_search_2 = UserSearchModel(type='User', last_name="Smith")
        or_search = OrSearchModel(type='Or', children=[not_search, user_search_2])
        company_search = UserSearchModel(type='User', company_id=1000000042)
        and_search = AndSearchModel(type='And', children=[company_search, or_search])

        assert not diff(and_search.dict(exclude_unset=True),
                        examples.get_example_value("user-search-and-of-or"))

class TestPydanticErrorChecking(EndpointTestFixtures):
    def test_pydantic_type_checking(self):
        '''
        Test that Pydantic raises a ValidationError when we try to deserialize bad data.
        '''
        with pytest.raises(ValidationError):
            user = UserSearchModel(type='User', first_name=123)

        with pytest.raises(ValidationError):
            user = UserSearchModel(type='User', id="not a number")

        with pytest.raises(ValidationError):
            user = UserSearchModel(type='User', email=12345)

    def test_pydantic_validate_assignment(self):
        '''
        Test that Pydantic raises a ValidationError when we try to assign bad data. Runtime error checking ftw!
        '''
        user = UserSearchModel(type='User', first_name="John", id=1, email="john.doe@example.com")

        with pytest.raises(ValidationError):
            user.first_name = 123  # first_name should be a str

        with pytest.raises(ValidationError):
            user.id = "not a number"  # id should be an int

        with pytest.raises(ValidationError):
            user.email = 12345  # email should be a str

    def test_invalid_type(self, examples: ExamplePayloads):
        data = examples.get_example_value("invalid-payload-type")
        with pytest.raises(ValidationError):
            # An exception should be raised as InvalidSearchModel type doesn't exist
            parse_obj_as(SearchModel, data)

    def test_unknown_field_name_user_search_model(self, examples: ExamplePayloads):
        payload = examples.get_example_value("error-user-search-unknown-field")
        with pytest.raises(ValidationError):
            model = parse_obj_as(SearchModel, payload)

    def test_string_company_id_user_search_model(self, examples: ExamplePayloads):
        payload = examples.get_example_value("error-user-search-string-company-id")
        with pytest.raises(ValidationError):
            model = parse_obj_as(SearchModel, payload)

    def test_dict_first_name_user_search_model(self, examples: ExamplePayloads):
        payload = examples.get_example_value("error-user-search-dict-first-name")
        with pytest.raises(ValidationError):
            model = parse_obj_as(SearchModel, payload)


class TestSearchModelPolymorphicDeserializationAndSearch(EndpointTestFixtures):
    def test_user_search_mode_simple(self, ephemeral_session: Session, examples: ExamplePayloads):
        logger.info(f"{ephemeral_session=}")
        payload = examples.get_example_value("user-search-simple")
        model: UserSearchModel = parse_obj_as(SearchModel, payload)

        assert isinstance(model, UserSearchModel)
        assert model.dict(exclude_unset=True) == payload
        assert model.first_name == payload["first_name"]
        assert model.last_name == payload["last_name"]
        assert model.company_id is None

        # Ok, the tree looks good. Let's test the search in the db!

        condition = model.render_condition()

        add_test_entities_john_doe(ephemeral_session)
        results = ephemeral_session.query(User).filter(condition).order_by(User.id).all()

        assert len(results) == 2

        user_0 = results[0]
        validate_john_doe_1000000042(user_0)

        user_1 = results[1]
        validate_john_doe_1(user_1)


    def test_and_search_model(self, ephemeral_session: Session, examples: ExamplePayloads):
        logger.info(f"{ephemeral_session=}")
        payload = examples.get_example_value("user-search-by-company-id-and-name")
        model = parse_obj_as(SearchModel, payload)
        assert isinstance(model, AndSearchModel)
        assert model.dict(exclude_unset=True) == payload

        assert len(model.children) == 2
        assert model.children[0].first_name == "John"
        assert model.children[0].company_id is None

        assert model.children[1].first_name is None
        assert model.children[1].company_id == 1000000042

        # Ok, the tree looks good. Let's test the search in the db!

        condition = model.render_condition()

        add_test_entities_john_doe(ephemeral_session)
        results = ephemeral_session.query(User).filter(condition).order_by(User.id).all()

        assert len(results) == 1
        user = results[0]
        validate_john_doe_1000000042(user)

    def test_company_search_model(self, ephemeral_session: Session, examples: ExamplePayloads):
        payload = examples.get_example_value("company-search-by-id")
        model: CompanySearchModel = parse_obj_as(SearchModel, payload)

        assert isinstance(model, CompanySearchModel)
        assert model.dict(exclude_unset=True) == payload
        assert model.id == payload["id"]

        # Ok, the tree looks good. Let's test the search in the db!

        condition = model.render_condition()

        add_test_entities_acme_tyrell(ephemeral_session)
        results = ephemeral_session.query(Company).filter(condition).order_by(Company.id).all()

        assert len(results) == 1
        user_0 = results[0]
        validate_acme_1000000042(user_0)

    def test_or_search_model(self, ephemeral_session: Session, examples: ExamplePayloads):
        payload = examples.get_example_value("user-search-by-name-or-company-id")
        model = parse_obj_as(SearchModel, payload)
        assert isinstance(model, OrSearchModel)
        assert model.dict(exclude_unset=True) == payload

        assert len(model.children) == 2
        assert model.children[0].last_name == "Doe"
        assert model.children[0].company_id is None

        assert model.children[1].first_name is None
        assert model.children[1].company_id == 1000000024

        # Ok, the tree looks good. Let's test the search in the db!

        condition = model.render_condition()

        add_test_entities_john_doe(ephemeral_session)
        results = ephemeral_session.query(User).filter(condition).all()

        assert len(results) == 3

        user_0 = results[0]
        validate_john_doe_1000000042(user_0)

        user_1 = results[1]
        validate_john_doe_1(user_1)

        user_2 = results[2]
        validate_jane_doe_1000000024(user_2)

    def test_not_search_model(self, ephemeral_session: Session, examples: ExamplePayloads):
        payload = examples.get_example_value("user-search-not-named-john")
        model = parse_obj_as(SearchModel, payload)
        assert isinstance(model, NotSearchModel)
        assert model.dict(exclude_unset=True) == payload

        # Ok, the tree looks good. Let's test the search in the db!

        condition = model.render_condition()

        add_test_entities_john_doe(ephemeral_session)
        results = ephemeral_session.query(User).filter(condition).order_by(User.id).all()

        assert len(results) == 2

        user_0 = results[0]
        validate_raymond_peck_1(user_0)

        user_1 = results[1]
        validate_jane_doe_1000000024(user_1)
        assert user_1.id is not None and user_1.id > 1

    def test_nested_depth_three_search_model(self, ephemeral_session: Session, examples: ExamplePayloads):
        payload = examples.get_example_value("user-search-depth-three")
        model = parse_obj_as(SearchModel, payload)

        assert isinstance(model, AndSearchModel)
        assert model.dict(exclude_unset=True) == payload

        # Ok, the tree looks good. Let's test the search in the db!

        condition = model.render_condition()

        add_test_entities_john_doe(ephemeral_session)
        results = ephemeral_session.query(User).filter(condition).order_by(User.id).all()

        assert len(results) == 1

        user_0 = results[0]
        validate_john_doe_1(user_0)

class TestEntitiesForSearchModel(EndpointTestFixtures):
    '''
    Tests of the entities_for_search_model() function.
    '''
    def test_user_search_and_of_or(self, ephemeral_session: Session, examples: ExamplePayloads):
        payload = examples.get_example_value('user-search-and-of-or')
        result = entities_for_search_model(payload)

        assert len(result) == 3
        assert all([ isinstance(entity, UserSearchModel) for entity in result ])
        assert all([ entity.type == "User" for entity in result] )

        assert isinstance(result[0], UserSearchModel)
        assert result[0].company_id == 1000000042

        assert isinstance(result[1], UserSearchModel)
        assert result[1].first_name == "John"

        assert isinstance(result[2], UserSearchModel)
        assert result[2].last_name == "Smith"

    def test_user_search_depth_three(self, ephemeral_session: Session, examples: ExamplePayloads):
        payload = examples.get_example_value('user-search-depth-three')
        result = entities_for_search_model(payload)

        assert len(result) == 4
        assert all([ isinstance(entity, UserSearchModel) for entity in result ])
        assert all([ entity.type == "User" for entity in result] )

        assert isinstance(result[0], UserSearchModel)
        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"

        assert isinstance(result[1], UserSearchModel)
        assert result[1].first_name == "John"
        assert result[1].last_name == "Doe"

        assert isinstance(result[2], UserSearchModel)
        assert result[2].company_id == 1000000042

        assert isinstance(result[2], UserSearchModel)
        assert result[3].company_id == 1000000042

    def test_user_search_simple(self, ephemeral_session: Session, examples: ExamplePayloads):
        payload = examples.get_example_value('user-search-simple')
        result = entities_for_search_model(payload)

        assert len(result) == 1
        assert all([ isinstance(entity, UserSearchModel) for entity in result ])
        assert all([ entity.type == "User" for entity in result] )

        assert isinstance(result[0], UserSearchModel)
        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"

if __name__ == "__main__":
    pytest.main()
