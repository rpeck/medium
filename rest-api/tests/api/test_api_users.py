from typing import TypeVar, Type, cast
import secrets

import time
from random import choice

from httpx import AsyncClient, Response

from rest_api.entities.users import UserCreate, UserRead, UserBase, UserUpdate
from rest_api.helpers.examples import ExamplePayloads

from tests.common import EndpointTestFixtures
from tests.helpers.entities_helpers import test_users

UserT = TypeVar("UserT", bound=UserBase)

firstnames: list[str] = ["John", "Billy", "Sally", "Jane"]
lastnames: list[str] = ["Doe", "Bob", "Fields", "Fonda"]
def create_test_user(t: Type[UserT]) -> UserT:
    num: int = int(time.perf_counter() * 1000) % 1000
    user: UserT

    # Need to set required fields when we construct the object!
    if "password" in t.model_fields:  # does this class declare a password instance attribute?
        user = t(email="place@holder.com", password="foo!")
    else:
        user = t(email="place@holder.com")

    user.first_name = choice(firstnames)
    user.last_name = choice(lastnames)
    user.email = f"{user.first_name}.{user.last_name}-{num}@somewhere.com"

    if hasattr(user, "password"):
        user.password = secrets.token_urlsafe(8)
    return user

class TestUsersCRUD(EndpointTestFixtures):

    async def test_user_crud(self, http_client: AsyncClient) -> None:
        response: Response

        try:
            # test Create (POST):
            test_user_0: UserCreate = create_test_user(UserCreate)
            assert test_user_0.password is not None

            response = await http_client.post("/v1/users", json=test_user_0.dict())
            assert response.status_code == 201
            created_user_1: UserRead = UserRead(**response.json())

            assert created_user_1.id is not None
            assert created_user_1.first_name == test_user_0.first_name
            assert created_user_1.last_name == test_user_0.last_name
            assert created_user_1.email == test_user_0.email
            assert not hasattr(created_user_1, "hashed_password")

            # test Read (GET) of the User we just created:
            response = await http_client.get(f"/v1/users/{created_user_1.id}")
            assert response.status_code == 200
            read_user_1: UserRead = UserRead(**response.json())
            assert not hasattr(read_user_1, "hashed_password")
            assert read_user_1.id == created_user_1.id

            # test Update (PATCH) of the User we just created; note: use a raw dict, because we're not including required field `email`:
            updates_patch: dict[str, str] = {
                "first_name": "Raymond",
                "last_name": "Peck",
            }
            response = await http_client.patch(f"/v1/users/{created_user_1.id}", json=updates_patch)
            assert response.status_code == 200

            # read it back:
            response = await http_client.get(f"/v1/users/{created_user_1.id}")
            assert response.status_code == 200
            read_user_1_patched: UserRead = UserRead(**response.json())
            assert not hasattr(read_user_1_patched, "hashed_password")
            assert read_user_1_patched.id == created_user_1.id
            assert read_user_1_patched.first_name == "Raymond"
            assert read_user_1_patched.last_name == "Peck"

            # test that PATCH fails when the user isn't found:
            response = await http_client.patch("/v1/users/1000000000", json=updates_patch)
            assert response.status_code == 404
            assert 'User not found:' in response.text

            # test Update (PUT) of the User we just created; note that this replaces ALL the fields, even if they are None:
            updates_put: UserUpdate = UserUpdate(**{
                "first_name": None,
                "last_name": None,
                "email": created_user_1.email
            })
            response = await http_client.put(f"/v1/users/{created_user_1.id}", json=updates_put.dict(exclude_unset=False))
            assert response.status_code == 200

            # read it back:
            response = await http_client.get(f"/v1/users/{created_user_1.id}")
            assert response.status_code == 200
            read_user_1_put: UserRead = UserRead(**response.json())
            assert not hasattr(read_user_1_put, "hashed_password")
            assert read_user_1_put.id == created_user_1.id
            assert read_user_1_put.first_name is None
            assert read_user_1_put.last_name is None

            # test /users (unfiltered list); check all the users for when we run this against a real server with a real db!
            found_created_user: bool = False
            params = {
                "start_with": 0,
                "max_count": 10000
            }

            http_status_code = None
            while found_created_user is False and http_status_code != 404:
                response = await http_client.get("/v1/users", params=params)
                users = response.json()
                assert isinstance(users, list)

                http_status_code = response.status_code
                for user in users:
                    if user["email"] == created_user_1.email:
                        found_created_user = True
                        break

            assert found_created_user


            # TODO: add /search test!

        finally:  # clean up, whether the code above raised an exception or not
            # delete the new user and verify that it's deleted:
            response = await http_client.delete(f"/v1/users/{created_user_1.id}")
            assert response.status_code == 204

            # try to read it back:
            response = await http_client.get(f"/v1/users/{created_user_1.id}")
            assert response.status_code == 404
            assert 'User not found:' in response.text

            # try to delete it again:
            response = await http_client.delete(f"/v1/users/{created_user_1.id}")
            assert response.status_code == 404
            assert 'User not found:' in response.text

