"""

Actually sends out the watched minutes for each account, and handles callback
events for streams going online or offline. This is done by the clients
appending `signum.Event` objects to the queue in the manager.

"""

import asyncio
import json
import logging
from typing import List, Optional

from .account import Account
from .channel import Channel

log = logging.getLogger(__name__)


class Manager:
    def __init__(self, channel_names: List[str]):
        self.accounts: List[Account] = []
        self.channels: List[Channel] = []

        self._channel_names: List[str] = channel_names
    
    def _find_account_by_id(self, user_id: int) -> Optional[Account]:
        """ Find an account in the local storage from its ID. """
        for account in self.accounts:
            if account.user_id == int(user_id):
                return account
    
    def _find_channel_by_id(self, channel_id: int) -> Optional[Channel]:
        """ Find a channel in the local storage from its ID. """
        for channel in self.channels:
            if channel.id == int(channel_id):
                return channel
    
    async def _update_event(self, event: dict) -> None:
        """
        Update a channel's status based on data from the client's websockets.
        """

        data: dict = event.get("data", {})

        # Most likely PONG message, doesn't have any useful data so we skip.
        if not data.get("topic") or not data.get("message"):
            return

        topic, user_id = data["topic"].rsplit(".", 1)
        message = json.loads(data["message"])
        
        # Find user by the given ID.
        user = self._find_account_by_id(user_id)

        if not user:
            log.warning(f"Failed to find user {user_id} from event callback")
            return

        # TODO: Fix this up soon, define callbacks rather than a big ol' if/elif.
        if topic == "stream-change-v1":
            channel = self._find_channel_by_id(message["channel_id"])

            if not channel:
                return

            if message["type"] == "stream_up" and not channel.is_streaming:
                channel.update(await self.accounts[0].fetch_channel(channel.name))
                log.info(f"Started streaming {channel.stream.game_name}", extra={
                    "channel": channel.display_name
                })

            elif message["type"] == "stream_down" and channel.is_streaming:
                channel.stream = None
                log.info(f"Stopped streaming", extra={
                    "channel": channel.display_name
                })

        elif topic == "community-points-user-v1":
            if message["type"] == "points-earned":
                channel = self._find_channel_by_id(message["data"]["balance"]["channel_id"])

                log.info(
                    f"Gained {message['data']['point_gain']['total_points']} points "
                    f"({message['data']['balance']['balance']} total)",
                    extra={
                        "channel": channel.name,
                        "account": user.username
                    }
                )

            elif message["type"] == "claim-available":
                claim = message["data"]["claim"]
                channel = self._find_channel_by_id(claim["channel_id"])

                await user.claim_points(channel, claim["id"])
    
    async def run(self) -> None:
        """ Start watching minutes on all clients. """

        # Initialize the channel on one of the clients. By this I mean, find
        # the channel's ID (mainly) and get the broadcast ID. This will then
        # be saved to the `self.channels` array for later use.
        if len(self.accounts) < 1:
            raise Exception("No valid accounts were found")
        
        for account in self.accounts:
            await account.initialize_user()
            await account.initialize_websocket(self._update_event)
        
        for channel_name in self._channel_names:
            channel_data = await self.accounts[0].fetch_channel(channel_name)

            if not channel_data:
                log.warn(f"Channel {channel_name} was not found on Twitch")
                continue
            
            self.channels.append(Channel(channel_data))
        
        if len(self.channels) < 1:
            raise Exception("No valid channels were found")
        
        for account in self.accounts:
            for channel in self.channels:
                if not await account.is_following(channel):
                    await account.follow(channel)

                claim_id = await account.available_points(channel)

                if claim_id is not None:
                    await account.claim_points(channel, claim_id)
        
        log.info("Started the manager loop")

        while True:
            await asyncio.sleep(60)

            # Update all the channels while looping over clients.
            # TODO: Follow raids.
            # TODO: Follow users if not already following.

            # TODO: Mark only two channels per client.
            tasks = []

            for account in self.accounts:
                for channel in self.channels:
                    if channel.is_streaming:
                        tasks.append(account.watch_minute(channel))
            
            await asyncio.gather(*tasks)
