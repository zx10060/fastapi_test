"""
Puller from twitter
"""
import logging
from typing import Union
import functools
import snscrape.modules.twitter as sntwitter
from pymongo import InsertOne, UpdateOne, DeleteOne
from datetime import datetime
from app.config import with_settings
from app.connections import get_api
from app.database import cash_server, sync_client
from app.models import InternalError, Account, TaskFaled
from time import sleep

END_TIME = "2010-01-01"
# time limit 900 sec
TTL: int = 15 * 60

TWITTER_LIMITS = {
    "twitts": 300,
    "users": 300,
    "tasks": 150,
}

log = logging.getLogger(__name__)


def with_limits(function):
    """
    Decorator for count requests to Twitter API
    :param function:
    :return: function(*args, **kwargs)
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        """Decorator"""
        method = ""
        key = f"twitter:{method}"
        method_call_count = 0
        try:
            method_call_count = int(
                cash_server.ts().range(
                    key=key,
                    from_time="-",
                    to_time="+",
                    aggregation_type="sum",
                    bucket_size_msec=TTL * 10000,
                )[0][1]
            )
            print(method_call_count)
        except BaseException:
            pass

        if method_call_count > int(TWITTER_LIMITS.get(method) * 0.75):
            d_time = TTL / (TWITTER_LIMITS.get(method) - method_call_count)
            print("sleep ", d_time)
            sleep(d_time)
        cash_server.ts().add(key=key, timestamp="*", value=1)
        return function(*args, **kwargs)

    return wrapper


class TwitterPuller:
    """
    Class from pull data from twitter
    """

    @with_settings
    def __init__(self):
        self.api = get_api()
        self.storage = sync_client.twitter
        self.storage_data = sync_client.twitter_data

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
    def _get_users(self, usernames: list) -> list[Account, None]:
        users = []
        try:
            _users = self.api.lookup_users(screen_name=usernames)
            """
            [
                {
                 'contributors_enabled': False,
                 'created_at': 'Tue Jun 02 20:12:29 +0000 2009',
                 'default_profile': False,
                 'default_profile_image': False,
                 'description': '',
                 'entities': {'description': {'urls': []}},
                 'favourites_count': 16798,
                 'follow_request_sent': False,
                 'followers_count': 124887908,
                 'following': False,
                 'friends_count': 165,
                 'geo_enabled': False,
                 'has_extended_profile': True,
                 'id': 44196397,
                 'id_str': '44196397',
                 'is_translation_enabled': False,
                 'is_translator': False,
                 'lang': None,
                 'listed_count': 106952,
                 'location': '',
                 'name': 'Elon Musk',
                 'notifications': False,
                 'profile_background_color': 'C0DEED',
                 'profile_background_image_url': 'http://abs.twimg.com/images/themes/theme1/bg.png',
                 'profile_background_image_url_https': 'https://abs.twimg.com/images/themes/theme1/bg.png',
                 'profile_background_tile': False,
                 'profile_banner_url': 'https://pbs.twimg.com/profile_banners/44196397/1576183471',
                 'profile_image_url': 'http://pbs.twimg.com/profile_images/1590968738358079488/IY9Gx6Ok_normal.jpg',
                 'profile_image_url_https': 'https://pbs.twimg.com/profile_images/1590968738358079488/IY9Gx6Ok_normal.jpg',
                 'profile_link_color': '0084B4',
                 'profile_location': None,
                 'profile_sidebar_border_color': 'C0DEED',
                 'profile_sidebar_fill_color': 'DDEEF6',
                 'profile_text_color': '333333',
                 'profile_use_background_image': True,
                 'protected': False,
                 'screen_name': 'elonmusk',
                 'status': {'contributors': None,
                            'coordinates': None,
                            'created_at': 'Sun Jan 08 01:05:44 +0000 2023',
                            'entities': {'hashtags': [],
                                         'symbols': [],
                                         'urls': [],
                                         'user_mentions': [{'id': 14710129,
                                                            'id_str': '14710129',
                                                            'indices': [0, 15],
                                                            'name': 'Peter H. Diamandis, MD',
                                                            'screen_name': 'PeterDiamandis'}]},
                            'favorite_count': 2907,
                            'favorited': False,
                            'geo': None,
                            'id': 1611891871512514560,
                            'id_str': '1611891871512514560',
                            'in_reply_to_screen_name': 'PeterDiamandis',
                            'in_reply_to_status_id': 1611867056768532481,
                            'in_reply_to_status_id_str': '1611867056768532481',
                            'in_reply_to_user_id': 14710129,
                            'in_reply_to_user_id_str': '14710129',
                            'is_quote_status': False,
                            'lang': 'en',
                            'place': None,
                            'retweet_count': 185,
                            'retweeted': False,
                            'source': '<a href="http://twitter.com/download/iphone" '
                                      'rel="nofollow">Twitter for iPhone</a>',
                            'text': '@PeterDiamandis Risky Business (great movie)',
                            'truncated': False},
                 'statuses_count': 21995,
                 'time_zone': None,
                 'translator_type': 'none',
                 'url': None,
                 'utc_offset': None,
                 'verified': True,
                 'withheld_in_countries': []
                },
            ]
            """
            for _user in _users:
                users.append(
                    Account.construct(
                        twitter_id=_user.id,
                        name=_user.name,
                        username=_user.screen_name,
                        following_count=_user.favourites_count,
                        followers_count=_user.followers_count,
                        description=_user.description,
                        twitts_count=_user.statuses_count,
                        status="new",
                    )
                )
        except BaseException:
            log.error("Error of lookup users in twitter!")
        return users

    def _scrapp_users(self, usernames: list) -> list[Account, None]:
        """
        Scrapp users from twitter.
        :param usernames:
        :return:
        """
        new_users_data = []
        try:
            from snscrape.modules.twitter import TwitterUserScraper

            for user_name in usernames:
                # TODO add proxy to env or other file or endpoint
                # _data = TwitterUserScraper(user=user_name, proxies={}).get_items()
                _data = TwitterUserScraper(user=user_name).get_items()
                _user = _data.gi_frame.f_locals["self"].entity
                """
                User(
                    username = 'elonmusk',
                    id = 44196397,
                    displayname = 'Elon Musk',
                    rawDescription = '',
                    renderedDescription = '',
                    descriptionLinks = [],
                    verified = True,
                    created = datetime.datetime(2009, 6, 2, 20, 12, 29, tzinfo = datetime.timezone.utc),
                    followersCount = 129994028,
                    friendsCount = 181,
                    statusesCount = 23224,
                    favouritesCount = 18901,
                    listedCount = 115282,
                    mediaCount = 1424,
                    location = '',
                    protected = False,
                    link = None,
                    profileImageUrl = 'https://pbs.twimg.com/profile_images/1590968738358079488/IY9Gx6Ok_normal.jpg',
                    profileBannerUrl = 'https://pbs.twimg.com/profile_banners/44196397/1576183471',
                    label = None
                    )
                """
                new_users_data.append(
                    Account.construct(
                        twitter_id=_user.id,
                        name=_user.displayname,
                        username=_user.username,
                        following_count=_user.favouritesCount,
                        followers_count=_user.followersCount,
                        description=_user.rawDescription,
                        twitts_count=_user.statusesCount,
                        status="new",
                    )
                )
        except BaseException:
            log.error("Bad response from twitter, scrapper not working..")

        return new_users_data

    def get_users_data(self, usernames: list) -> None:
        """
        Get users data from twitter
        :param usernames: list
        :return:
        """
        if self.api:
            users = self._get_users(usernames)
        else:
            users = self._scrapp_users(usernames)

        if not users:
            raise InternalError

        query = {"username": {"$in": usernames}}
        params = {"username": 1, "twitts_count": 1}
        accounts = self.storage.accounts.find(query, params)
        accounts_exist = {
            account["usename"]: account["twitts_count"] for account in accounts
        }

        users_for_pull_data = []
        query = []
        for user in users:
            if accounts_exist.get(user.username):
                _filter = {"username": user.username}
                query.append(UpdateOne(_filter, {"$set": user.dict()}))
                if user.twitts_count != accounts_exist.get(user.username):
                    users_for_pull_data.append(user.id)
            else:
                InsertOne(user.dict())
                users_for_pull_data.append(user.id)

        if query:
            self.storage.accounts.bulk_write(query)

        if users_for_pull_data:
            from celery_twitter import start_pull_from_twitter

            for user in users:
                start_pull_from_twitter.delay(user.id)

    @with_limits
    def _get_twitts_by_id(self, ids: list) -> list:
        """
        Return up to 100 twitt objs by IDs.
        https://docs.tweepy.org/en/latest/api.html#tweepy.API.lookup_statuses
        :param ids: list
        :return:
        """
        statuses = []
        try:
            statuses = self.api.lookup_statuses(ids)
        except BaseException:
            log.error("Error lookup statuses")
        return statuses

    @with_limits
    def _get_twitts(self, user_id: int, since_id: int = None) -> list:
        """
        Return 20 twitts by user id.
        :param user_id:
        :param since_id:
        :return:
        """
        try:
            result = self.api.user_timeline(user_id=user_id, since_id=since_id)
            if result:
                return result
            else:
                return []
        except BaseException:
            log.error("Get user timeline error!")

    def _remove_twitts_repits(
        self,
        user_id: Union[str, int],
        twitts: list,
    ) -> None:
        """
        Remove dublicate twitts from DB.
        :rtype: object
        :param user_id:
        :param twitts:
        """

        def _write(_data):
            self.storage_data[f"{user_id}"].bulk_write(_data, ordered=False)

        seen = set()
        must_delete = []
        for twitt in twitts:
            if twitt in seen:
                must_delete.append(DeleteOne({"_id": twitt.id}))
                if len(must_delete) == 500:
                    _write(must_delete)
                    must_delete.clear()
            else:
                seen.add(twitt)
        _write(must_delete)

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
            log.info("New data")
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
        try:
            if not start_time:
                start_time = datetime.today().strftime("%Y-%m-%d")
            account = self._get_user_by_name(username)
            twitts_id_set = self._get_twitts_by_user_id(account.twitter_id)

            if account.twitts_count == len(twitts_id_set):
                # If all twitts updated exit from task
                if account.status != "updated":
                    account.status = "updated"
                    _filter = {"_id": account.username}
                    self.storage.UpdateOne(_filter, {"$set": account.dict()})
                return True

            query = f"(from:{username}) until:{start_time} since:{end_time}"
            new_twitts = []
            butch_count = 500
            for twitt in sntwitter.TwitterSearchScraper(query).get_items():
                if twitt.id not in twitts_id_set:
                    new_twitts.append(InsertOne(twitt.json()))
                    twitts_id_set.add(twitt.id)
                if len(new_twitts) == butch_count:
                    collection = f"{account.twitter_id}"
                    self.storage_data[collection].bulk_write(new_twitts)
                    new_twitts.clear()
        except BaseException:
            raise TaskFaled
