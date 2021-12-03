from datetime import datetime
from typing import Optional

def process_time_string(date_string: str) -> datetime:
    try:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

class Stream:
    def __init__(self, data: dict = None):
        self.id: int = None
        self.title: str = None
        self.type: str = None
        self.viewers_count: int = None
        self.created_at: datetime = None
        self.game_name: str = None

        if data: self.update(data)
    
    def update(self, data: dict) -> None:
        """ Update the Stream object based on Twitch GQL data. """
        self.id = int(data["id"]) if data.get("id") else None
        self.viewers_count = int(data["viewersCount"]) if data.get("viewersCount") else None

        self.title = data.get("title")
        self.type = data.get("type")

        if data.get("createdAt"):
            self.created_at = process_time_string(data["createdAt"])
        
        if data.get("game"):
            self.game_name = data["game"]["name"]

class Channel:
    def __init__(self, data: dict = None):
        self.id: int = None
        self.name: str = None
        self.display_name: str = None
        self.created_at: str = None
        self.stream: Optional[Stream] = None

        if data: self.update(data)

    @property
    def is_streaming(self) -> bool:
        return self.stream is not None

    def update(self, data: dict) -> None:
        """ Update the Channel object based on Twitch GQL data. """
        self.id = int(data["id"]) if data.get("id") else None

        self.name = data.get("login")
        self.display_name = data.get("displayName")

        if data.get("createdAt"):
            self.created_at = process_time_string(data["createdAt"])

        self.is_partner = data.get("roles", {}).get("isPartner", False)

        if data.get("stream") is not None:
            self.stream = Stream(data["stream"])
