from os import getenv
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from bot.utils import setup_chrome_driver, wait_static_content

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
user_data_dir = getenv("USER_DATA_DIR")


def check_security_risks(driver, token_name: str, url="https://www.birdeye.so/") -> Dict:
    """Check security risks for a given token on Birdeye."""

    try:
        driver.get(url)

        search_area = WebDriverWait(driver, 20).until(
            ec.element_to_be_clickable((By.CSS_SELECTOR,
                                        "div.flex.grow.justify-center.space-x-2.lg\\:space-x-4 div"))
        )
        search_area.click()

        wait_static_content()

        search_input = WebDriverWait(driver, 20).until(
            ec.presence_of_element_located((By.CSS_SELECTOR,
                                            "div.border-b.bg-neutral-50 input"))
        )
        search_input.send_keys(token_name)

        wait_static_content()

        search_input.send_keys(Keys.RETURN)

        WebDriverWait(driver, 20).until(
            lambda driver: "token" in driver.current_url
        )
        security_url = driver.current_url + "&tab=security"
        driver.get(security_url)

        security_content = WebDriverWait(driver, 20).until(
            ec.presence_of_element_located((By.CSS_SELECTOR, "div.mt-4.space-y-1"))
        )

        security_data = {
            "c": {},
            "h": {},
            "m": {},
            "n": {}
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

                title_elem = item.find_element(By.CSS_SELECTOR, "div.flex-1")
                title = title_elem.text.lower()

                cells = item.find_elements(By.CSS_SELECTOR, "div.flex.justify-center")
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


def should_post_token(security_info: Dict) -> bool:
    """
    Determine if a token should be posted based on security information.
    Add your specific security criteria here.
    """
    # # Example criteria - customize based on your needs
    # if security_info.get("error"):  # If there was an error checking security
    #     return False
    #
    # if security_info["c"]:  # If any critical issues
    #     return False
    #
    # # Count high risk issues
    # high_risk_count = len(security_info["h"])
    # if high_risk_count > 2:  # If more than 2 high risk issues
    #     return False

    return True


if __name__ == "__main__":
    driver = setup_chrome_driver(user_data_dir)
    try:
        test_token = "SOL/USDC"
        security_info = check_security_risks(driver, test_token)
        print(f"Security info for {test_token}:")
        print(security_info)
        print(f"Should post: {should_post_token(security_info)}")
    except Exception as e:
        print(f"Error when checking security: {str(e)}")
    finally:
        driver.quit()
