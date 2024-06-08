from typing import TypeVar, Type
import secrets

import time
from random import choice

from httpx import AsyncClient, Response

from rest_api.entities.users import UserCreate, UserRead, UserBase, UserUpdate
from rest_api.entities.users import test_user_1

from .common import EndpointTestFixtures

UserT = TypeVar("UserT", bound=UserBase)

firstnames: list[str] = ["John", "Billy", "Sally", "Jane"]
lastnames: list[str] = ["Doe", "Bob", "Fields", "Fonda"]
def create_test_user(t: Type[UserT]) -> UserT:
    num: int = int(time.perf_counter() * 1000) % 1000
    user: UserT = t(email="place@holder.com")  # need to set email, since it's required in the table

    user.first_name = choice(firstnames)
    user.last_name = choice(lastnames)
    user.email = f"{user.first_name}.{user.last_name}-{num}@somewhere.com"
    user.hashed_password = secrets.token_urlsafe(8)
    return user

class TestUsersCRUD(EndpointTestFixtures):

    async def test_validate_test_data(self, http_client: AsyncClient) -> None:
        '''
        Check that the expected test data is present in the db.
        '''
        response: Response = await http_client.get("/v1/users/1")
        assert response.status_code == 200

        user_1: UserRead = UserRead(**response.json())
        assert user_1.email == test_user_1.email
        assert user_1.first_name == test_user_1.first_name
        assert user_1.last_name == test_user_1.last_name
        assert not hasattr(user_1, "hashed_password")

    async def test_user_crud(self, http_client: AsyncClient) -> None:
        response: Response

        # test Create (POST):
        test_user_1: UserCreate = create_test_user(UserCreate)
        assert test_user_1.hashed_password is not None

        response = await http_client.post("/v1/users", json=test_user_1.dict())
        assert response.status_code == 200
        created_user_1: UserRead = UserRead(**response.json())

        assert created_user_1.id is not None and created_user_1.id > 1
        assert created_user_1.first_name == test_user_1.first_name
        assert created_user_1.last_name == test_user_1.last_name
        assert created_user_1.email == test_user_1.email
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

        # delete the new user and verify that it's deleted:
        response = await http_client.delete(f"/v1/users/{created_user_1.id}")
        assert response.status_code == 200
        deleted: UserRead = UserRead(**response.json())
        assert not hasattr(deleted, "hashed_password")
        assert deleted.id == created_user_1.id

        # try to read it back:
        response = await http_client.get(f"/v1/users/{created_user_1.id}")
        assert response.status_code == 404
        assert 'User not found:' in response.text

        # try to delete it again:
        response = await http_client.delete(f"/v1/users/{created_user_1.id}")
        assert response.status_code == 404
        assert 'User not found:' in response.text
