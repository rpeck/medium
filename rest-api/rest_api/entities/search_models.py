from abc import ABC, abstractmethod
from typing import Optional, Union, TypeAlias, Any, Type
from pydantic import BaseModel, Field, model_validator, parse_obj_as, root_validator

from sqlmodel import or_, and_, not_
from sqlmodel.sql.expression import BinaryExpression, ColumnElement

from sqlalchemy.sql.elements import ClauseElement
from rest_api.helpers.introspection import has_field, get_field, get_all_subclasses

# get these into globals(); DO NOT REMOVE!
from rest_api.entities.users import User  # noqa
from rest_api.entities.companies import Company  # noqa

def abstract_class(cls):
    '''
    Custom decorator that declares that a class is abstract, and prevents it from being instantiated directly.
    '''
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        if type(self) is cls:
            raise NotImplementedError(f'{cls.__name__} is an abstract base class and cannot be instantiated directly')
        original_init(self, *args, **kwargs)

    cls.__init__ = new_init
    return cls

@abstract_class
class BaseSearchModel(BaseModel, ABC):
    '''
    Base class for all of our search models. These follow the Discriminated Union
    pattern, which enables Pydantic to determine which model class it's deserializing if
    we have multiple models with the same fields, like our multi-child operators do.

    See: https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions

    We declare this as an Abstract Base Class because we don't want to instantiate it.
    '''
    type: str = Field(..., alias='type')
    "We use the `type` field to discriminate between payloads for different classes during deserialization. For example, it must be set to `Not` for a `NotSearchModel`."

    class Config:
        use_attribute_docstrings=True
        extra = "forbid"  # raise a ValidationError if we see unknown fields
        validate_assignment = True  # validate the model at runtime when the model is changed

        # NOTE: we're not using the `discriminator` property because it doesn't work with
        # parse_obj_as(). Instead, we use a model_validator called `discriminator()`.
        #
        # discriminator = "type"  # use the type field to discriminate when deserializing

    @model_validator(mode="before")
    @classmethod
    def discriminator(cls, values: dict[str, Any]) -> dict[str, Any]:
        '''
        This validator is used to discriminate between our classes during polymorphic deserialization.
        It does that by failing validation if the value of the `type` field doesn't match the class name.
        This is how parse_obj_as(SearchModel, d) is able to create and return the correct class's instance.
        '''
        if not has_field(values, "type") or get_field(values, "type") is None:
            raise ValueError("'type' must be set for all SearchModel instances")

        t: str = get_field(values, "type")
        if cls.__name__ != f"{t}SearchModel":
            raise ValueError(f"type was set to {t} for class: {cls.__name__}")
        return values

    @abstractmethod
    def render_condition(self) -> ClauseElement:
        pass

@abstract_class
class EntitySearchModel(BaseSearchModel):
    '''
    The base class for all of our entity search models.
    '''
    pass

    def render_condition(self) -> ColumnElement:
        """
        Create a SQLAlchemy ClauseElement object by combining the equality checks for each field of the instance.
        """

        # Generate a list of SQLAlchemy BinaryExpression instances, representing conditions
        # for the SQL WHERE clause

        # First, substitute the SearchModel class name with the SQLModel class name
        # (e.g., UserSearchModel -> User)
        model_class_name = self.__class__.__name__.replace("SearchModel", "")

        # Get the actual model class; note that it has to be imported in this file to be available in globals()!
        model_class = globals()[model_class_name]

        # Create a list of binary expressions in SQLAlchemy to represent our conditions.
        #
        # For each annotated field in the current class, check if it is called not "type" and its corresponding
        # attribute on `self` is not None.
        #
        # If both checks pass, create a BinaryExpression comparing the attribute of the same name on our `model_class`
        # to the attribute's value in `self`.
        #
        # It's a bit subtle how the `==` bit works:
        # * The getattr(model_class, field) expression retrieves the Column object for the model class.
        # * This object is an instance of Column that represents the column in the database table for the `field`.
        # * The returned Column class overloads standard Python operators such as `==`.
        # * The overloaded `==` returns a BinaryExpression object that represents the equality comparison in the AST.
        conditions: list[BinaryExpression] = [
            getattr(model_class, field) == value
            for field in self.__class__.__annotations__
            if field != "type" and (value := getattr(self, field)) is not None
        ]

        # NOTE: `and_` will do the right thing when there are no conditions or only one condition.
        # If there are no conditions it will return something that evaluates to True; if there is
        # one condition it will return the child.
        return and_(*conditions)

