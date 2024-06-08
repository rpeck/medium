from typing import Optional
from environs import Env

from httpx import AsyncClient, ASGITransport
import pytest

from loguru import logger

from rest_api.rest import rest

env: Env = Env()
host: Optional[str] = env.str("SERVER_HOST", None)
timeout: int = env.int("TEST_CLIENT_TIMEOUT", 30)

class EndpointTestFixtures:
    @pytest.fixture
    def http_client(self):
        '''
        Note: we use `yield` for this fixture so that we can wrap the test with logging.
        :return: http test client that may connect directly to the server code, or to a running instance via the network
        '''
        if host is None:
            client: AsyncClient = AsyncClient(transport=ASGITransport(app=rest), base_url="http://")
            logger.debug(f"Returning direct http test client: {client}")
            yield client  # this client goes through the full FastAPI request stack without launching a server instance
            logger.debug(f"Done with direct http test client: {client}")
        else:
            logger.debug(f"Returning http test client for host {host}: {client}...")
            yield AsyncClient(base_url=host, timeout=timeout)  # this client lets us point the tests at a running instance
            logger.debug(f"Done with http test client for host {host}: {client}.")
