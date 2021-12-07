import asyncio
import json
import logging
import re
import urllib.parse
from base64 import b64encode
from http.cookiejar import MozillaCookieJar
from typing import Optional

import aiohttp

from .websocket.pubsub import Pubsub

from .channel import Channel
from .gql import operations, hashes

log = logging.getLogger(__name__)


class Account:
    def __init__(
        self,
        cookie_file: str = None,
        default_headers: Optional[dict] = None
    ):
        self._cookie_jar = {}
        self._default_headers = default_headers

        self._websocket: Optional[Pubsub] = None

        if cookie_file:
            cookie_jar = MozillaCookieJar()
            cookie_jar.load(cookie_file)

            for cookie in cookie_jar:
                self._cookie_jar[cookie.name] = cookie.value

        self._spade_url: Optional[str] = None
        
        self.username: Optional[str] = None
        self.authorization_token: Optional[str] = None

        self.unique_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.client_id: Optional[str] = None

    @property
    def session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            headers=self._default_headers,
            cookies=self._cookie_jar
        )
    
    async def fetch_twitch_gql(
        self,
        query_or_hash: str,
        variables: Optional[dict] = None,
        is_persisted: bool = False
    ) -> dict:
        """ Perform a GraphQL request on Twitch's API. """
        data = {}

        if is_persisted:
            data.update({
                "operationName": query_or_hash,
                "extensions": {
                    "persistedQuery": {
                        "sha256Hash": hashes[query_or_hash],
                        "version": 1
                    }
                }
            })
        else:
            data["query"] = query_or_hash

        if variables:
            data["variables"] = variables

        headers = {
            "Authorization": f"OAuth {self.authorization_token}",
            "Client-ID": self.client_id,
        }

        async with self.session as session:
            async with session.post("https://gql.twitch.tv/gql", json=[data], headers=headers, raise_for_status=True) as resp:
                return (await resp.json())[0]["data"]
    
    async def fetch_client_id(self) -> Optional[str]:
        """
        Find the current client ID from the Twitch home page. Cookies must be
        set before this can be called.
        """
        async with self.session as session:
            async with session.get("https://www.twitch.tv/", raise_for_status=True) as resp:
                text = await resp.text()

        search = re.search(r"\"Client-ID\":\"(.*?)\"", text)

        # TODO: More stable way to get client ID.
        if not search:
            search = re.search(r"clientId=\"(.*?)\"", text)

            if not search:
                return None

        return search.group(1)
    
    async def fetch_channel(self, channel_name: str) -> Optional[dict]:
        """ Find the ID for the given channel name from Twitch. """
        variables = {
            "login": channel_name
        }

        data = await self.fetch_twitch_gql(
            operations["find_channel"],
            variables
        )

        user = data["user"]

        if user is None:
            return None

        return user
    
    async def get_spade_url(self) -> str:
        """ Get the Spade URL. If it is not set, fetch it. """
        if self._spade_url:
            return self._spade_url

        async with self.session as session:
            async with session.get("https://static.twitchcdn.net/config/settings.js", raise_for_status=True) as resp:
                data: dict = json.loads((await resp.text())[28:])

        self._spade_url = data.get("spade_url")

        return self._spade_url

    async def initialize_user(self) -> None:
        """ Update the user's authentication and then find the client ID. """
        for name, value in self._cookie_jar.items():
            if name == "twilight-user":
                data: str = urllib.parse.unquote(str(value))
                data: dict = json.loads(data)

                self.authorization_token = data.get("authToken")
                self.user_id = int(data.get("id"))

            elif name == "login":
                self.username = value

            elif name == "unique_id":
                self.unique_id = value
        
        self.client_id = await self.fetch_client_id()
    
    async def initialize_websocket(self, function) -> None:
        self._websocket = Pubsub()

        if function:
            self._websocket.set_event_callback(function)
        
        asyncio.get_event_loop().create_task(self._websocket.run())
        
        while not self._websocket.initialized:
            await asyncio.sleep(1)

        await self._websocket.listen("stream-change-v1", self.user_id, self.authorization_token)
        await self._websocket.listen("community-points-user-v1", self.user_id, self.authorization_token)
    
    async def is_following(self, channel: Channel) -> bool:
        """ See if the account is following the given channel. """
        data = await self.fetch_twitch_gql("ChatRestrictions", {
            "channelLogin": channel.name
        }, is_persisted=True)

        return data["channel"]["self"]["follower"] is not None
    
    async def follow(self, channel: Channel) -> None:
        """ Follow the given channel. """
        await self.fetch_twitch_gql("FollowButton_FollowUser", {
            "input": {
                "disableNotifications": False,
                "targetID": str(channel.id)
            }
        }, is_persisted=True)

        log.info(f"Started following", extra={
            "channel": channel.name,
            "account": self.username
        })

    async def claim_points(self, channel: Channel, claim_id: str) -> None:
        """ Claim the 50 points with the given ID on the given channel. """
        await self.fetch_twitch_gql("ClaimCommunityPoints", {
            "input": {
                "channelID": str(channel.id),
                "claimID": claim_id
            }
        }, is_persisted=True)

        log.info(f"Claimed 50 channel points", extra={
            "channel": channel.name,
            "account": self.username
        })
    
    async def available_points(self, channel: Channel) -> Optional[str]:
        """ Returns the currently available reward claim's ID. """
        data = await self.fetch_twitch_gql("ChannelPointsContext", {
            "channelLogin": channel.name
        }, is_persisted=True)

        points: dict = data["community"]["channel"]["self"]["communityPoints"]

        if points.get("availableClaim") is None:
            return None
        
        return points["availableClaim"]["id"]
    
    async def watch_minute(self, channel: Channel) -> None:
        """
        Watch one minute of the given broadcast on the given channel.
        
        :param channel_id: ID of the channel.
        :param broadcast_id: ID of the specific broadcast.
        """

        data = {
            "event": "minute-watched",
            "properties": {
                "channel_id": channel.id,
                "broadcast_id": channel.stream.id,
                "user_id": self.user_id,
                "player": "site",
            }
        }

        async with self.session as session:
            await session.post(
                await self.get_spade_url(),
                data=b64encode(json.dumps([data]).encode("utf-8")),
                raise_for_status=True
            )

        log.info(f"Watched one minute", extra={
            "channel": channel.display_name,
            "account": self.username
        })
