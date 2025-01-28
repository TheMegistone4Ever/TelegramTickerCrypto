from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from telebot import TeleBot

from bot.birdeye import check_security_risks, should_post_token
from bot.utils import (to_minutes, from_minutes, transform_token, string_to_number, number_to_string,
                       avoid_tg_rate_limit, wait_dynamic_content, setup_chrome_driver, as_number, get_solana_address)

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
BOT_TOKEN = getenv("BOT_TOKEN")
channel_id = getenv("CHANNEL_ID")
user_data_dir = getenv("USER_DATA_DIR")
bot = TeleBot(BOT_TOKEN)


def scrape_dexscreener_data(driver, url="https://dexscreener.com/solana?rankBy=pairAge&order=asc&minLiq=2000&minAge=3"):
    """Scrape data from DexScreener"""

    driver.get(url)

    WebDriverWait(driver, 20).until(
        ec.presence_of_element_located((By.CLASS_NAME, "ds-dex-table-th"))
    )

    wait_dynamic_content()

    pairs = driver.find_elements(By.CSS_SELECTOR, "a.ds-dex-table-row")

    pairs_data = []
    for pair in pairs:
        try:
            columns = pair.find_elements(By.CSS_SELECTOR, "div.ds-table-data-cell")
            if len(columns) < 13:
                continue
            token, description = transform_token(columns[0].text)
            pair_data = {
                "token": token,
                "description": description,
                "address": get_solana_address(pair.get_attribute("href")),
                "price": string_to_number(columns[1].text),
                "age": to_minutes(columns[2].text),
                "buys": as_number(columns[3].text),
                "sells": as_number(columns[4].text),
                "volume": string_to_number(columns[5].text),
                "makers": as_number(columns[6].text),
                "5m_change": string_to_number(columns[7].text) if len(columns[7].text) > 1 else None,
                "1h_change": string_to_number(columns[8].text) if len(columns[8].text) > 1 else None,
                "6h_change": string_to_number(columns[9].text) if len(columns[9].text) > 1 else None,
                "24h_change": string_to_number(columns[10].text) if len(columns[10].text) > 1 else None,
                "liquidity": string_to_number(columns[11].text),
                "market_cap": string_to_number(columns[12].text),
            }
            pairs_data.append(pair_data)
        except (ValueError, IndexError) as e:
            print(f"Error processing pair: {e}")
            continue

    return pairs_data


def calculate_token_score(security_data):
    """Calculate token security score based on various factors"""

    SCORING_WEIGHTS = {
        "c": {
            "airdrop_scam": {"b": -0.5, "g": -0.3},
            "fake_token": {"b": -0.5, "g": -0.3},
            "honeypot": {"b": -0.5, "g": -0.3},
            "owner_can_change_balance": {"b": -0.4, "g": -0.2},
            "ownership_renounced": {"b": -0.3, "g": -0.3},
            "self_destruct": {"b": -0.5, "g": -0.3}
        },
        "h": {
            "assigned_address'_slippage_is_modifiable": {"b": -0.2, "g": -0.1},
            "cannot_be_bought": {"b": -0.3, "g": -0.2},
            "cannot_sell_all": {"b": -0.3, "g": -0.2},
            "dex_info": {"b": -0.1, "g": -0.1},
            "mintable": {"b": -0.2, "g": -0.2},
            "modifiable_anti_whale": {"b": -0.2, "g": -0.1},
            "open_source": {"b": -0.2, "g": -0.2},
            "proxy_contract": {"b": -0.2, "g": -0.1},
            "token_holder_number": {"b": -0.1, "g": -0.1},
            "trading_with_cooldowntime": {"b": -0.2, "g": -0.1},
            "trust_list": {"b": -0.2, "g": -0.2},
            "with_hidden_owner": {"b": -0.2, "g": -0.1},
            "blacklist": {"b": -0.2, "g": -0.1},
            "buy_tax": {"b": -0.1, "g": -0.1},
            "freezable": {"b": -0.2, "g": -0.1},
            "gas_abuse": {"b": -0.2, "g": -0.1},
            "max_fee": {"b": -0.1, "g": -0.1},
            "other_potential_risks": {"b": -0.1, "g": -0.1},
            "sell_tax": {"b": -0.1, "g": -0.1},
            "transfer_fees": {"b": -0.1, "g": -0.1},
            "transfer_fees_enable": {"b": -0.1, "g": -0.1},
            "extreme_fee_test": {"b": -0.2, "g": -0.1},
            "top10_lp_token_holders_info": {"b": -0.2, "g": -0.2},
            "inadequate_liquidity_test": {"b": -0.2, "g": -0.1},
            "inadequate_ininitial_liquidity_test": {"b": -0.2, "g": -0.1},
            "take_back_ownership": {"b": -0.2, "g": -0.1},
            "token_percentage_of_creator": {"b": -0.1, "g": -0.1},
            "token_percentage_of_owner": {"b": -0.1, "g": -0.1},
            "ua_percentage": {"b": -0.1, "g": -0.1},
            "jupiter_strict_list": {"b": -0.2, "g": -0.0},
            "top_holders_percentage": {"b": -0.2, "g": -0.2}
        },
        "m": {
            "mutable_info": {"b": -0.1, "g": -0.1},
            "whitelist": {"b": -0.1, "g": -0.1},
            "with_external_call": {"b": -0.1, "g": -0.1},
            "liquidity_locked_or_liquidity_burned": {"b": -0.1, "g": -0.1},
            "creator_high_lp_balance_test": {"b": -0.1, "g": -0.1},
            "owner_high_lp_balance_test": {"b": -0.1, "g": -0.1}
        },
        "n": {
            "anti_whale": {"b": -0.05, "g": -0.05},
            "token_total_supply": {"b": -0.0, "g": -0.0},
            "note": {"b": -0.0, "g": -0.0},
            "fee_withdrawer": {"b": -0.0, "g": -0.0},
            "freeze_authority": {"b": -0.0, "g": -0.0},
            "transfer_fee_config_authority": {"b": -0.0, "g": -0.0},
            "liquidity_burned": {"b": -0.05, "g": -0.05},
            "liquidity_locked": {"b": -0.05, "g": -0.05},
            "lp_holders_count": {"b": -0.0, "g": -0.0},
            "lp_token_total_supply": {"b": -0.0, "g": -0.0},
            "creator_address": {"b": -0.0, "g": -0.0},
            "creator_balance": {"b": -0.0, "g": -0.0},
            "first_mint_time": {"b": -0.0, "g": -0.0},
            "first_mint_tx": {"b": -0.0, "g": -0.0},
            "owner_address": {"b": -0.0, "g": -0.0},
            "owner_balance": {"b": -0.0, "g": -0.0},
            "ua_balance": {"b": -0.0, "g": -0.0},
            "update_authority_(ua)": {"b": -0.0, "g": -0.0}
        }
    }

    max_score = sum(
        abs(weight["b"]) + abs(weight["g"])
        for category in SCORING_WEIGHTS.values()
        for weight in category.values()
    )

    score = max_score

    for risk_level, risks in security_data.items():
        if risk_level not in SCORING_WEIGHTS:
            continue

        for issue, details in risks.items():
            issue_key = issue.lower().replace(" ", "_")
            if issue_key not in SCORING_WEIGHTS[risk_level]:
                continue

            weights = SCORING_WEIGHTS[risk_level][issue_key]
            for platform, weight in weights.items():
                if not details[platform]:
                    continue

                score -= abs(weight)

    return max(0, min(100, score / max_score * 100))


