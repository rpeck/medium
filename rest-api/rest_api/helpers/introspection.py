from typing import Any, Type
def has_field(obj: Any, field: str) -> bool:
    """
    Check if a field exists in a given object (which could be a dictionary or a regular Python object).

    :param obj: The object where the field will be checked.
    :param field: The field name to check.
    :return: True if the field exists, False otherwise.
    """
    if isinstance(obj, dict):
        return field in obj
    else:
        return hasattr(obj, field)


def get_field(obj: Any, field: str) -> Any:
    """
    Get the value of a field from a given object (which could be a dictionary or a regular Python object).
    Raises KeyError if the field doesn't exist in the dictionary, or AttributeError if the field doesn't exist in the object.

    :param obj: The object where the field will be retrieved.
    :param field: The field name to retrieve.
    :return: The field's value if it exists.
    :raises: KeyError if the field doesn't exist in the dictionary, AttributeError if the field doesn't exist in the object.
    """
    if isinstance(obj, dict):
        if field in obj:
            return obj.get(field)
        else:
            raise KeyError(f"Field '{field}' does not exist in the dictionary.")
    else:
        if hasattr(obj, field):
            return getattr(obj, field)
        else:
            raise AttributeError(f"Field '{field}' does not exist in the object {type(obj).__name__}.")


def set_field(obj: Any, field: str, value: Any) -> Any:
    """
    Set the value of a field in a given object (which could be a dictionary or a regular Python object).
    Returns the old value of the field if it existed.

    :param obj: The object where the field will be updated.
    :param field: The field name to update.
    :param value: The new value for the field.
    :return: The old value of the field if it existed, None otherwise.
    """
    old_value = None
    if isinstance(obj, dict):
        old_value = obj.get(field)
        obj[field] = value
    else:
        if hasattr(obj, field):
            old_value = getattr(obj, field)
        setattr(obj, field, value)

    return old_value

def get_all_subclasses(cls: Type[Any]) -> list[Type[Any]]:
    all_subclasses = []

    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses
