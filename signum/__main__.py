import argparse
import asyncio
import glob
import logging

from .account import Account
from .manager import Manager

# TODO: Improve logging.
# [%(asctime)s] [%(account)s] [%(channel)s] %(message)s <-- Stream
# %(created)s:%(name)s:%(levelname)s|%(account)s:%(channel)s|%(message)s <-- File

logging.basicConfig(
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

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
