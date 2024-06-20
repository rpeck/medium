import os
from typing import Optional, Any, Union
import json
from pathlib import Path
from pydantic import BaseModel

from loguru import logger
class OpenAPIExample(BaseModel):
    '''
    Class to manage examples in OpenAPI format.
    See: https://fastapi.tiangolo.com/tutorial/schema-extra-example/#using-the-openapi_examples-parameter
    '''
    summary: Optional[str] = None
    description: Optional[str] = None
    value: Union[dict, list]

class ExamplePayloads:
    """
    Class to load and parse OpenAPI example JSON files.

    - directory: The path where JSON files for examples are stored, typically `resources/examples`.
    """

    def __init__(self, directory: str = None):
        if directory is None:
            # Get the current file's directory, move up to the project root and then down to 'resources/examples':
            directory = (Path(__file__).parent / '..' / 'resources' / 'examples').resolve()
        if not os.path.exists(directory) or not os.path.isdir(directory):
            msg = f"REST API examples directory does not exist or is not a directory: {directory}"
            logger.error(msg)
            raise ValueError(msg)
        self.directory = directory

    def get_example(self, example_name: str) -> OpenAPIExample:
        """
        Load and parse a JSON file to an OpenAPIExample instance.

        :param example_name: The name of the example (excluding the .json file extension)
        :return: An instance of OpenAPIExample with data parsed from the JSON file.
        """
        file_path = Path(self.directory) / f"{example_name}.json"
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
        example = OpenAPIExample(**data)
        return example

    def get_example_value(self, example_name: str) -> dict[str, Any]:  # TODO: tighten up the types!
        """
        Retrieves the 'value' field from the specific example. This is the actual example payload.

        :param example_name: The name of the example.
        :return: The JSON payload for the example.
        """
        example = self.get_example(example_name)
        return example.value

    def get_example_summary(self, example_name: str) -> Optional[str]:
        example = self.get_example(example_name)
        return example.summary

    def get_example_description(self, example_name: str) -> Optional[str]:
        example = self.get_example(example_name)
        return example.description

    def get_examples(self, example_names: list[str]) -> dict[str, dict[str, Any]]:
        '''
        This gives us what we need for FastAPI::Body's `openapi_examples` field:
        a dictionary of OpenAPI example dictionaries.
        The example names are used as the keys, and the OpenAPI metadata
        dicts are the values.
        :return: A dictionary of rich OpenAPI examples.
        '''
        examples = {}
        for example_name in example_names:
            examples[example_name] = self.get_example(example_name).dict(exclude_unset=True)
        return examples
