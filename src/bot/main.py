from dataclasses import replace
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from seleniumbase import SB
from telebot import TeleBot

from birdeye import check_security_risks, should_post_token
from gemini.assistant import CryptoAIProcessor
from models import PairData
from utils import (transform_token, string_to_number, as_number, get_solana_address, to_minutes,
                   wait_for_url_change, calculate_token_score, format_telegram_message)

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
BOT_TOKEN = getenv("BOT_TOKEN")
channel_id = getenv("CHANNEL_ID")
user_data_dir = getenv("USER_DATA_DIR")
gemini_api_key = getenv("GEMINI_API_KEY")
bot = TeleBot(BOT_TOKEN)
crypto_ai = CryptoAIProcessor(
    model_name="models/gemini-2.0-flash-thinking-exp-01-21",
    api_key=gemini_api_key,
    database_path="crypto_pairs.csv"
)
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

            crypto_ai.save_pair_data(pairs_data)

            for pair_data in pairs_data:
                security_data = check_security_risks(sb, pair_data.token)
                score = calculate_token_score(security_data)
                pair_data = replace(pair_data, security=replace(security_data, score=score))

                if should_post_token(pair_data.security):
                    msg = format_telegram_message(pair_data)
                    bot.send_message(channel_id, msg, parse_mode="HTML")
        finally:
            pass


@bot.message_handler(commands=["start", "help", "info", "trends", "support"])
def handle_commands(message):
    """Handle bot commands using AI assistant"""
    command = message.text[1:]
    response = crypto_ai.handle_command(command)
    bot.send_message(message.chat.id, response, parse_mode="HTML")


@bot.message_handler()
def handle_messages(message):
    """Handle messages with two-stage processing"""
    technical_output, user_response = crypto_ai.process_message(message.text)

    if technical_output:
        print(f"{technical_output = }")

    if user_response:
        print(f"{user_response = }")
        bot.reply_to(message, user_response)


if __name__ == "__main__":
    """Run the bot."""

    print("Starting bot...")
    # main()
    bot.polling(none_stop=True)
