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
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id")

class User(UserBase, table=True):
    '''
    This class is used by SQLAlchemy to represent the User entity in the database.
    '''
    __tablename__ = "users"  # override the automatic table name, which is `user`
    __table_args__ = (UniqueConstraint("email"), )

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: Optional[str] = None
    email: str = Field(index=True)



class UserCreate(UserBase):
    '''
    This class is used by the Create operation of our API. Note that the database will
    auto-generate the `id` field internally, and will return a UserRead object when we
    create a new User.
    '''
    password: Optional[str] = None


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
    password: Optional[str] = None

def get_user_by_email(session: Session, email: str) -> Optional[UserRead]:
    return session.exec(select(User).where(User.email == email)).first()  # noqa

test_user_1: Final[User] = User(email="rpeck@rpeck.com", first_name="Raymond", last_name="Peck", company_id=1)
