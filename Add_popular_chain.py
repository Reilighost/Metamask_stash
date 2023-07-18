from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time
import sys
import configparser
import random
import pandas as pd
import threading
from queue import Queue
from selenium.common.exceptions import NoSuchElementException

config_path = 'config.ini'
config = configparser.ConfigParser()
config.read(config_path)

max_simultaneous_profiles = int(config['DEFAULT'].get('max_simultaneous_profiles'))
metamask_identificator = (config['DEFAULT'].get('metamask_identificator'))
metamask_url = f"chrome-extension:/{metamask_identificator}/home.html#"


start_idx = int(input("Enter the starting index of the profile range: "))
end_idx = int(input("Enter the ending index of the profile range: "))

DATA = "Data\profiles_data.xlsx"
df = pd.read_excel(DATA)
profile_ids = df['profile_id'].tolist()
passwords = df['passwords'].tolist()


def click_if_exists(driver, locator):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, locator))
            )
            element.click()
            time.sleep(random.uniform(1.3, 2.1))
            return True
        except TimeoutException:
            return False
        except StaleElementReferenceException:
            attempts += 1
            time.sleep(3)
    return False
def worker():
    while True:
        idx, profile_id = task_queue.get()
        if profile_id is None:
            break
        password = passwords[idx - 1]
        process_profile(idx, profile_id, password)
        task_queue.task_done()
def element_exists(driver, xpath):
    time.sleep(random.uniform(1.2, 1.7))
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        return True
    except NoSuchElementException:
        return False
def process_profile(idx, profile_id, password):

    open_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={profile_id}"
    close_url = f"http://local.adspower.net:50325/api/v1/browser/stop?user_id={profile_id}"
    resp = requests.get(open_url).json()

    if resp["code"] != 0:
        print(resp["msg"])
        print("Failed to start a driver")
        sys.exit()

    chrome_driver = resp["data"]["webdriver"]
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", resp["data"]["ws"]["selenium"])
    driver = webdriver.Chrome(service=Service(chrome_driver), options=chrome_options)
    initial_window_handle = driver.current_window_handle
    time.sleep(1.337)
    for tab in driver.window_handles:
        if tab != initial_window_handle:
            driver.switch_to.window(tab)
            driver.close()
    driver.switch_to.window(initial_window_handle)
    driver.get(metamask_url)
    try:
        password_input = '//*[@id="password"]'
        contract_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, password_input)))
        contract_input.send_keys(password)
        click_if_exists(driver, '//*[@id="app-content"]/div/div[3]/div/div/button')

        driver.get(f"chrome-extension://{metamask_identificator}/home.html#settings/networks/add-popular-custom-network")

        while element_exists(driver,
            '/html/body/div[1]/div/div[3]/div/div[2]/div[2]/div/div[2]/div[1]/div[2]/button') is True:
            click_if_exists(driver, '/html/body/div[1]/div/div[3]/div/div[2]/div[2]/div/div[2]/div[1]/div[2]/button')
            click_if_exists(driver, '/html/body/div[2]/div/div/section/div/div/div[2]/div/button[2]')
            click_if_exists(driver, '/html/body/div[2]/div/div/section/div/div/button[1]/h6')
            click_if_exists(driver, '/html/body/div[2]/div/div/section/div[3]/button')
            time.sleep(random.uniform(1.2, 1.7))
            driver.back()

        driver.get(metamask_url)
        click_if_exists(driver, "/html/body/div[1]/div/div[1]/div/div[2]/button")
        click_if_exists(driver, "/html/body/div[1]/div/div[3]/button[5]")
        click_if_exists(driver, "/html/body/div[1]/div/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[2]/div/div/select")
        click_if_exists(driver, "/html/body/div[1]/div/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[2]/div/div/select/option[10]")
        print(f"Done for profile {idx}")
        time.sleep(3)
        requests.get(close_url)
    except Exception:
        print(f"Failed for profile №{idx}!")
        driver.quit()
task_queue = Queue(max_simultaneous_profiles)
threads = []

for _ in range(max_simultaneous_profiles):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

for idx, profile_id in zip(range(start_idx, end_idx + 1), profile_ids[start_idx - 1:end_idx]):
    task_queue.put((idx, profile_id))
    time.sleep(5)

task_queue.join()

for _ in range(max_simultaneous_profiles):
    task_queue.put((None, None))

for t in threads:
    t.join()