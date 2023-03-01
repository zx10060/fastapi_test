"""
File for connection to Mongo and REDIS
"""
import logging

import motor.motor_asyncio
import redis
from pymongo import MongoClient
from app.config import get_settings

log = logging.getLogger()

_config = get_settings()

_mongo_host = _config.MONGO_HOST if _config.MONGO_HOST else "localhost"
_mongo_port = _config.MONGO_PORT if _config.MONGO_PORT else 27017

async_client = motor.motor_asyncio.AsyncIOMotorClient(_mongo_host, _mongo_port)
a_db = async_client.twitter
a_db_data = async_client.twitter_data

sync_client = MongoClient(host=_mongo_host, port=_mongo_port)
s_db_data = sync_client.twitter_data


def _create_ts_for_limist(_connection):
    # create time sirieses for count calls to twitter
    try:
        from app.puller import TWITTER_LIMITS, TTL

        for method in TWITTER_LIMITS.keys():
            _connection.ts().create(
                key=f"twitter:{method}",
                retention_msecs=TTL * 1000,
                duplicate_policy="SUM",
            )
    except BaseException:
        log.error("Redis not available!")


_redis_host = _config.MONGO_HOST if _config.MONGO_HOST else "localhost"
_redis_port = _config.REDIS_HOST if _config.REDIS_PORT else 6379
_pool = redis.ConnectionPool(host=_redis_host, port=_redis_port, db=0)
cash_server = redis.Redis(connection_pool=_pool)
_create_ts_for_limist(cash_server)
