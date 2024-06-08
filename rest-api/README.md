# Best Practices for Modern REST APIs in Python

Over the last few months I've been working on a REST API in modern Python for my startup, and would like to pass on what I've learned. I've built the REST APIs for two prior startups, one in Java making heavy use of reflection and one in Python, and bring that experience to bear here. 

I also focus on the use of modern Python. Python and the associated libraries have been going through some fairly radical changes over the last few years, so a lot of the docs and examples out in the world are either out of date or rather sketchy. Some of the topics I'll cover in this series of posts are:

* Using FastAPI, a feature-rich framework for building APIs written by Tiangolo (aka Sebastián Ramírez). It is based on Starlette, a fast but loer-level asynchronous REST API framework.
* SQLModel, an entity-class framework also by Tiangolo, which allows us to create classes that have rich functionality for both JSON serialization and persistence, and automatically checks for many kinds of client errors.
* Docs with Swagger and ReDoc. These doc frameworks use the same underlying OpenAPI schema and are built into FastAPI. I recommend some best practices to get things documented in a way that is maintainable and doesn't clutter the code.
* Implementing a safe and very flexible way of providing search functionality through a REST API, similar to e.g. Notion's flexible search mechanism.
* Both static and dynamic type-checking, with Pydantic, Ruff, and MyPy.
* Proper testing practices.

We'll use Python 3.11.5 for all of this, since it's the most up-to-date stable version.

## Contents

* [SQLModel Entity Classes](#sqlmodel-entity-classes)
  * [CRUD Classes](#crud-classes)
* [FastAPI](#fastapi)
  * [Defining Our Endpoints](#defining-our-endpoints)
* [A Flexible Search Language](#a-flexible-search-language)
  * [SearchModel Classes](#searchmodel-classes)
  * [An Expression Language](#an-expression-language)


## SQLModel Entity Classes

SQLAlchemy and Pydantic are very rich class frameworks for creating entity classes in your code, e.g. as a basis for `User`, `Group`, and `Employer` classes for managing your users. SQLAlchemy is focused on persistence in popular databases, while Pydantic is focused on three important capabilities: JSON serialization, runtime error checking, and exporting an OpenAPI JSON schema which powers our API documentation.

Until SQLModel came along, there was no framework that covered _both_ serialization and persistence: if you needed both sets of functionality, you would need to either build things from scratch, or maintain two sets of entity classes and keep them in sync, which is obviously painful. Fortunately for us, SQLModel brings together both Pydantic and SQLAlchemy. 

Obviously, mixing together two rich class frameworks is very tricky. SQLModel reaches deep into the bowels of these frameworks and wraps parts of the APIs, so it's not always obvious how to do certain things on the edges of the base functionality: e.g., do we use SQLModel functions for a certain task or do we need to drop down directly to either SQLAlchemy's or Pydantic's API? The guidelines here clear help to that up for you.

### CRUD Classes

In this tutorial we're going to create two different kinds of classes: those that represent the entities that our API acts on, and ones that are used for the rich search features we're going to build. In this section we cover the entity classes. It is a simplified version of some of the material in [the FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) with clarifications and (IMO) some improvements.

When we think about the general case of implementing CRUD (**C**reate, **R**ead, **U**pdate, **D**elete) operations in a REST API, we might need to expose different entity fields for different operations. In [the example in the FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/extra-models/) the use case for this is the `password` field for our User. We want to include the `password` field when we create and update a User, but not when we read them. To be clearly represent this, we'll create a separate class for each operation. 

Unlike the examples in the FastAPI tutorial, I think it's best to create a common base class to hold all the common fields. This is most important when we have many fields in our classes, but it's best to start out on the right foot by following [the DRY Principle](https://www.wikiwand.com/en/Don%27t_repeat_yourself) as much as possible: Don't Repeat Yourself (also known as Once and Only Once). When we define things in a single place we're less likely to introduce bugs as we modify and maintain the code. Of course, we need to balance this against introducing complexity to our class hierarchy.

There are some important things to note about how these classes connect to the database:

* One of our classes (`User`, in this case) will represent the entity in the database, and that fact is marked by the parameter `table=True`
* Our `id` column in that class has the `primary_key=True` annotation, which makes it a primary key in the database.
* We've marked out `email` field with `index=True` so that it is indexed in the database for very fast searching.
* We've set the `__table_args__ = (UniqueConstraint("email_primary"),)` variable in order to create a database constraint. This will help us by catching application errors that might try to insert Users with duplicate email addresses.

Note that we have defined `id` and `hashed_password` each in two places, in conflict with the DRY principal. We could do some refactoring to create additional parent or mixin classes to eliminate this, but given that these fields are special cases I think this is a cleaner, simpler solution than making the class heirarchy more complex. The main fields are still all collected in `UserBase`.

```
from typing import Optional, Final
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel
from sqlmodel import Field, select, Session

class UserBase(SQLModel):
    '''
    UserBase collects all the common fields shared by all the User-related classes.
    '''
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

class User(UserBase, table=True):
    '''
    This class is used by SQLAlchemy to represent the User entity in the database.
    '''
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: Optional[str] = None
    email: str = Field(index=True)

    __table_args__ = (UniqueConstraint("email"), )


class UserCreate(UserBase):
    '''
    This class is used by the Create operation of our API. Note that the database will
    auto-generate the `id` field internally, and will return a UserRead object when we
    create a new User.
    '''
    hashed_password: Optional[str] = None


class UserRead(UserBase):
    '''
    This class is used by the Read (and by extension, search) operations of our API.
    '''
    id: int  # note that this is not an Optional[int], because we must always read the database ID.


class UserUpdate(UserBase):
    '''
    NOTE: if we want to make `email` immutable we could make this class inherit from SQLModel and
    redefine the first_name and last_name fields here.
    '''
    pass

```

#### Linked Classes

Often, we want to link 

### Search Classes

SQLModel makes it easy to implement simple searches, e.g. to search by email address:

```
def get_user_by_email(session: Session, email: str) -> Optional[UserRead]:
    return session.exec(select(User).where(User.email == email)).first()
```

However, if we want to give a flexible way to search the idea method is to let them create arbitrary expressions with nested And and Or predicates. For example, we we might want to allow them to search for all users whose email address is 


## FastAPI

### Defining Our Endpoints

## A Flexible Search Language

### SearchModel Classes

### An Expression Language