def format_telegram_message(data, threshold=98):
    """Format data for a Telegram message with security score"""

    security_info, score_text = "", ""

    if "security" in data:
        security_score = calculate_token_score(data["security"])
        score_emoji = "🟢" if security_score >= threshold else "🔴"
        score_text = f"{score_emoji} {security_score:.2f}%"

        severities = (
            ("c", "Critical", "⚠️⚠️"),
            ("h", "High", "⚠️"),
            ("m", "Medium", "⚡️"),
            ("n", "Low", "🍏"),
        )

        for severity_key, severity_label, emoji in severities:
            if data["security"].get(severity_key):
                security_info += f"\n{emoji} <b>{severity_label} Security Risks:</b> {emoji}"
                for issue, details in data["security"][severity_key].items():
                    for source_key, source_name in [("b", "BirdEye"), ("g", "GoPlus")]:
                        if details.get(source_key):
                            security_info += f"\n<u>{source_name}</u> - {issue}: {details[source_key]}"

    def format_change(value):
        return f"{number_to_string(value)}%" if value is not None else "-"

    time_frames = [
        ("5m", "5m_change"),
        ("1h", "1h_change"),
        ("6h", "6h_change"),
        ("24h", "24h_change")
    ]
    change_lines = [f"🕛 <b>{label} Change:</b> <i>{format_change(data.get(key))}</i>"
                    for label, key in time_frames]

    return f"""
🌱 <b>Token:</b> <a href="https://dexscreener.com/solana/{data["address"]}">{data["token"]}: {data["description"]}</a>
💵 <b>Price:</b> ${number_to_string(data["price"])}
🕛 <b>Age:</b> {from_minutes(data["age"])}
🛒 <b>Sells:</b> {data["sells"]}
📊 <b>Volume:</b> ${number_to_string(data["volume"])}
👥 <b>Makers:</b> {data["makers"]}
{"\n".join(change_lines)}
💧 <b>Liquidity:</b> ${number_to_string(data["liquidity"])}
💰 <b>Market Cap:</b> ${number_to_string(data["market_cap"])}

📊 <b>Models Score:</b>
Model 1: {score_text}
Model 2: <i>currently not working</i>
{security_info}
"""


def main():
    driver = setup_chrome_driver(user_data_dir)
    try:
        pairs_data = scrape_dexscreener_data(driver)

        for pair_data in pairs_data:
            pair_data["security"] = check_security_risks(driver, pair_data["token"])

            if should_post_token(pair_data["security"]):
                msg = format_telegram_message(pair_data)
                bot.send_message(channel_id, msg, parse_mode="HTML")
                avoid_tg_rate_limit()

    finally:
        driver.quit()


if __name__ == "__main__":
    main()


    @bot.message_handler(commands=["start"])
    def tg_start(message):
        print(message.chat.id)
        bot.send_message(message.chat.id, "ІДІ")


    @bot.message_handler(commands=["help"])
    def tg_help(message):
        bot.send_message(message.chat.id, "<u>НЕ ІДІ</u>", parse_mode="HTML")


    @bot.message_handler()
    def tg_echo(message):
        bot.reply_to(message, message.text)


    bot.polling(none_stop=True)