class TestExamples(EndpointTestFixtures):

    async def test_user_create_john_doe(self, http_client: AsyncClient, examples: ExamplePayloads) -> None:
        """Test creating a new user named John Doe is successful and can be deleted afterward."""
        payload = examples.get_example_value('user-create-john-doe')
        del payload['company_id']  # or, we could create a company and use its ID here
        create_response = await http_client.post("/v1/users", json=payload)

        assert create_response.status_code == 201  # Success on creating

        user: UserRead = UserRead(**create_response.json())
        assert user.first_name == payload["first_name"]
        assert user.last_name == payload["last_name"]
        assert user.email == payload["email"]
        assert user.id is not None

        # GET the newly created user by using id from the creation response.
        get_response = await http_client.get(f"/v1/users/{user.id}")

        assert get_response.status_code == 200
        create_response.json() == get_response.json()  # compares all the fields (at the top level of the dict)

        # DELETE the created user.
        delete_response = await http_client.delete(f"/v1/users/{user.id}")
        assert delete_response.status_code == 204  # Success on deleting user

        # Validate if the deletion is successful by trying to get the deleted user.
        get_deleted_user_response = await http_client.get(f"/v1/users/{user.id}")
        assert get_deleted_user_response.status_code == 404  # User should not be found.


    async def test_error_user_create_type_error(self, http_client: AsyncClient, examples: ExamplePayloads) -> None:
        """Ensure that an error is returned if a wrong company type is provided when creating a user."""
        payload = examples.get_example_value('error-user-create-john-doe-company-type-error')
        response = await http_client.post("/v1/users", json=payload)

        assert response.status_code == 422
        detail: dict = response.json()["detail"]
        assert detail[0]["type"] == "int_parsing"
        assert detail[0]["msg"] == "Input should be a valid integer, unable to parse string as an integer"
        assert detail[0]["input"] == "garbage"  # note that by default, Pydantic will convert a stringified int like "42" to its value...
        assert detail[0]["loc"] == ["body", "company_id"]


    async def test_error_user_create_no_password(self, http_client: AsyncClient, examples: ExamplePayloads) -> None:
        """Ensure that an error is returned if no password is provided when creating a user."""
        payload = examples.get_example_value('error-user-create-john-doe-no-password')
        response = await http_client.post("/v1/users", json=payload)

        assert response.status_code == 422
        detail: dict = response.json()["detail"]
        assert detail[0]["type"] == "missing"
        assert detail[0]["msg"] == "Field required"
        assert detail[0]["loc"] == ["body", "password"]


    async def test_error_user_create_unknown_company(self, http_client: AsyncClient, examples: ExamplePayloads) -> None:
        """Ensure that an error is returned if an unknown company is provided when creating a user."""
        payload = examples.get_example_value('error-user-create-john-doe-unknown-company')
        response = await http_client.post("/v1/users", json=payload)

        assert response.status_code == 404
        detail: dict = response.json()["detail"]
        assert "Company 1000000 not found for User" in detail

    async def test_user_update_john_doe(self, http_client: AsyncClient, examples: ExamplePayloads) -> None:
        """Test updating a user named John Doe and validating changes."""
        user_create_payload: dict = cast(dict, examples.get_example_value('user-create-john-doe'))
        del user_create_payload['company_id']  # or, create the company first and use its ID here
        create_response = await http_client.post("/v1/users", json=user_create_payload)
        created_user: UserRead = UserRead(**create_response.json())

        assert created_user.email == user_create_payload['email']
        assert created_user.first_name == user_create_payload['first_name']
        assert created_user.last_name == user_create_payload['last_name']

        # Update the created user
        user_update_payload: dict = cast(dict, examples.get_example_value('user-update-jane'))
        update_response = await http_client.patch(f"/v1/users/{created_user.id}", json=user_update_payload)

        assert update_response.status_code == 200  # Success on updating

        updated_user: UserRead = UserRead(**update_response.json())
        assert updated_user.first_name == user_update_payload["first_name"]
        assert updated_user.last_name == user_create_payload["last_name"]
        assert updated_user.email == user_create_payload["email"]

        # GET the updated user and validate changes.
        get_response = await http_client.get(f"/v1/users/{updated_user.id}")

        assert get_response.status_code == 200
        update_response.json() == get_response.json()  # compares all the fields (at the top level of the dict)

        # DELETE the updated user.
        delete_response = await http_client.delete(f"/v1/users/{updated_user.id}")
        assert delete_response.status_code == 204  # Success on deleting user

        # Validate if the deletion is successful by trying to get the deleted user.
        get_deleted_user_response = await http_client.get(f"/v1/users/{updated_user.id}")
        assert get_deleted_user_response.status_code == 404  # User should not be found.


if __name__ == "__main__":
    pytest.main()
