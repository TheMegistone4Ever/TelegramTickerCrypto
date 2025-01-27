from re import search, DOTALL
from time import sleep
from typing import Optional


def to_minutes(time_str: str) -> int:
    """
    Convert a time string to total minutes.
    Supports formats: [Nd] [Nh] [Nm] where N is a number

    Args:
        time_str (str): Time string like "3h", "3m", "3h 59m", "1d 5h 44m"

    Returns:
        int: Total minutes

    Examples:
        >>> to_minutes("3h")
        180
        >>> to_minutes("45m")
        45
        >>> to_minutes("1d 5h 44m")
        1784
    """

    time_str = time_str.strip()

    total_minutes = 0
    parts = time_str.split()

    for part in parts:
        if part.endswith("d"):
            total_minutes += int(part[:-1]) * 24 * 60
        elif part.endswith("h"):
            total_minutes += int(part[:-1]) * 60
        elif part.endswith("m"):
            total_minutes += int(part[:-1])

    return total_minutes


def from_minutes(minutes: int) -> str:
    """
    Convert total minutes to a time string in the format "Nd Nh Nm"

    Args:
        minutes (int): Total number of minutes

    Returns:
        str: Formatted time string

    Examples:
        >>> from_minutes(180)
        "3h"
        >>> from_minutes(45)
        "45m"
        >>> from_minutes(1784)
        "1d 5h 44m"
    """

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


def transform_token(text: str) -> Optional[str]:
    """Transform string using regex approach"""

    text = text.strip()

    pattern = r"(?:#\d+\n)?\??\n(.*?)\n/\n(.*?)\n(.*?)$"
    match = search(pattern, text, DOTALL)
    if match:
        token1, token2, description = match.groups()
        return f"{token1.split()[-1]}/{token2}: {description}"
    return None


def string_to_number(money: str) -> int:
    """
    Convert a money string like "$5.3K" or "$6.9M" to an integer
    Examples:
    "$5.3K" -> 5300
    "$6.9M" -> 6900000
    "$1.2B" -> 1200000000
    """

    MULTIPLIERS = {
        "K": 1000,
        "M": 1000000,
        "B": 1000000000
    }

    money = money.replace("$", "").strip()

    last_char = money[-1].upper()
    if last_char in MULTIPLIERS:
        number = float(money[:-1])
        return int(number * MULTIPLIERS[last_char])
    else:
        return int(float(money))


def number_to_string(number: int) -> str:
    """
    Convert a number to a formatted money string using the same multipliers
    Examples:
    5300 -> "$5.3K"
    6900000 -> "$6.9M"
    1200000000 -> "$1.2B"
    """

    MULTIPLIERS = {
        "B": 1000000000,
        "M": 1000000,
        "K": 1000
    }

    for suffix, value in MULTIPLIERS.items():
        if number >= value:
            return f"{number / value:.1f}{suffix}"

    return str(number)


def avoid_tg_rate_limit():
    """Avoid hitting Telegram's rate limits"""

    sleep(2)


def wait_dynamic_content():
    """Wait for dynamic content to load"""

    sleep(5)
