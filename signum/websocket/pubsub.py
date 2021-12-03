import asyncio
import json
import logging
import time
from typing import Optional

import websockets
import websockets.client

from ..util import generate_nonce

log = logging.getLogger(__name__)

class Pubsub:
    def __init__(self):
        self._websocket: Optional[websockets.client.WebSocketClientProtocol] = None

        self._initialized = False
        self._event_callback = None
    
    @property
    def initialized(self) -> bool:
        return self._initialized
    
    def set_event_callback(self, function) -> None:
        self._event_callback = function
    
    async def ping(self):
        await self._websocket.send(json.dumps({
            "type": "PING"
        }))
    
    async def listen(self, topic: str, target_id: str, authorization_token: str):
        await self._websocket.send(json.dumps({
            "type": "LISTEN",
            "nonce": generate_nonce(30),
            "data": {
                "topics": [
                    f"{topic}.{target_id}"
                ],
                "auth_token": authorization_token
            }
        }))

    async def initialize(self):
        await self.ping()

        self._initialized = True
    
    async def process(self, message: str):
        processed_message = message.strip()
        processed_data = json.loads(processed_message)

        log.debug(processed_data)

        if self._event_callback:
            await self._event_callback(processed_data)

    async def run(self):
        last_ping = time.time()
        self._websocket = await websockets.client.connect("wss://pubsub-edge.twitch.tv/v1")
        
        while True:
            try:
                if not self._initialized:
                    await self.initialize()

                message = await asyncio.wait_for(self._websocket.recv(), timeout=10)

                await self.process(message)

            except asyncio.TimeoutError:
                if last_ping + (4 * 60) < time.time():
                    await self.ping()
                    last_ping = time.time()
