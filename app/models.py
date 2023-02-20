"""
Models for API
"""
from typing import List

from bson import ObjectId
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass
import pymongo


class PyObjectId(ObjectId):
    """
    Class for id in Mongo
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")





class SyncTask(BaseModel):
    """
    Class for task sync from twitter
    """

    session_id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    users_list: set[str] = Field(...)

    class Config:
        allow_population_by_field_name = False
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AccountStatus(BaseModel):
    """
    Model for twitter Account status.
    """

    username: str
    status: str


class Account(BaseModel):
    """
    Class for Users of twitter
    """

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    twitter_id: str = Field(...)
    name: str = Field(...)
    username: str = Field(...)
    following_count: int = Field(...)
    followers_count: int = Field(...)
    description: str = Field(...)
    status: str = Field(...)

    class Collection:
        name = "usernames"
        indexes = [
            [
                # TEXT indexes
                ("username", pymongo.TEXT),
            ],
        ]

    class Config:
        allow_population_by_field_name = False
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class InternalError(BaseException):
    """
    Class for internal errors.
    """

    pass


class Session(BaseModel):
    """
    Class for session id
    """

    session_id: str


class ProfilesList(BaseModel):
    """
    Class for list of profiles in twitter
    """

    profiles: List[str]
