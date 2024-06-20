from typing import Optional, Final
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel
from sqlmodel import Field, select, Session
from pydantic import ConfigDict

class UserBase(SQLModel):
    '''
    UserBase collects all the common fields shared by all the User-related classes.
    '''
    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid", validate_assignment=True)

    first_name: Optional[str] = None
    "first name of the user, e.g. John"
    
    last_name: Optional[str] = None
    "last name of the user, e.g. Doe"
    
    email: Optional[str] = None
    "email address of the user, e.g. john.doe@acompany.com; must be unique"
    
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True)
    "id of the user's Company"
    

# Doc using Field:
# class UserBase(SQLModel):
#     '''
#     UserBase collects all the common fields shared by all the User-related classes.
#     '''
#     first_name: Optional[str] = Field(default=None,
#                                       description="first name of the user, e.g. John")
#     last_name: Optional[str] = Field(default=None,
#                                       description="last name of the user, e.g. Doe")
#     email: Optional[str] = Field(default=None,
#                                       description="email address of the user, e.g. john.doe@acompany.com")
#     company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True,
#                                       description="id of the user's Company")


class User(UserBase, table=True):
    '''
    This class is used by SQLAlchemy to represent the User entity in the database.
    '''
    __tablename__ = "users"
    "override the automatic table name, which is `user`"
    __table_args__ = (UniqueConstraint("email"), )

    id: Optional[int] = Field(default=None, primary_key=True)
    "unique identifier for this user"

    hashed_password: Optional[str] = None
    "the user's password, salted and hashed for security"

    email: str = Field(index=True)
    "email address of the user, e.g. john.doe@acompany.com; must be unique"


class UserCreate(UserBase):
    '''
    This class is used by the Create operation of our API. Note that the database will
    auto-generate the `id` field internally, and will return a UserRead object when we
    create a new User.
    '''
    password: str
    "cleartext password for this user; required"

class UserRead(UserBase):
    '''
    This class is used by the Read (and by extension, search) operations of our API.
    '''
    id: int  # note that this is not an Optional[int], because we must always read the database ID.
    "unique identifier for this user"


class UserUpdate(UserBase):
    '''
    This class is used by the PUT and PATCH operations of our API. Note that we can modify the
    `password` field, and this gets hashed by the back end and stored in the `hashed_password`
    field in the database.
    '''
    # NOTE: if we want to make `email` immutable we could make this class inherit from SQLModel and
    # redefine the first_name and last_name fields here.
    password: Optional[str] = None
    "cleartext password for this user"

def get_user_by_email(session: Session, email: str) -> Optional[UserRead]:
    '''
    Find user that matches the given email string, or None.
    Note that email addresses are unique.
    '''
    return session.exec(select(User).where(User.email == email)).first()  # noqa
