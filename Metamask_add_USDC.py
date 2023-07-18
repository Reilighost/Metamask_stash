from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time
import random
import threading
from queue import Queue
import sys
import pandas as pd
from selenium.common.exceptions import NoSuchElementException
import configparser

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


networks = [
    ("//*[contains(text(), 'Arbitrum One')]", "Arbitrum", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"),
    ("//*[contains(text(), 'Polygon Mainnet')]", "Polygon", "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"),
    ("//*[contains(text(), 'BNB Smart Chain (previously Binance Smart Chain Mainnet)')]", "BNB", "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"),
    ("//*[contains(text(), 'Optimism')]", "Optimism", "0x7f5c764cbc14f9669b88837ca1490cca17c31607"),
    ("//*[contains(text(), 'Fantom Opera')]", "Fantom", "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75"),
    ("//*[contains(text(), 'Avalanche Network C-Chain')]", "Avalanche", "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"),
]

def click_if_exists(driver, locator):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, locator))
            )
            element.click()
            time.sleep(random.uniform(0.7, 1.4))
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
        click_if_exists(driver, '/html/body/div[2]/div/div/section/div[1]/div/button')
        assets = '/html/body/div[1]/div/div[3]/div/div/div/div[3]/ul/li[1]/button'
        click_if_exists(driver, assets)

        for network_xpath, network_name, contract_address in networks:
            click_if_exists(driver, "/html/body/div[1]/div/div[1]/div/div[2]/div/div/span")
            click_if_exists(driver, network_xpath)
            click_if_exists(driver, '/html/body/div[2]/div/div/section/div[3]/button')
            click_if_exists(driver, "/html/body/div[1]/div/div[3]/div/div/div/div[3]/div[2]/div[3]/div[2]/a")
            contract_input_xpath = "/html/body/div[1]/div/div[3]/div/div[2]/div[1]/div/div[2]/div/input"
            contract_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, contract_input_xpath)))
            contract_input.send_keys(contract_address)
            time.sleep(5)
            click_if_exists(driver, "/html/body/div[1]/div/div[3]/div/div[2]/div[2]/footer/button")
            click_if_exists(driver, "/html/body/div[1]/div/div[3]/div/div[3]/footer/button[2]")


        time.sleep(1)
        print(f"Done for profile № {idx}")
        driver.get(close_url)
    except Exception:
        print(f"failed for profile № {idx}!")
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