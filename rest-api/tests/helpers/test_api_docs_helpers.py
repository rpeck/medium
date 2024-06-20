import os
import pytest
from helpers.api_docs_helpers import MarkdownSlicer


def test_markdown_file_parser():
    current_path = os.path.realpath(__file__)
    current_directory = os.path.dirname(current_path)
    md_slicer = MarkdownSlicer()

    system_description = md_slicer.get_system_description()
    assert "best practices for building APIs using `FastAPI` and `SQLModel`." in system_description

    users_tag_docs = md_slicer.get_tag_docs("Users")
    assert "# Endpoints: Users\n" in users_tag_docs
    assert "`User` entities represent the users of this system" in users_tag_docs
    assert "## Endpoint: GET /v1/users/{id}\n" not in users_tag_docs

    endpoint_docs = md_slicer.get_endpoint_docs("GET /v1/users/{id}")
    assert "## Endpoint: `GET /v1/users/{id}`\n" in endpoint_docs
    assert "If the User is not found, it returns an `http` `404` error." in endpoint_docs

    openapi_tags = md_slicer.get_openapi_tags()
    assert len(openapi_tags) > 0
    assert any(tag['name'] == "Users" for tag in openapi_tags)


# Run it with pytest
if __name__ == "__main__":
    pytest.main(["-v", __file__])
