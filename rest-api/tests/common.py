from typing import Optional, Generator
from environs import Env  # type: ignore[import-untyped]

from httpx import AsyncClient, ASGITransport
import pytest

from sqlmodel import Session

from rest_api.db.common import ephemeral_transaction_scope, create_tables_if_missing
from rest_api.rest import rest
from rest_api.helpers.examples import ExamplePayloads

from loguru import logger

env: Env = Env()
host: Optional[str] = env.str("TEST_SERVER_HOST", None)
timeout: int = env.int("TEST_CLIENT_TIMEOUT", 30)

class EndpointTestFixtures:
    @pytest.fixture
    def http_client(self) -> Generator[AsyncClient, None, None]:
        '''
        This is a pytest fixture. It will automagically be run by the pytest framework if it's specified in
        the params list of your test case.

        Note: we use `yield` rather than `return` for this fixture so that we can wrap the test with logging.
        :returns: http test client that may connect directly to the server code, or to a running instance via the network
        '''
        client: AsyncClient
        if host is None:
            client = AsyncClient(transport=ASGITransport(app=rest), base_url="http://")  # type: ignore[arg-type]
            logger.debug(f"Returning direct http test client: {client}")
            yield client  # this client goes through the full FastAPI request stack without launching a server instance
            logger.debug(f"Done with direct http test client: {client}")
        else:
            client = AsyncClient(base_url=host, timeout=timeout)
            logger.debug(f"Returning http test client for host {host}: {client}...")
            yield client  # this client lets us point the tests at a running instance
            logger.debug(f"Done with http test client for host {host}: {client}.")

    @pytest.fixture(scope="module", autouse=True)
    def examples(self) -> ExamplePayloads:
        '''
        Parse and return the examples JSON payloads for our tests to use.
        '''
        return ExamplePayloads()

    @pytest.fixture
    def ephemeral_session(self) -> Generator[Session, None, None]:
        '''
        Create an ephemeral database transaction when we enter a test function, so that any
        database effects are rolled back at the end of the test, whether or not it passes.
        '''
        with ephemeral_transaction_scope() as session:
            yield session

    '''
    Create our database tables once when we run the tests in a module. 
    '''
    @pytest.fixture(scope="module", autouse=True)
    def set_up_db(self):
        create_tables_if_missing()
