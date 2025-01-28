from re import search, DOTALL
from time import sleep
from typing import Optional, Tuple

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options

MULTIPLIERS = {
    "K": 1000,
    "M": 1000000,
    "B": 1000000000,
}


def to_minutes(time_str: str) -> int:
    """Convert a time string to total minutes. Supports formats: [Nd] [Nh] [Nm] where N is a number"""

    return sum(int(part[:-1]) * (24 * 60 if part.endswith("d") else 60 if part.endswith("h") else 1)
               for part in time_str.split())


def from_minutes(minutes: int) -> str:
    """Convert total minutes to a time string in the format "Nd Nh Nm" """

    days = minutes // (24 * 60)
    remaining_minutes = minutes % (24 * 60)
    hours = remaining_minutes // 60
    final_minutes = remaining_minutes % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if final_minutes > 0 or not parts:
        parts.append(f"{final_minutes}m")

    return " ".join(parts)


def transform_token(text: str) -> Optional[Tuple[str, str]]:
    return (lambda m: (f"{m.group(1).split()[-1]}/{m.group(2)}", m.group(3)) if m else None
            )(search(r"(?:#\d+\n)?\??\n(.*?)\n/\n(.*?)\n(.*?)$", text.strip(), DOTALL))


def string_to_number(money: str) -> float:
    """Convert a money string like "$5.3K" or "$6.9M" to an integer"""

    money = money.strip().replace("$", "").replace("%", "").replace(",", "")

    if "<" in money:
        money = money.split("<", 1)[-1]

    try:
        last_char = money[-1].upper()
        if last_char in MULTIPLIERS:
            number = float(money[:-1])
            return number * MULTIPLIERS[last_char]
        else:
            return float(money)
    except (ValueError, IndexError) as e:
        print(f"Error processing pair: {e}")


def number_to_string(number: int) -> str:
    """Convert a number to a formatted money string using the same multipliers"""

    for suffix, value in list(MULTIPLIERS.items())[::-1]:
        if number >= value:
            return f"{number / value:.2f}{suffix}"

    return str(number)


def as_number(comma_number: str) -> int:
    """Convert a comma-separated number string to an integer"""

    return int(comma_number.replace(",", "").strip())


def get_solana_address(dex_solana_link: str, sep="https://dexscreener.com/solana/") -> str:
    """Extract Solana address from DEX Solana link"""

    return dex_solana_link.split(sep, 1)[-1]


def avoid_tg_rate_limit(seconds=2):
    """Avoid hitting Telegram's rate limits"""

    sleep(seconds)


def wait_dynamic_content(seconds=5):
    """Wait for dynamic content to load"""

    sleep(seconds)


def wait_static_content(seconds=2):
    """Wait for static content to load"""

    sleep(seconds)


def setup_chrome_driver(user_data_dir: str, profile_dir="Default") -> Chrome:
    """Setup Chrome driver with your existing profile"""

    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--profile-directory={profile_dir}")
    return Chrome(options=chrome_options)
