from typing import Optional, Any
import os
from pathlib import Path
from loguru import logger
import json

def swagger_ui_parameters() -> Optional[dict[str, Any]]:
    '''
    Allow us to customize the look and feel of the Swagger web UI.
    :return: a customization dictionary from swagger-ui-parameters.json, or None if the file is missing
    :raises: ValueError if the file contains something other than a dictionary
    '''
    path: str = (Path(__file__).parent / ".." / "resources" / "docs" / "swagger-ui-parameters.json").resolve()

    if not os.path.exists(path):
        msg = f"swagger-ui-parameters.json not found: {path}"
        logger.error(msg)
        raise ValueError(msg)

    params: Optional[dict[str, Any]] = None
    with open(path, "r") as f:
        params = json.load(fp=f)

        if not isinstance(params, dict):
            msg = f"Swagger customization file {path} doesn't contain a dict as expected: {params}"
            logger.warning(msg)
            raise ValueError(msg)

        logger.info(f"Using Swagger UI overrides: {params}")
    return params

class MarkdownSlicer:
    def __init__(self, path_to_md: str = None):
        if path_to_md is None:
            self.path_to_md = (Path(__file__).parent / ".." / "resources" / "docs" / "rest-api.md").resolve()
        else:
            self.path_to_md = path_to_md
        self.endpoint_docs = {}
        self.tag_docs = {}
        self.system_description = ""
        self.__parse()

    def __parse(self):
        if not os.path.exists(self.path_to_md):
            msg = f"REST API Markdown file not found: {self.path_to_md}"
            logger.error(msg)
            raise ValueError(msg)

        with open(self.path_to_md, "r") as f:
            lines = f.readlines()

        in_system_description = True
        current_tag = None
        current_endpoint = None
        endpoint_pfx = "## Endpoint: "
        endpoints_pfx = "# Endpoints: "
        for line in lines:
            if line.startswith(endpoints_pfx):
                in_system_description = False
                current_tag = line[len(endpoints_pfx):].replace("`", "").rstrip()
                current_endpoint = None
                if current_tag not in self.tag_docs:
                    self.tag_docs[current_tag] = line
                else:
                    self.tag_docs[current_tag] += line
            elif line.startswith(endpoint_pfx):
                in_system_description = False
                current_endpoint = line[len(endpoint_pfx):].replace("`", "").rstrip()
                current_tag = None
                if current_endpoint not in self.endpoint_docs:
                    self.endpoint_docs[current_endpoint] = line
                else:
                    self.endpoint_docs[current_endpoint] += line
            elif in_system_description:
                self.system_description += line
            elif current_tag is not None:
                self.tag_docs[current_tag] += line
            elif current_endpoint is not None:
                self.endpoint_docs[current_endpoint] += line

    def get_system_description(self):
        if self.system_description is None:
            logger.error("System description not found in the docs object!")
        return self.system_description

    def get_endpoint_docs(self, endpoint):
        if endpoint not in self.endpoint_docs:
            logger.error(f"Endpoint {endpoint} not found in the docs object!")
        return self.endpoint_docs.get(endpoint, "")

    def get_tag_docs(self, tag):
        if tag not in self.tag_docs:
            logger.error(f"Tag {tag} not found in the docs object!")
        return self.tag_docs.get(tag, "")

    def get_openapi_tags(self):
        return [{"name": k, "description": v} for k, v in self.tag_docs.items()]
