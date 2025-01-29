from os import getenv
from pathlib import Path
from random import uniform
from time import time
from typing import Dict

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumbase import SB

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
user_data_dir = getenv("USER_DATA_DIR")


def check_security_risks(sb, token_name: str, url="https://www.birdeye.so/") -> Dict:
    """Check security risks for a given token on Birdeye using SeleniumBase."""

    try:
        sb.driver.get(url)

        sb.driver.execute_script("document.body.style.zoom='50%'")
        sb.driver.set_window_size(1920, 1080)

        sb.click(r"div.w-full.bg-transparent > span")
        sb.sleep(2)

        search_input = sb.wait_for_element("div.border-b.bg-neutral-50 input", timeout=10)

        for char in token_name:
            search_input.send_keys(char)
            sb.sleep(uniform(0.05, 0.1))

        search_input.send_keys(Keys.RETURN)

        start_time = time()
        while "token" not in sb.get_current_url():
            sb.sleep(.5)
            if time() - start_time > 3:
                print("Timeout: URL did not change to include 'token'")
                break

        if "token" not in sb.get_current_url():
            sb.wait_for_element_clickable("table tbody tr:first-child td:first-child a", timeout=3)
            sb.click("table tbody tr:first-child td:first-child a")
            sb.sleep(2)

        security_url = sb.get_current_url() + "&tab=security"
        sb.driver.get(security_url)

        security_content = sb.wait_for_element("div.mt-4.space-y-1")

        sb.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", security_content)

        security_data = {
            "c": {},
            "h": {},
            "m": {},
            "n": {},
        }

        risk_sections = security_content.find_elements(By.CLASS_NAME, "divide-y")

        for section in risk_sections:
            if "hidden" in section.get_attribute("class"):
                continue

            border_class = section.get_attribute("class")
            if "border-l-destructive" in border_class:
                risk_level = "c"
            elif "border-l-primary" in border_class:
                risk_level = "h"
            elif "border-l-pending" in border_class:
                risk_level = "m"
            elif "border-l-neutral-700" in border_class:
                risk_level = "n"
            else:
                continue

            grid_items = section.find_elements(By.CLASS_NAME, "grid-cols-3")
            for item in grid_items:
                if "hidden" in item.get_attribute("class"):
                    continue

                title_elem = item.find_element(By.CSS_SELECTOR, "div.flex.gap-1 > div.flex-1")
                title = title_elem.text.lower()

                cells = item.find_elements(By.CSS_SELECTOR, "div.flex.px-2")
                birdeye_data = None if cells[0].text == "N/A" else cells[0].text
                goplus_data = None if cells[1].text == "N/A" else cells[1].text

                security_data[risk_level][title] = {
                    "b": birdeye_data,
                    "g": goplus_data
                }

        return security_data

    except Exception as e:
        print(f"Error checking security for {token_name}: {str(e)}")
        return {
            "c": {},
            "h": {},
            "m": {},
            "n": {},
            "error": str(e)
        }


def should_post_token(security_data: Dict) -> bool:
    """
    Determine if a token should be posted based on security information.
    Add your specific security criteria here.
    """

    return security_data["score"] > .9


if __name__ == "__main__":
    with SB(uc=True, test=True, headless=False, user_data_dir=user_data_dir) as sb:
        try:
            test_token = "SOL/USDC"
            security_info = check_security_risks(sb, test_token)
            print(f"Security info for {test_token}:")
            print(security_info)
            print(f"Should post: {should_post_token(security_info)}")
        except Exception as e:
            print(f"Error when checking security: {str(e)}")
        finally:
            pass
