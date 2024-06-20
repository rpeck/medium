from typing import Optional, Final
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel
from sqlmodel import Field, select, Session
from pydantic import ConfigDict

class CompanyBase(SQLModel):
    '''
    CompanyBase collects all the common fields shared by all the Company-related classes.
    '''
    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid", validate_assignment=True)

    name: Optional[str] = None  # leave this Optional so we don't need to reset it with PATCH
    address: Optional[str] = None


class Company(CompanyBase, table=True):
    '''
    This class is used by SQLAlchemy to represent the Company entity in the database.
    '''
    __tablename__ = "companies"  # override the automatic table name, which is `company`
    __table_args__ = (UniqueConstraint("name"), )

    id: Optional[int] = Field(default=None, primary_key=True)



class CompanyCreate(CompanyBase):
    '''
    This class is used by the Create operation of our API. Note that the database will
    auto-generate the `id` field internally, and will return a CompanyRead object when we
    create a new Company.
    '''
    name: str  # required!


class CompanyRead(CompanyBase):
    '''
    This class is used by the Read (and by extension, search) operations of our API.
    '''
    id: int


class CompanyUpdate(CompanyBase):
    '''
    NOTE: if we want to make `name` immutable we could make this class inherit from SQLModel and
    redefine the address field here.
    '''
    pass
