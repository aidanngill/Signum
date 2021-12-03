import random
import string


def generate_nonce(length: int) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
