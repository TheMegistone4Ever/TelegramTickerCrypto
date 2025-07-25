from os import getenv
from pathlib import Path
from random import uniform
from typing import Dict

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumbase import SB

from bot.utils import wait_for_url_change, define_risk_level
from models import SecurityData, RiskLevel

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
user_data_dir = getenv("USER_DATA_DIR")


def check_security_risks(sb, token_name: str, url="https://www.birdeye.so/") -> SecurityData:
    """Check security risks for a given token on Birdeye using SeleniumBase."""

    try:
        sb.driver.get(url)

        sb.driver.execute_script("document.body.style.zoom=\"50%\"")
        sb.driver.set_window_size(1920, 1080)

        sb.click(r"div.w-full.bg-transparent > span")
        sb.sleep(2)

        search_input = sb.wait_for_element("div.border-b.bg-neutral-50 input", timeout=10)
        search_input.clear()

        for char in token_name.split("/")[0]:
            search_input.send_keys(char)
            sb.sleep(uniform(0.05, 0.1))

        sb.wait_for_element_clickable("div.flex.items-center.justify-center.gap-4 > div > div > div", timeout=10)
        sb.click("div.flex.items-center.justify-center.gap-4 > div > div > div")
        sb.sleep(2)

        sb.wait_for_element_clickable("div[data-value='solana']", timeout=10)
        sb.click("div[data-value='solana']")
        sb.sleep(2)

        search_input.send_keys(Keys.RETURN)

        wait_for_url_change(sb, "token", timeout=3)

        url = sb.get_current_url()
        if "token" not in url:
            css_selector = "div > div > div > div:first-child div table tbody tr:first-child td:first-child a"
            sb.wait_for_element_clickable(css_selector, timeout=10)
            url = sb.find_element(css_selector).get_attribute("href")

        sb.driver.get(url + "&tab=security")

        wait_for_url_change(sb, "security", timeout=5, error_type="raise")

        sb.wait_for_element_clickable("div > div > div > div.col-span-11.py-8.lg\\:col-span-5 > div > button",
                                      timeout=5)
        sb.click("div > div > div > div.col-span-11.py-8.lg\\:col-span-5 > div > button")

        security_content = sb.wait_for_element("div.mt-4.space-y-1")

        sb.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: \"smooth\", block: \"center\", inline: \"center\"});",
            security_content)

        security_data: Dict[str, Dict[str, Dict[str, str]]] = {
            RiskLevel.CRITICAL.value[0]: {},
            RiskLevel.HIGH.value[0]: {},
            RiskLevel.MEDIUM.value[0]: {},
            RiskLevel.LOW.value[0]: {},
        }

        risk_sections = security_content.find_elements(By.CLASS_NAME, "divide-y")

        for section in risk_sections:
            if "hidden" in (border_class := section.get_attribute("class")):
                continue

            risk_level = define_risk_level(border_class)
            if not risk_level:
                continue

            grid_items = section.find_elements(By.CLASS_NAME, "grid-cols-3")
            for item in grid_items:
                if "hidden" in item.get_attribute("class"):
                    continue

                title_elem = item.find_element(By.CSS_SELECTOR, "div.flex.gap-1")
                title = title_elem.text.lower()

                cells = item.find_elements(By.CSS_SELECTOR, "div.flex.px-2")
                birdeye_data = cells[0].text if cells[0].text != "N/A" else None
                goplus_data = cells[1].text if cells[1].text != "N/A" else None

                security_data[risk_level.value][title] = {
                    "birdeye": birdeye_data,
                    "goplus": goplus_data
                }

        return SecurityData(**security_data)

    except Exception as e:
        print(f"Error checking security for {token_name}: {str(e)}")
        return SecurityData(c={}, h={}, m={}, n={}, error=str(e))


def should_post_token(security_data: SecurityData) -> bool:
    """
    Determine if a token should be posted based on security information.
    Add your specific security criteria here.
    """

    return security_data.score is not None and security_data.score > .9


if __name__ == "__main__":
    """Run a test to check security risks for a token."""

    with SB(uc=True, headless=False, user_data_dir=user_data_dir) as sb_main:
        try:
            test_token = "SOL/USDC"
            security_info = check_security_risks(sb_main, test_token)
            print(f"Security info for {test_token}:")
            print(security_info)
            print(f"Should post: {should_post_token(security_info)}")
        except Exception as exception:
            print(f"Error when checking security: {str(exception)}")
