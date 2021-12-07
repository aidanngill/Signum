import argparse
import asyncio
import glob
import logging
import sys
from typing import List, Tuple

from .account import Account
from .manager import Manager

log = logging.getLogger()
log.setLevel(logging.DEBUG)

class StreamFormatter(logging.Formatter):
    base_format: List[str] = [
        "[%(asctime)s]",
        "%(message)s"
    ]

    extra_format: List[Tuple[str, str, int]] = [
        ("channel", "[%(channel)s]", 1),
        ("account", "[%(account)s]", 1)
    ]

    def format(self, record):
        _old_format = self._style._fmt
        _base_format = self.base_format.copy()

        for attr, form, index in self.extra_format:
            if hasattr(record, attr):
                _base_format.insert(index, form)
        
        self._style._fmt = " ".join(_base_format)
        result = super().format(record)
        self._style._fmt = _old_format

        return result

stream_formatter = StreamFormatter(datefmt="%Y-%m-%d %H:%M:%S")

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(stream_formatter)
stream_handler.setLevel(logging.INFO)

file_formatter = logging.Formatter(
    "%(created)i/%(name)s/%(levelname)s/%(account)s:%(channel)s/%(message)s",
    defaults={
        "account": "",
        "channel": ""
    }
)

file_handler = logging.FileHandler("debug.log")
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)

log.addHandler(stream_handler)
log.addHandler(file_handler)

logging.getLogger("charset_normalizer").setLevel(logging.ERROR)

async def main():
    parser = argparse.ArgumentParser(description="Twitch channel point farmer")

    parser.add_argument("-j", "--cookies", type=str, required=False, default="cookies.txt", help="Pattern to find cookie files by")
    parser.add_argument("-c", "--channels", nargs="+", required=True, help="List of channels to watch")

    args = parser.parse_args()

    manager = Manager(args.channels)

    for file in glob.glob(args.cookies):
        manager.accounts.append(Account(file))

    await manager.run()

asyncio.run(main())
