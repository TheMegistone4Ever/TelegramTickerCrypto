from re import search, DOTALL
from time import time
from typing import Optional, Tuple

from bot.models import Multiplier
from models import PairData, SecurityData, RiskLevel, TimeFrame
from scoring_config import SCORING_CONFIG


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
    """Transforms token text into a tuple of token and description."""

    match = search(r"(?:#\d+\n)?\??\n(.*?)\n/\n(.*?)\n(.*?)$", text.strip(), DOTALL)
    if match:
        token_parts = match.group(1).split()
        token = f"{token_parts[-1]}/{match.group(2)}" if token_parts else ""
        description = match.group(3)
        return token, description
    return None


def string_to_number(money: str) -> float:
    """Convert a money string like "$5.3K" or "$6.9M" to a float."""

    money = money.strip().replace("$", "").replace("%", "").replace(",", "")

    if "<" in money:
        money = money.split("<", 1)[-1]

    try:
        if (last_char := money[-1].upper()) in Multiplier.__members__:
            return float(money[:-1]) * Multiplier[last_char].value
        else:
            return float(money)
    except (ValueError, IndexError) as e:
        print(f"Error processing pair: {e}")
        return .0


def number_to_string(number: float) -> str:
    """Convert a number to a formatted money string using the same multipliers."""

    for suffix, multiplier in Multiplier.__members__.items():
        if number >= multiplier.value:
            return f"{number / multiplier.value:.2f}{suffix}"
    return str(number)


def as_number(comma_number: str) -> int:
    """Convert a comma-separated number string to an integer."""

    return int(comma_number.replace(",", "").strip())


def get_solana_address(dex_solana_link: str, sep="https://dexscreener.com/solana/") -> str:
    """Extract Solana address from DEX Solana link."""

    return dex_solana_link.split(sep, 1)[-1]


def define_risk_level(border_class: str) -> Optional[RiskLevel]:
    if "border-l-destructive" in border_class:
        return RiskLevel.CRITICAL
    elif "border-l-primary" in border_class:
        return RiskLevel.HIGH
    elif "border-l-pending" in border_class:
        return RiskLevel.MEDIUM
    elif "border-l-neutral-700" in border_class:
        return RiskLevel.LOW
    return None


def wait_for_url_change(sb, keyword, timeout, wait_time=.5, error_type="print", error_message=None):
    """
    Waits for the current URL to contain a specific keyword within a given timeout.

    Args:
        sb: The SeleniumBase object (or any object with `get_current_url()` and `sleep()` methods).
        keyword: The keyword to look for in the URL.
        timeout: The maximum time (in seconds) to wait for the URL change.
        wait_time: The time (in seconds) to wait between checks.
        error_type:
          - "print": Prints an error message and continues. (Default)
          - "raise": Raises a custom exception or a TimeoutError if error_message is not given.
          - "silent" - Does nothing if timeout occurs
        error_message: The custom error message to print or raise (optional).
                       If not provided and error_type is "raise", a generic TimeoutError is raised.

    Raises:
        TimeoutError: If error_type is "raise" and the timeout is reached.
        Exception: If error_type is "raise" and error_message is provided.
    """

    start_time = time()
    while keyword not in sb.get_current_url():
        sb.sleep(wait_time)
        if time() - start_time > timeout:
            if error_type == "print":
                print(error_message or f"Timeout: URL did not change to include \"{keyword}\"")
            elif error_type == "raise":
                if error_message:
                    raise Exception(error_message)
                else:
                    raise TimeoutError(f"Timeout: URL did not change to include \"{keyword}\"")
            break


def calculate_token_score(security_data: SecurityData) -> float:
    """Calculate token security score based on various factors."""

    max_score = 0
    for risk_scoring in SCORING_CONFIG:
        for weight in risk_scoring.weights.values():
            max_score += abs(weight.birdeye) + abs(weight.goplus)

    score = max_score

    for risk_scoring in SCORING_CONFIG:
        if not (severity_data := getattr(security_data, risk_scoring.level.value)):
            continue

        for issue, details in severity_data.items():
            score += sum(getattr(risk_scoring.weights.get(issue), key, 0) for key, value in details.items() if value)

    return max(0, min(100, score / max_score * 100))


def format_telegram_message(data: PairData, threshold=98):
    """Format data for a Telegram message with security score."""

    security_info, score_text = "", ""

    if data.security:
        score_emoji = "🟢" if data.security.score >= threshold else "🔴"
        score_text = f"{score_emoji} {data.security.score:.2f}%"

        for risk_level in RiskLevel:
            if severity_data := getattr(data.security, risk_level.value):
                security_info += f"\n{risk_level.emoji} <b>{risk_level.label} Security Risks:</b> {risk_level.emoji}"
                for issue, details in severity_data.items():
                    for platform, description in details.items():
                        if description:
                            security_info += f"\n<u>{platform.capitalize()}</u> - {issue.capitalize()}: {description}"

    def format_change(value):
        return f"{number_to_string(value)}%" if value is not None else "-"

    change_lines = [
        f"🕛 <b>{time_frame.label} Change:</b> <i>{format_change(getattr(data, time_frame.attribute, None))}</i>"
        for time_frame in TimeFrame
    ]

    return f"""
🌱 <b>Token:</b> <a href="https://dexscreener.com/solana/{data.address}">{data.token}: {data.description}</a>
💵 <b>Price:</b> ${number_to_string(data.price)}
🕛 <b>Age:</b> {from_minutes(data.age)}
🛒 <b>Sells:</b> {data.sells}
📊 <b>Volume:</b> ${number_to_string(data.volume)}
👥 <b>Makers:</b> {data.makers}
{"\n".join(change_lines)}
💧 <b>Liquidity:</b> ${number_to_string(data.liquidity)}
💰 <b>Market Cap:</b> ${number_to_string(data.market_cap)}

📊 <b>Models Score:</b>
Model 1: {score_text}
Model 2: <i>currently not working</i>
{security_info}
"""


def handle_command(command: str) -> str:
    commands = {
        "start": "Welcome to CryptoTicker! I'm your crypto assistant. Ask me questions about cryptocurrencies or specific coins in our database. 🚀",
        "help": """Here's how I can help:
- Ask about specific coins
- Get market information
- Check trending cryptocurrencies
- Get real-time updates
Available commands:
  /start: Start the conversation
  /help: Show this help message
  /info: Get information about the bot
  /trends: Show trending cryptocurrencies
  /support: Get support or ask questions
Just ask your question! 📊""",
        "info": "I'm here to provide real-time crypto information. What would you like to know?",
        "trends": "Let me show you what's trending in the crypto world right now.",
        "support": "Need help? Just ask your question and I'll assist you!",
    }
    return commands.get(
        command, "Unknown command. Try /help to see what I can do!"
    )
