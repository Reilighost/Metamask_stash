import requests
import threading
import time
import random
import string
import sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from queue import Queue
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
seed_phrases = df['seed_phrase'].tolist()
lock = threading.Lock()

def generate_password(length):
    if length < 8:
        print("Password length should be at least 8")
        return None

    all_characters = string.ascii_letters + string.digits + string.punctuation

    password = []
    password.append(random.choice(string.ascii_lowercase))  # Ensures at least one lowercase letter
    password.append(random.choice(string.ascii_uppercase))  # Ensures at least one uppercase letter
    password.append(random.choice(string.digits))  # Ensures at least one number
    password.append(random.choice(string.punctuation))  # Ensures at least one special character

    for i in range(length - 4):  # Remaining characters can be anything
        password.append(random.choice(all_characters))

    random.shuffle(password)  # Shuffles the characters around

    password_string = "".join(password)  # Join list into a string
    return password_string
def click_if_exists(driver, locator):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 30).until(
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
        seed_phrase = seed_phrases[idx - 1]
        process_profile(idx, profile_id, seed_phrase)
        task_queue.task_done()
def process_profile(idx, profile_id, seed_phrase):
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
    time.sleep(13.37)
    for tab in driver.window_handles:
        if tab != initial_window_handle:
            driver.switch_to.window(tab)
            driver.close()
    driver.switch_to.window(initial_window_handle)
    driver.get(metamask_url)
    try:
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div/button')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div/div[5]/div[1]/footer/button[2]')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div[2]/div/div[2]/div[1]/button')
        seed_words = seed_phrase.split()
        for i, word in enumerate(seed_words):
            seed_word_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="import-srp__srp-word-{i}"]')))
            seed_word_input.send_keys(word)

        password = str(generate_password(32))
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))
        )
        password_input.send_keys(password)
        password_confirm = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="confirm-password"]'))
        )
        password_confirm.send_keys(password)
        with lock:
            df.loc[df.index[idx - 1], 'passwords'] = password
            df.to_excel(DATA, index=False)
        click_if_exists(driver, '//*[@id="create-new-vault__terms-checkbox"]')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/div[2]/form/button')
        click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div/button')

        click_if_exists(driver, '//*[@id="tippy-tooltip-2"]/div/div[2]/div/div[1]/button')
        driver.refresh()
        click_if_exists(driver, '//*[@id="popover-content"]/div/div/section/div[1]/div/button')
        driver.refresh()
        click_if_exists(driver, '//*[@id="popover-content"]/div/div/section/div[1]/div/button')
        print(f"Done for profile {idx}")
        time.sleep(3)
        requests.get(close_url)
    except Exception as e:
        print(f"L: {e}")
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
