import pytest
from sqlmodel.sql.expression import Select
from pydantic import parse_obj_as
from sqlalchemy import create_engine

from rest_api.entities.search_models import SearchModel, entity_class_for_tree

class TestSelectGeneration:
    # Initialize a SQLite memory-only database engine
    engine = create_engine('sqlite:///:memory:')

    def test_user_select(self):
        user_dict = {
            "type": "User",
            "first_name": "John"
        }
        obj = parse_obj_as(SearchModel, user_dict)
        select_obj = Select(entity_class_for_tree(obj)).where(obj.render_condition())
        compiled_sql = select_obj.compile(self.engine)
        assert str(compiled_sql) == (
            "SELECT users.first_name, users.last_name, users.company_id, users.id, users.hashed_password, users.email \n"
            "FROM users \n" 
            "WHERE users.first_name = ?"
        )

    def test_company_select(self):
        company_dict = {
            "type": "Company",
            "id": 1,
            "name": "Tech Corp"
        }
        obj = parse_obj_as(SearchModel, company_dict)
        select_obj = Select(entity_class_for_tree(obj)).where(obj.render_condition())
        compiled_sql = select_obj.compile(self.engine)
        assert str(compiled_sql) == (
            "SELECT companies.name, companies.address, companies.id \n" 
            "FROM companies \n" 
            "WHERE companies.id = ? AND companies.name = ?"
        )

    def test_not_select(self):
        not_dict = \
        {
            "type": "Not",
            "child": {
                "type": "User",
                "first_name": "John"}
        }
        obj = parse_obj_as(SearchModel, not_dict)
        select_obj = Select(entity_class_for_tree(obj)).where(obj.render_condition())
        compiled_sql = select_obj.compile(self.engine)
        assert str(compiled_sql) == (
            "SELECT users.first_name, users.last_name, users.company_id, users.id, users.hashed_password, users.email \n" 
            "FROM users \n" 
            "WHERE users.first_name != ?"
        )

    def test_and_select(self):
        and_dict = {
            "type": "And",
            "children": [
                {"type": "User", "first_name": "John"},
                {"type": "User", "last_name": "Smith"},
                {"type": "User", "company_id": 1}
            ]
        }
        obj = parse_obj_as(SearchModel, and_dict)
        select_obj = Select(entity_class_for_tree(obj)).where(obj.render_condition())
        compiled_sql = select_obj.compile(self.engine)
        assert str(compiled_sql) == (
            "SELECT users.first_name, users.last_name, users.company_id, users.id, users.hashed_password, users.email \n" 
            "FROM users \n" 
            "WHERE users.first_name = ? AND users.last_name = ? AND users.company_id = ?"
        )

    def test_or_select(self):
        or_dict = {
            "type": "Or",
            "children": [
                {"type": "User", "first_name": "John"},
                {"type": "User", "first_name": "Jane"},
                {"type": "User", "first_name": "Doe"}
            ]
        }
        obj = parse_obj_as(SearchModel, or_dict)
        select_obj = Select(entity_class_for_tree(obj)).where(obj.render_condition())
        compiled_sql = select_obj.compile(self.engine)
        assert str(compiled_sql) == (
            "SELECT users.first_name, users.last_name, users.company_id, users.id, users.hashed_password, users.email \n" 
            "FROM users \n" 
            "WHERE users.first_name = ? OR users.first_name = ? OR users.first_name = ?"
        )

    def test_nested_search_select(self):
        complex_dict = {
            "type": "And",
            "children": [
                {
                    "type": "Or",
                    "children": [
                        {"type": "User", "first_name": "John"},
                        {"type": "User", "first_name": "Jane"}
                    ]
                },
                {
                    "type": "User",
                    "company_id": 1
                }
            ]
        }
        obj = parse_obj_as(SearchModel, complex_dict)
        select_obj = Select(entity_class_for_tree(obj)).where(obj.render_condition())
        compiled_sql = select_obj.compile(self.engine)
        assert str(compiled_sql) == (
            "SELECT users.first_name, users.last_name, users.company_id, users.id, users.hashed_password, users.email \n" 
            "FROM users \n"
            "WHERE (users.first_name = ? OR users.first_name = ?) AND users.company_id = ?"
        )


if __name__ == "__main__":
    pytest.main()
