"""
Models for API
"""
from typing import List

from bson import ObjectId
from pydantic import BaseModel, Field
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
        """
        Validate ObjID
        :param v:
        :return:
        """
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
        """
        Config for model.
        Decorator doesnt work...
        """

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
    twitts_count: int = Field(...)
    status: str = Field(..., default="started")

    class Collection:
        """
        Create index for username field in collection Accounts
        """

        name = "usernames"
        indexes = [
            [
                # TEXT indexes
                ("username", pymongo.TEXT),
            ],
        ]

    class Config:
        """
        Config for model.
        @decorator doesnt work...
        """

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


class TaskFaled(BaseException):
    """
    Class for task fails
    """
