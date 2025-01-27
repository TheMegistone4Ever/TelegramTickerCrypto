from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from telebot import TeleBot

from bot.utils import (to_minutes, from_minutes, transform_token, string_to_number, number_to_string,
                       avoid_tg_rate_limit, wait_dynamic_content)

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
BOT_TOKEN = getenv("BOT_TOKEN")
channel_id = getenv("CHANNEL_ID")
user_data_dir = getenv("USER_DATA_DIR")
bot = TeleBot(BOT_TOKEN)


def setup_chrome_driver():
    """Setup Chrome driver with your existing profile"""

    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    chrome_options.add_argument("--profile-directory=Default")
    return webdriver.Chrome(options=chrome_options)


def scrape_dexscreener_data(driver):
    """Scrape data from DexScreener"""

    url = "https://dexscreener.com/solana?rankBy=pairAge&order=asc&minLiq=2000&minAge=3"
    driver.get(url)

    WebDriverWait(driver, 20).until(
        ec.presence_of_element_located((By.CLASS_NAME, "ds-dex-table-th"))
    )

    wait_dynamic_content()

    pairs = driver.find_elements(By.CSS_SELECTOR, "a.ds-dex-table-row")

    pairs_data = []
    for pair in pairs[1:]:
        try:
            columns = pair.find_elements(By.CSS_SELECTOR, "div.ds-table-data-cell")
            if len(columns) < 8:
                continue
            pair_data = {
                "token": transform_token(columns[0].text),
                "link": pair.get_attribute("href").split("https://dexscreener.com/solana/")[-1],
                "price": float(columns[1].text.strip().replace("$", "").replace(",", "")),
                "age": to_minutes(columns[2].text),
                "buys": int(columns[3].text.strip().replace(",", "")),
                "sells": int(columns[4].text.strip().replace(",", "")),
                "volume": string_to_number(columns[5].text),
                "makers": int(columns[6].text.strip().replace(",", "")),
                "5m_change": float(columns[7].text.strip().replace("%", "").replace(",", ".")) if len(
                    columns[7].text.strip().replace("%", "").replace(",", ".")) > 1 else None,
                "1h_change": float(columns[8].text.strip().replace("%", "").replace(",", ".")) if len(
                    columns[8].text.strip().replace("%", "").replace(",", ".")) > 1 else None,
                "6h_change": float(columns[9].text.strip().replace("%", "").replace(",", ".")) if len(
                    columns[9].text.strip().replace("%", "").replace(",", ".")) > 1 else None,
                "24h_change": float(columns[10].text.strip().replace("%", "").replace(",", ".")) if len(
                    columns[10].text.strip().replace("%", "").replace(",", ".")) > 1 else None,
                "liquidity": string_to_number(columns[11].text),
                "market_cap": string_to_number(columns[12].text),
            }
            pairs_data.append(pair_data)
        except (ValueError, IndexError) as e:
            print(f"Error processing pair: {e}")
            continue

    return pairs_data


def format_telegram_message(data):
    """Format data for Telegram message"""

    return f"""
🌱 <strong>Token: </strong><a href="https://dexscreener.com/solana/{data["link"]}">{data["token"]}</a>
💵 <strong>Price: </strong>${data["price"]}
🕛 <strong>Age: </strong>{from_minutes(data["age"])}
🛒 <strong>Sells: </strong>{data["sells"]}
📊 <strong>Volume: </strong>${number_to_string(data["volume"])}
👥 <strong>Makers: </strong>{data["makers"]}
🕛 <strong>5m Change: </strong><em>{data["5m_change"] if data["5m_change"] is not None else "-"}{"%" if data["5m_change"] is not None else ""}</em>
🕛 <strong>1h Change: </strong><em>{data["1h_change"] if data["1h_change"] is not None else "-"}{"%" if data["1h_change"] is not None else ""}</em>
🕛 <strong>6h Change: </strong><em>{data["6h_change"] if data["6h_change"] is not None else "-"}{"%" if data["6h_change"] is not None else ""}</em>
🕛 <strong>24h Change: </strong><em>{data["24h_change"] if data["24h_change"] is not None else "-"}{"%" if data["24h_change"] is not None else ""}</em>
💧 <strong>Liquidity: </strong>${number_to_string(data["liquidity"])}
💰 <strong>Market Cap: </strong>${number_to_string(data["market_cap"])}
"""


def main():
    driver = setup_chrome_driver()
    try:
        pairs_data = scrape_dexscreener_data(driver)

        for pair_data in pairs_data:
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
