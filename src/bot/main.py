from dataclasses import replace
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from seleniumbase import SB
from telebot import TeleBot

from birdeye import check_security_risks, should_post_token
from models import PairData
from utils import (transform_token, string_to_number, avoid_tg_rate_limit, as_number, get_solana_address, to_minutes,
                   wait_for_url_change, calculate_token_score, format_telegram_message)

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
BOT_TOKEN = getenv("BOT_TOKEN")
channel_id = getenv("CHANNEL_ID")
user_data_dir = getenv("USER_DATA_DIR")
bot = TeleBot(BOT_TOKEN)
MAX_ON_PAGE = 100


def scrape_dexscreener_data(sb, url="https://dexscreener.com/solana?rankBy=pairAge&order=asc&minLiq=2000&minAge=3"):
    """Scrape data from Dexscreener using SeleniumBase"""

    sb.driver.get(url)
    wait_for_url_change(sb, "solana", timeout=10)

    pairs_data = set()
    for i in range(MAX_ON_PAGE):
        if i == 3:
            break
        print(f"Processing pair {i + 1} of {MAX_ON_PAGE}")
        try:
            pair = sb.find_elements("a.ds-dex-table-row")[i]
            columns = pair.find_elements(By.CSS_SELECTOR, "div.ds-table-data-cell")

            if not columns or len(columns) < 13:
                continue

            token, description = transform_token(columns[0].text)
            pair_data = PairData(
                token=token,
                description=description,
                address=get_solana_address(pair.get_attribute("href")),
                price=string_to_number(columns[1].text),
                age=to_minutes(columns[2].text),
                buys=as_number(columns[3].text),
                sells=as_number(columns[4].text),
                volume=string_to_number(columns[5].text),
                makers=as_number(columns[6].text),
                five_min_change=string_to_number(columns[7].text) if len(columns[7].text) > 1 else None,
                one_hour_change=string_to_number(columns[8].text) if len(columns[8].text) > 1 else None,
                six_hour_change=string_to_number(columns[9].text) if len(columns[9].text) > 1 else None,
                twenty_four_hour_change=string_to_number(columns[10].text) if len(columns[10].text) > 1 else None,
                liquidity=string_to_number(columns[11].text),
                market_cap=string_to_number(columns[12].text),
            )
            pairs_data.add(pair_data)
        except (ValueError, IndexError) as e:
            print(f"Error processing pair: {e}")
            continue

    return pairs_data


def main():
    """Main function to run the bot."""

    with SB(uc=True, headless=False) as sb:
        try:
            pairs_data = scrape_dexscreener_data(sb)
            for pair_data in pairs_data:
                security_data = check_security_risks(sb, pair_data.token)
                score = calculate_token_score(security_data)
                pair_data = replace(pair_data, security=replace(security_data, score=score))

                if should_post_token(pair_data.security):
                    msg = format_telegram_message(pair_data)
                    bot.send_message(channel_id, msg, parse_mode="HTML")
                    avoid_tg_rate_limit()
        finally:
            pass


if __name__ == "__main__":
    """Run the bot."""

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