@abstract_class
class OperatorSearchModel(BaseSearchModel, ABC):
    '''
    The base class for all of our operators, such as And, Or, and Not.
    '''
    pass

@abstract_class
class UnaryOperatorSearchModel(OperatorSearchModel, ABC):
    '''
    The base class for all of our unary operators (currently only Not).
    '''
    child: "SearchModel"
    "the argument for this operator to act upon"

@abstract_class
class NaryOperatorSearchModel(OperatorSearchModel, ABC):
    '''
    The base class for all of our operators that take 2..N parameters.
    '''
    children: list["SearchModel"] = Field(..., alias='children')
    "the list of arguments for this operator to act upon"

class NotSearchModel(UnaryOperatorSearchModel):
    type: str = "Not"
    "field that tells us what type of entity this dictionary is"

    def render_condition(self) -> ColumnElement:
        """
        Render a UnaryExpression object by transforming a NOT clause's child's conditions.
        """
        not_condition = self.child.render_condition()
        return not_(not_condition)

class OrSearchModel(NaryOperatorSearchModel):
    type: str = "Or"
    "field that tells us what type of entity this dictionary is"

    def render_condition(self) -> ColumnElement:
        """
        Render a BooleanClauseList object by recursively traversing the AST and ORing the child conditions.
        """

        # NOTE: `or_` will do the right thing when there are no conditions or only one condition.
        # If there are no conditions it will return something that evaluates to False; if there is
        # one condition it will return the child.
        or_conditions = [child.render_condition() for child in self.children]
        return or_(*or_conditions)

class AndSearchModel(NaryOperatorSearchModel):
    type: str = "And"
    "field that tells us what type of entity this dictionary is"

    def render_condition(self) -> ColumnElement:
        """
        Render a BooleanClauseList object by recursively traversing the AST and ANDing the child conditions.
        """
        # NOTE: `and_` will do the right thing when there are no conditions or only one condition.
        # If there are no conditions it will return something that evaluates to True; if there is
        # one condition it will return the child.
        conditions = [child.render_condition() for child in getattr(self, 'children', [])]
        return and_(*conditions)

class UserSearchModel(EntitySearchModel):
    type: str = "User"
    "field that tells us what type of entity this dictionary is"

    id: Optional[int] = None
    "unique identifier for this user"

    first_name: Optional[str] = None
    "first name of the user, e.g. John"

    last_name: Optional[str] = None
    "last name of the user, e.g. Doe"

    email: Optional[str] = None
    "email address of the user, e.g. john.doe@acompany.com"

    company_id: Optional[int] = None
    "id of the user's Company"

class CompanySearchModel(EntitySearchModel):
    type: str = "Company"
    "field that tells us what type of entity this dictionary is"

    id: Optional[int] = None
    "unique identifier for this company"

    name: Optional[str] = None
    "canonical name of this company"

# Note: when deserializing to a SearchModel using parse_obj_as, Pydantic walks through
# this list of classes in order.
SearchModel: TypeAlias = Union[
    NotSearchModel, OrSearchModel, AndSearchModel,
    UserSearchModel, CompanySearchModel
]

entity_classes = get_all_subclasses(EntitySearchModel)
entity_types = [ cls.__name__.replace("SearchModel", "") for cls in entity_classes ]

def entity_class_for_tree(tree: SearchModel) -> Type[SearchModel]:
    '''
    Return the entity class that's found in the search tree. This is used for determining which
    table to operate on (e.g., to search).

    NOTE: We don't yet support subqueries or joins! When we do, the use of this needs to be updated.
    :param tree: Any valid SearchModel instance or tree
    :return: The entity class that's found in the search tree.
    '''
    if isinstance(tree, EntitySearchModel):
        return globals()[tree.type]
    elif isinstance(tree, UnaryOperatorSearchModel):
        return entity_class_for_tree(tree.child)
    else:
        # each child should have at least one EntitySearchModel!
        return entity_class_for_tree(tree.children[0])

def entities_for_search_model(data: dict) -> list[EntitySearchModel]:
    instances = []

    if not isinstance(data, dict):
        raise ValueError('data must be a dictionary')

    # TODO: don't hardwire these types; dynamically find the subclasses of EntitySearchModel
    if 'type' in data and data['type'] in entity_types:
        entity = parse_obj_as(SearchModel, data)
        instances.append(entity)

    for key, value in data.items():
        if key == "child":
            instances.extend(entities_for_search_model(value))
        elif key == "children":
            for child in value:
                if not isinstance(child, dict):
                    raise ValueError("expected only dicts as children")

                instances.extend(entities_for_search_model(child))
    return instances
