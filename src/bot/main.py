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
            "airdrop_scam": {"B": -0.5, "G": -0.3},
            "fake_token": {"B": -0.5, "G": -0.3},
            "honeypot": {"B": -0.5, "G": -0.3},
            "owner_can_change_balance": {"B": -0.4, "G": -0.2},
            "ownership_renounced": {"B": -0.3, "G": -0.3},
            "self_destruct": {"B": -0.5, "G": -0.3}
        },
        "h": {
            "assigned_address'_slippage_is_modifiable": {"B": -0.2, "G": -0.1},
            "cannot_be_bought": {"B": -0.3, "G": -0.2},
            "cannot_sell_all": {"B": -0.3, "G": -0.2},
            "dex_info": {"B": -0.1, "G": -0.1},
            "mintable": {"B": -0.2, "G": -0.2},
            "modifiable_anti_whale": {"B": -0.2, "G": -0.1},
            "open_source": {"B": -0.2, "G": -0.2},
            "proxy_contract": {"B": -0.2, "G": -0.1},
            "token_holder_number": {"B": -0.1, "G": -0.1},
            "trading_with_cooldowntime": {"B": -0.2, "G": -0.1},
            "trust_list": {"B": -0.2, "G": -0.2},
            "with_hidden_owner": {"B": -0.2, "G": -0.1},
            "blacklist": {"B": -0.2, "G": -0.1},
            "buy_tax": {"B": -0.1, "G": -0.1},
            "freezable": {"B": -0.2, "G": -0.1},
            "gas_abuse": {"B": -0.2, "G": -0.1},
            "max_fee": {"B": -0.1, "G": -0.1},
            "other_potential_risks": {"B": -0.1, "G": -0.1},
            "sell_tax": {"B": -0.1, "G": -0.1},
            "transfer_fees": {"B": -0.1, "G": -0.1},
            "transfer_fees_enable": {"B": -0.1, "G": -0.1},
            "extreme_fee_test": {"B": -0.2, "G": -0.1},
            "top10_lp_token_holders_info": {"B": -0.2, "G": -0.2},
            "inadequate_liquidity_test": {"B": -0.2, "G": -0.1},
            "inadequate_ininitial_liquidity_test": {"B": -0.2, "G": -0.1},
            "take_back_ownership": {"B": -0.2, "G": -0.1},
            "token_percentage_of_creator": {"B": -0.1, "G": -0.1},
            "token_percentage_of_owner": {"B": -0.1, "G": -0.1},
            "ua_percentage": {"B": -0.1, "G": -0.1},
            "jupiter_strict_list": {"B": -0.2, "G": -0.0},
            "top_holders_percentage": {"B": -0.2, "G": -0.2}
        },
        "m": {
            "mutable_info": {"B": -0.1, "G": -0.1},
            "whitelist": {"B": -0.1, "G": -0.1},
            "with_external_call": {"B": -0.1, "G": -0.1},
            "liquidity_locked_or_liquidity_burned": {"B": -0.1, "G": -0.1},
            "creator_high_lp_balance_test": {"B": -0.1, "G": -0.1},
            "owner_high_lp_balance_test": {"B": -0.1, "G": -0.1}
        },
        "n": {
            "anti_whale": {"B": -0.05, "G": -0.05},
            "token_total_supply": {"B": -0.0, "G": -0.0},
            "note": {"B": -0.0, "G": -0.0},
            "fee_withdrawer": {"B": -0.0, "G": -0.0},
            "freeze_authority": {"B": -0.0, "G": -0.0},
            "transfer_fee_config_authority": {"B": -0.0, "G": -0.0},
            "liquidity_burned": {"B": -0.05, "G": -0.05},
            "liquidity_locked": {"B": -0.05, "G": -0.05},
            "lp_holders_count": {"B": -0.0, "G": -0.0},
            "lp_token_total_supply": {"B": -0.0, "G": -0.0},
            "creator_address": {"B": -0.0, "G": -0.0},
            "creator_balance": {"B": -0.0, "G": -0.0},
            "first_mint_time": {"B": -0.0, "G": -0.0},
            "first_mint_tx": {"B": -0.0, "G": -0.0},
            "owner_address": {"B": -0.0, "G": -0.0},
            "owner_balance": {"B": -0.0, "G": -0.0},
            "ua_balance": {"B": -0.0, "G": -0.0},
            "update_authority_(ua)": {"B": -0.0, "G": -0.0}
        }
    }

    max_score = sum(
        abs(weight["B"]) + abs(weight["G"])
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
        score_text = f"\n{"🟢" if security_score >= threshold else "🔴"} {security_score:.2f}%"

        if data["security"]["c"]:
            security_info += "\n⚠️⚠️ <b>Critical Security Risks:</b> ⚠️⚠️"
            for issue, details in data["security"]["c"].items():
                if details["b"]:
                    security_info += f"\n<u>BirdEye - </u> {issue}: {details['b']}"
                if details["g"]:
                    security_info += f"\n<u>GoPlus - </u> {issue}: {details['g']}"

        if data["security"]["h"]:
            security_info += "\n⚠️ <b>High Security Risks:</b> ⚠️"
            for issue, details in data["security"]["h"].items():
                if details["b"]:
                    security_info += f"\n<u>BirdEye - </u> {issue}: {details['b']}"
                if details["g"]:
                    security_info += f"\n<u>GoPlus - </u> {issue}: {details['g']}"

    return f"""
🌱 <b>Token: </b><a href="https://dexscreener.com/solana/{data["address"]}">{data["token"]}: {data["description"]}</a>
💵 <b>Price: </b>${number_to_string(data["price"])}
🕛 <b>Age: </b>{from_minutes(data["age"])}
🛒 <b>Sells: </b>{data["sells"]}
📊 <b>Volume: </b>${number_to_string(data["volume"])}
👥 <b>Makers: </b>{data["makers"]}
🕛 <b>5m Change: </b><i>{number_to_string(data["5m_change"]) if data["5m_change"] is not None else "-"}{"%" if data["5m_change"] is not None else ""}</i>
🕛 <b>1h Change: </b><i>{number_to_string(data["1h_change"]) if data["1h_change"] is not None else "-"}{"%" if data["1h_change"] is not None else ""}</i>
🕛 <b>6h Change: </b><i>{number_to_string(data["6h_change"]) if data["6h_change"] is not None else "-"}{"%" if data["6h_change"] is not None else ""}</i>
🕛 <b>24h Change: </b><i>{number_to_string(data["24h_change"]) if data["24h_change"] is not None else "-"}{"%" if data["24h_change"] is not None else ""}</i>
💧 <b>Liquidity: </b>${number_to_string(data["liquidity"])}
💰 <b>Market Cap: </b>${number_to_string(data["market_cap"])}

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
