import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from common import EndpointTestFixtures
from rest_api.rest import validate_email

class TestGeneralApiEndpoints(EndpointTestFixtures):
    pass

class TestEmailValidation(EndpointTestFixtures):
    def test_validate_email_valid(self, http_client: AsyncClient):
        try:
            validate_email("test@example.com")
        except HTTPException as e:
            pytest.fail("HTTPException raised unexpectedly! {e}")


    def test_validate_email_invalid(self, http_client: AsyncClient):
        with pytest.raises(HTTPException):
            validate_email("not-an-email")


if __name__ == "__main__":
    pytest.main()
