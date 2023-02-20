"""
Puller from twitter
"""
import logging
from typing import Union, Any
import functools
import snscrape.modules.twitter as sntwitter
from pymongo import InsertOne, UpdateOne, DeleteOne
from datetime import datetime
from app.config import with_settings
from app.database import cash_server, sync_client
import tweepy
from app.models import InternalError

END_TIME = "2010-01-01"
# time limit 900 sec
TTL: int = 15 * 60

TWITTER_LIMITS = {
    "twitts": 300,
    "users": 300,
    "tasks": 150,
}


def with_limits(function):
    """
    Decorator for count requests to Twitter API
    :param function:
    :return: function(*args, **kwargs)
    """

    @functools.wraps
    def wrapper(*args, **kwargs):
        function(*args, **kwargs)

    return wrapper


class TwitterPuller:
    """
    Class from pull data from twitter
    """

    @with_settings
    def __init__(self, settings=None):
        auth = tweepy.OAuthHandler(settings.API_KEY, settings.API_SECRET_KEY)
        auth.set_access_token(
            settings.API_ACCESS_TOKEN, settings.API_ACCESS_TOKEN_SECRET
        )
        self.api = tweepy.API(auth, wait_on_rate_limit=True)
        self.storage = sync_client.twitter
        self.storage_data = sync_client.twitter_data
        # create time sirieses for count calls to twitter
        # try:
        #     for method, _ in twitter_limits.items():
        #         cash_server.ts().create(
        #             key = f"twitter:{method}",
        #             retention_msecs = TTL * 1000,
        #             duplicate_policy = 'SUM'
        #         )
        # except:
        #     pass

    # def _get(self, method: str):
    #     """
    #     Get from twitter.
    #     :param method:
    #     :return:
    #     """
    #     key = f"twitter:{method}"
    #     method_call_count = 0
    #     try:
    #         method_call_count = int(
    #             cash_server.ts().range(
    #                 key = key,
    #                 from_time = "-",
    #                 to_time = "+",
    #                 aggregation_type = 'sum',
    #                 bucket_size_msec = TTL * 10000
    #             )[0][1]
    #             )
    #         print(method_call_count)
    #     except:
    #         pass
    #
    #     if method_call_count > int(twitter_limits.get(method) * 0.75):
    #         d_time = TTL / (twitter_limits.get(method) - method_call_count)
    #         print("sleep ", d_time)
    #         time.sleep(d_time)
    #     cash_server.ts().add(key = key, timestamp = "*", value = 1)
    #     # TODO async call to twitter
    #     # await method(*args, **kwargs)

    def _get_user_by_name(self, username: str):
        """

        :param username:
        :return:
        """
        query = {"username": {"$eq": username}}
        return self.storage.accounts.find(query)

    def get_user_by_id(self, user_id: Union[str, int]):  # -> Account:
        """
        Return user data by id from Mongo.
        :param user_id:
        :return:
        """
        query = {"id_str": {"$eq": user_id}}
        return self.storage.accounts.find(query)

    @with_limits
    def _get_users(self, usernames: list) -> list:
        return self.api.lookup_users(screen_name=usernames)

    def get_users_data(self, usernames: list):
        """
        Get users data from twitter
        :param usernames: list
        :return:
        """
        users = self._get_users(usernames)
        if not users:
            raise InternalError
        query = {"username": {"$in": usernames}}
        accounts = self.storage.accounts.find(query, {"username": 1, "twitts_count": 1})
        accounts_exist = {
            account["usename"]: account["twitts_count"] for account in accounts
        }

        def _filer_fields(_user):
            """
            filer_fields
            :param _user:
            :return:
            """
            return {
                "twitter_id": _user.id,
                "name": _user.name,
                "username": _user.screen_name,
                "following_count": _user.followers_count,
                "followers_count": _user.description,
                "description": _user.description,
                "twitts_count": _user.statuses_count,
                "status": "started",
            }

        def _update_fields(_user):
            return {"$set": _filer_fields(_user)}

        users_for_pull_data = []
        query = []
        for user in users:
            if accounts_exist.get(user.screen_name):
                _filter = {"username": user.screen_name}
                query.append(UpdateOne(_filter, _update_fields(user)))
                if user.statuses_count != accounts_exist.get(user.screen_name):
                    users_for_pull_data.append(user.id)
            else:
                InsertOne(_filer_fields(user))
                users_for_pull_data.append(user.id)

        if query:
            self.storage.accounts.bulk_write(query)

        if users_for_pull_data:
            from celery_twitter import start_pull_from_twitter

            for user in users:
                start_pull_from_twitter.delay(user.id)

    @with_limits
    def _get_twitts_by_id(self, ids: list) -> Any:
        """
        Return up to 100 twitt objs by IDs.
        https://docs.tweepy.org/en/latest/api.html#tweepy.API.lookup_statuses
        :param ids: list
        :return:
        """
        # TODO will be try
        return self.api.lookup_statuses(ids)

    @with_limits
    def _get_twitts(self, user_id: int, since_id: int = None) -> Any:
        """
        Return 20 twitts by user id.
        :param user_id:
        :param since_id:
        :return:
        """
        # TODO will be try
        return self.api.user_timeline(user_id=user_id, since_id=since_id)

    def _remove_twitts_repits(self, user_id: Union[str, int], twitts: list) -> None:
        """
        Remove dublicate twitts from DB.
        :rtype: object
        :param user_id:
        :param twitts:
        """
        seen = set()
        must_delete = []
        for twitt in twitts:
            if twitt in seen:
                must_delete.append(DeleteOne({"_id": twitt.id}))
                if len(must_delete) == 500:
                    self.storage_data[f"{user_id}"].bulk_write(
                        must_delete, ordered=False
                    )
                    must_delete.clear()
            else:
                seen.add(twitt)

        self.storage_data[f"{user_id}"].bulk_write(must_delete, ordered=False)

    def _get_twitts_by_user_id(self, user_id: Union[str, int]) -> set:
        """
        Get twitts from Mongo DB by user_id
        :param user_id:
        :return:
        """
        collection_exists = self.storage_data.validate_collection(f"{user_id}")
        _result = set()
        twitts = []
        if collection_exists:
            twitts = self.storage_data[f"{user_id}"].find()
            if len(twitts):
                _result = {twitt_id["id_str"] for twitt_id in twitts}

        if len(twitts) != len(_result):
            self._remove_twitts_repits(user_id, twitts)
        return _result

    def pull_data(self, user_id: int) -> None:
        """
        Download all user twitts.
        :param user_id:
        """
        result = self._get_twitts(user_id)
        twitts_ids = self._get_twitts_by_user_id(user_id)

        if not twitts_ids:
            logging.info("New data")
            data = [InsertOne(twitt._json) for twitt in result]
        else:
            data = [
                InsertOne(twitt._json)
                for twitt in result
                if twitt.id_str not in twitts_ids
            ]

        if data:
            self.storage_data[f"{user_id}"].bulk_write(data)

        from celery_twitter import add_scrapper_task

        add_scrapper_task.delay(self.get_user_by_id(user_id))

    def scrap_user_data(
        self, username: str, start_time: str = "", end_time: str = END_TIME
    ):
        """
        Run scraper for twitter by username(scenename) in twitter.
        :param username:
        :param start_time:
        :param end_time:
        :return:
        """
        if not start_time:
            start_time = datetime.today().strftime("%Y-%m-%d")
        account = self._get_user_by_name(username)
        twitts_id_set = self._get_twitts_by_user_id(account.twitter_id)

        if account.twitts_count == len(twitts_id_set):
            # If all twitts updated exit from task
            return True

        query = f"(from:{username}) until:{start_time} since:{end_time}"
        new_twitts = []
        butch_count = 500
        for twitt in sntwitter.TwitterSearchScraper(query).get_items():
            if twitt.id not in twitts_id_set:
                new_twitts.append(InsertOne(twitt.json()))
                twitts_id_set.add(twitt.id)
            if len(new_twitts) == butch_count:
                self.storage_data[f"{account.twitter_id}"].bulk_write(new_twitts)
                new_twitts.clear()
