from typing import TypeVar, Type

import time
from random import choice

from httpx import AsyncClient, Response

from rest_api.entities.companies import CompanyCreate, CompanyRead, CompanyBase, CompanyUpdate
from rest_api.entities.companies import test_company_1

from .common import EndpointTestFixtures

CompanyT = TypeVar("CompanyT", bound=CompanyBase)

streets: list[str] = ["Main St", "First St", "Telegraph St", "Water St"]
def create_test_company(t: Type[CompanyT]) -> CompanyT:
    num: int = int(time.perf_counter() * 1000) % 1000
    company: CompanyT = t(name=f"Test Company-{num}")  # need to set name, since it's required in the table

    company.address = f"{num} {choice(streets)}"
    return company

class TestCompaniesCRUD(EndpointTestFixtures):

    async def test_validate_test_data(self, http_client: AsyncClient) -> None:
        '''
        Check that the expected test data is present in the db.
        '''
        response: Response = await http_client.get("/v1/companies/1")
        assert response.status_code == 200

        company_1: CompanyRead = CompanyRead(**response.json())
        assert company_1.name == test_company_1.name
        assert company_1.address == test_company_1.address

    async def test_company_crud(self, http_client: AsyncClient) -> None:
        response: Response

        # test Create (POST):
        test_company_1: CompanyCreate = create_test_company(CompanyCreate)

        response = await http_client.post("/v1/companies", json=test_company_1.dict())
        assert response.status_code == 200
        created_company_1: CompanyRead = CompanyRead(**response.json())

        assert created_company_1.id is not None and created_company_1.id > 1
        assert created_company_1.name == test_company_1.name
        assert created_company_1.address == test_company_1.address

        # test Read (GET) of the Company we just created:
        response = await http_client.get(f"/v1/companies/{created_company_1.id}")
        assert response.status_code == 200
        read_company_1: CompanyRead = CompanyRead(**response.json())
        assert read_company_1.id == created_company_1.id

        # test Update (PATCH) of the Company we just created; note: use a raw dict, because we're not including required field `email`:
        updates_patch: dict[str, str] = {
            "address": "101 My Street",
        }
        response = await http_client.patch(f"/v1/companies/{created_company_1.id}", json=updates_patch)
        assert response.status_code == 200

        # read it back:
        response = await http_client.get(f"/v1/companies/{created_company_1.id}")
        assert response.status_code == 200
        read_company_1_patched: CompanyRead = CompanyRead(**response.json())
        assert read_company_1_patched.id == created_company_1.id
        assert read_company_1_patched.address == "101 My Street"

        # test that PATCH fails when the company isn't found:
        response = await http_client.patch("/v1/companies/1000000000", json=updates_patch)
        assert response.status_code == 404
        assert 'Company not found:' in response.text

        # test Update (PUT) of the Company we just created; note that this replaces ALL the fields, even if they are None:
        updates_put: CompanyUpdate = CompanyUpdate(**{
            "name": test_company_1.name,
            "address": None,
        })
        response = await http_client.put(f"/v1/companies/{created_company_1.id}", json=updates_put.dict(exclude_unset=False))
        assert response.status_code == 200

        # read it back:
        response = await http_client.get(f"/v1/companies/{created_company_1.id}")
        assert response.status_code == 200
        read_company_1_put: CompanyRead = CompanyRead(**response.json())
        assert read_company_1_put.id == created_company_1.id
        assert read_company_1_put.address is None

        # delete the new company and verify that it's deleted:
        response = await http_client.delete(f"/v1/companies/{created_company_1.id}")
        assert response.status_code == 200
        deleted: CompanyRead = CompanyRead(**response.json())
        assert deleted.id == created_company_1.id

        # try to read it back:
        response = await http_client.get(f"/v1/companies/{created_company_1.id}")
        assert response.status_code == 404
        assert 'Company not found:' in response.text

        # try to delete it again:
        response = await http_client.delete(f"/v1/companies/{created_company_1.id}")
        assert response.status_code == 404
        assert 'Company not found:' in response.text
