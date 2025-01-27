from os import getenv
from pathlib import Path
from time import sleep
from typing import Dict

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from bot.utils import setup_chrome_driver

dotenv_path = Path(r"..\..\.env")
load_dotenv(dotenv_path=dotenv_path)
user_data_dir = getenv("USER_DATA_DIR")


def check_security_risks(driver, token_name: str) -> Dict:
    """
    Check security risks for a given token on Birdeye.

    Args:
        driver: Selenium WebDriver instance
        token_name: Name of the token to search for

    Returns:
        Dict containing security risk information
    """
    try:
        # Navigate to Birdeye
        driver.get("https://www.birdeye.so/")

        # Wait for and click the search box
        # search_button = WebDriverWait(driver, 20).until(
        #     # ec.element_to_be_clickable((By.CSS_SELECTOR,
        #     #                             "div.w-full.bg-transparent.p-[7px].text-subtitle-regular-14.transition-colors"
        #     #                             ".file\\:border-0.placeholder\\:text-neutral-400.focus\\:border-input-hover"
        #     #                             ".focus-visible\\:outline-none.disabled\\:pointer-events-none.disabled\\:opacity-50"
        #     #                             ".h-10.group.relative.hidden.max-w-\\[500px\\].cursor-pointer.gap-1.rounded"
        #     #                             ".border.pr-12.lg\\:flex.border-primary.text-neutral-500.hover\\:border-primary-400"))
        #
        # #     body > div:nth-child(3) > header.hidden.items-center.justify-between.gap-6.border-b.p-4.xl\:flex > div.flex.grow.
        #     #     justify-center.space-x-2.lg\:space-x-4 > div > div.w-full.bg-transparent.p-\[7px\].text-subtitle-regular-14.
        #     #     transition-colors.file\:border-0.placeholder\:text-neutral-400.focus\:border-input-hover.focus-visible\
        #     #     :outline-none.disabled\:pointer-events-none.disabled\:opacity-50.h-10.group.relative.hidden.max-w-\[500px\].
        #     #     cursor-pointer.gap-1.rounded.border.pr-12.lg\:flex.border-primary.text-neutral-500.hover\:border-primary-400 > span
        # )
        # search_button.click()

        search_area = WebDriverWait(driver, 20).until(
            ec.presence_of_element_located((By.CSS_SELECTOR,
                                            "div.flex.grow.justify-center.space-x-2.lg\\:space-x-4 div"))
        )
        search_area.click()

        # Wait for and fill the search input
        search_input = WebDriverWait(driver, 20).until(
            ec.presence_of_element_located((By.CSS_SELECTOR,
                                            "div.border-b.bg-neutral-50 input"))
        )
        search_input.send_keys(token_name)
        # search_input.send_keys(Keys.RETURN)

        # press enter

        sleep(2)

        search_input.send_keys(Keys.RETURN)

        # Wait for URL change and modify it to go directly to security tab
        WebDriverWait(driver, 20).until(
            lambda driver: "token" in driver.current_url
        )
        security_url = driver.current_url + "&tab=security"
        driver.get(security_url)

        # Wait for security content to load
        import re  # Regular expression
        security_content = WebDriverWait(driver, 20).until(
            # ec.presence_of_element_located((By.CSS_SELECTOR,
            #                                 "#radix-\\:r51\\:-content-security > div.mt-4.space-y-1"))

            # radix-\:r*ANY SYMBOLS WITH ANY LEN*\:-content-security > div.mt-4.space-y-1


            ec.presence_of_element_located((By.CSS_SELECTOR,"div.mt-4.space-y-1"))
        )

        # Initialize security data structure
        security_data = {
            "c": {},  # Critical
            "h": {},  # High risk
            "m": {},  # Medium risk
            "n": {}  # Neutral
        }

        # Find all risk sections
        risk_sections = security_content.find_elements(By.CLASS_NAME, "divide-y")

        for section in risk_sections:
            # Skip hidden sections
            if "hidden" in section.get_attribute("class"):
                continue

            # Determine risk level from border class
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

            # Process grid items in the section
            grid_items = section.find_elements(By.CLASS_NAME, "grid-cols-3")
            for item in grid_items:
                if "hidden" in item.get_attribute("class"):
                    continue

                # Get item title
                title_elem = item.find_element(By.CSS_SELECTOR, "div.flex-1")
                title = title_elem.text.lower()

                # Get Birdeye and Goplus data
                cells = item.find_elements(By.CSS_SELECTOR, "div.flex.justify-center")
                birdeye_data = None if cells[0].text == "N/A" else cells[0].text
                goplus_data = None if len(cells) < 2 or cells[1].text == "N/A" else cells[1].text

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
    # Test functionality
    driver = setup_chrome_driver(user_data_dir)
    try:
        test_token = "SOL/USDC"  # Example token
        security_info = check_security_risks(driver, test_token)
        print(f"Security info for {test_token}:")
        print(security_info)
        print(f"Should post: {should_post_token(security_info)}")
    finally:
        driver.quit()
