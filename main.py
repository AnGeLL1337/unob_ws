import json
import re
import uuid
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import asyncio
import aiohttp
import aiofiles

CACHE_DIR = 'html_cache'


def generate_uuid() -> str:
    return str(uuid.uuid4())


def remove_keyword(string, keyword):
    return string.replace(keyword, "")


def remove_chars(string, chars):
    return ''.join([char for char in string if char not in chars])


def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def get_cache_path(url):
    filename = url.split('/')[-1] + '.html'
    return os.path.join(CACHE_DIR, filename)


def fetch_page_sync(url, driver):
    cache_path = get_cache_path(url)
    if os.path.exists(cache_path):
        print(f"Using cached page: {url}")
        with open(cache_path, 'r', encoding='utf-8') as file:
            return file.read()

    print(f"Fetching page: {url}")
    driver.get(url)
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body')))  # Ensure the page has loaded
    except Exception as e:
        print(f"Error during page load: {e}")

    page_source = driver.page_source

    with open(cache_path, 'w', encoding='utf-8') as file:
        file.write(page_source)

    return page_source


async def fetch_page_async(url, session):
    cache_path = get_cache_path(url)
    if os.path.exists(cache_path):
        print(f"Using cached page: {url}")
        async with aiofiles.open(cache_path, 'r', encoding='utf-8') as file:
            return await file.read()

    print(f"Fetching page: {url}")
    async with session.get(url) as response:
        page_source = await response.text()

    async with aiofiles.open(cache_path, 'w', encoding='utf-8') as file:
        await file.write(page_source)

    return page_source


def parse_data(html_content) -> tuple:
    data = BeautifulSoup(html_content, 'html.parser')
    elems = data.find_all("div", class_="col text-end")
    print(f"Number of elements: {len(elems)}")
    num_elems = len(elems) - 1

    if num_elems >= 13:
        return (
            elems[0].text.strip(),
            elems[1].text.strip() + " / " + elems[2].text.strip(),
            elems[3].text.strip(),
            elems[4].text.strip(),
            elems[5].text.strip(),
            elems[6].text.strip(),
            elems[7].text.strip(),
            elems[8].text.strip(),
            elems[9].text.strip(),
            elems[10].text.strip(),
            elems[11].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )
    elif num_elems == 12:
        return (
            elems[0].text.strip(),
            elems[1].text.strip(),
            elems[2].text.strip(),
            elems[3].text.strip(),
            elems[4].text.strip(),
            elems[5].text.strip(),
            elems[6].text.strip(),
            elems[7].text.strip(),
            elems[8].text.strip(),
            elems[9].text.strip(),
            elems[10].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )
    elif num_elems == 11:
        return (
            elems[0].text.strip(),
            elems[1].text.strip(),
            None,
            elems[2].text.strip(),
            elems[3].text.strip(),
            elems[4].text.strip(),
            elems[5].text.strip(),
            elems[6].text.strip(),
            elems[7].text.strip(),
            elems[8].text.strip(),
            elems[9].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )
    else:
        return (
            elems[0].text.strip(),
            None,
            None,
            elems[1].text.strip(),
            elems[2].text.strip(),
            elems[3].text.strip(),
            elems[4].text.strip(),
            elems[5].text.strip(),
            elems[6].text.strip(),
            elems[7].text.strip(),
            elems[8].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )


def initialize_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)


def get_id(url, driver):
    print(f"Getting ID from URL: {url}")
    driver.get(url)
    driver.get(url)  # Load the URL twice to handle the popup
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body')))  # Ensure the page has loaded
    except Exception as e:
        print(f"Error during page load: {e}")
    ids = driver.page_source
    return ids


def login(driver, url, username, password):
    print(f"Logging in to URL: {url}")
    driver.get(url)
    driver.get(url)  # Load the URL twice to handle the popup
    wait = WebDriverWait(driver, 20)  # Increased timeout to 20 seconds

    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if iframes:
        driver.switch_to.frame(iframes[0])

    try:
        username_field = wait.until(EC.presence_of_element_located((By.ID, "floatingInput")))
        password_field = wait.until(EC.presence_of_element_located((By.ID, "floatingPassword")))
    except Exception as e:
        print(f"Exception occurred: {e}")
        driver.quit()
        raise e

    username_field.send_keys(username)
    password_field.send_keys(password)
    submit = driver.find_element(By.NAME, "button")
    submit.click()


def read_existing_systemdata():
    if os.path.exists("systemdata.json"):
        with open("systemdata.json", "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def read_existing_external_ids():
    if os.path.exists("external_ids.json"):
        with open("external_ids.json", "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def write_systemdata_entry(entry):
    data = read_existing_systemdata()
    if not any(d["ID"] == entry["ID"] for d in data):
        data.append(entry)
        with open("systemdata.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def write_external_ids_entry(entry):
    data = read_existing_external_ids()
    if not any(d["external_id"] == entry["external_id"] for d in data):
        data.append(entry)
        with open("external_ids.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def main_sync():
    ensure_cache_dir()

    with open("personal.json") as f:
        personal = json.load(f)
    login1Url = personal["login1Url"]
    login2Url = personal["login2Url"]
    url1 = personal['url1']
    url2 = personal['url2']
    user = personal['user']
    password = personal['password']

    driver = initialize_driver()
    login(driver, login1Url, user, password)

    ids = get_id(url1, driver)

    pattern = re.compile(r'"teachers":(.*?)],"classrooms"')
    matches = pattern.findall(ids)

    if matches:
        userID = matches[0].strip()
        print("Match found.")
    else:
        print("No match found.")
        return  # Exit the function if no match is found

    userIDSplits = userID.split("},{")

    with open("ids.txt", "w") as f:
        for userIDSplit in userIDSplits:
            user_id, user_surname, user_name = userIDSplit.split(",")
            user_id = remove_keyword(user_id, '"id":')
            user_id = remove_chars(user_id, '[{')
            f.write(user_id + "\n")

    print("IDs have been written.")

    login(driver, login2Url, user, password)
    print("Logged in, fetching data.")

    external_ids_data = read_existing_external_ids()

    with open("ids.txt", "r") as f:
        for line in f:
            value = line.strip()
            finalurl = url2 + value
            page_source = fetch_page_sync(finalurl, driver)
            print(f"Value: {value}, finalurl: {finalurl}, page_source: {page_source[:100]}")
            data_tuple = parse_data(page_source)

            existing_entry = next((item for item in external_ids_data if item["external_id"] == value), None)
            if existing_entry:
                entry_id = existing_entry["id"]
            else:
                entry_id = generate_uuid()
                new_external_entry = {
                    "id": entry_id,
                    "name": data_tuple[0],
                    "name_en": data_tuple[0],
                    "urlformat": finalurl,
                    "external_id": value
                }
                write_external_ids_entry(new_external_entry)
                external_ids_data.append(new_external_entry)  # Add new entry to the list

            data_dict = {
                "ID": entry_id,
                "Jméno": data_tuple[0],
                "Titul před / za": data_tuple[1],
                "Hodnosť / Titul za": data_tuple[2],
                "Katedra": data_tuple[3],
                "Email": data_tuple[4],
                "Telefon": data_tuple[5],
                "Mobil": data_tuple[6],
                "Datová schránka": data_tuple[7],
                "Areál": data_tuple[8],
                "Budova/Patro/Místnosť": data_tuple[9],
                "Fakulta": data_tuple[10],
                "Seznam vyučovaných skupin": data_tuple[11]
            }
            write_systemdata_entry(data_dict)

    print("Teachers have been written.")
    driver.quit()


async def main_async():
    ensure_cache_dir()

    with open("personal.json") as f:
        personal = json.load(f)
    url2 = personal['url2']

    external_ids_data = await read_existing_external_ids_async()

    async with aiohttp.ClientSession() as session:
        async with aiofiles.open("ids.txt", "r") as f:
            async for line in f:
                value = line.strip()
                finalurl = url2 + value
                page_source = await fetch_page_async(finalurl, session)
                data_tuple = parse_data(page_source)

                existing_entry = next((item for item in external_ids_data if item["external_id"] == value), None)
                if existing_entry:
                    entry_id = existing_entry["id"]
                else:
                    entry_id = generate_uuid()
                    new_external_entry = {
                        "id": entry_id,
                        "name": data_tuple[0],
                        "name_en": data_tuple[0],
                        "urlformat": finalurl,
                        "external_id": value
                    }
                    await write_external_ids_entry_async(new_external_entry)
                    external_ids_data.append(new_external_entry)  # Add new entry to the list

                data_dict = {
                    "ID": entry_id,
                    "Jméno": data_tuple[0],
                    "Titul před / za": data_tuple[1],
                    "Hodnosť / Titul za": data_tuple[2],
                    "Katedra": data_tuple[3],
                    "Email": data_tuple[4],
                    "Telefon": data_tuple[5],
                    "Mobil": data_tuple[6],
                    "Datová schránka": data_tuple[7],
                    "Areál": data_tuple[8],
                    "Budova/Patro/Místnosť": data_tuple[9],
                    "Fakulta": data_tuple[10],
                    "Seznam vyučovaných skupin": data_tuple[11]
                }
                await write_systemdata_entry_async(data_dict)

    print("Teachers have been written.")


async def read_existing_systemdata_async():
    if os.path.exists("systemdata.json"):
        async with aiofiles.open("systemdata.json", "r", encoding="utf-8") as f:
            try:
                content = await f.read()
                return json.loads(content)
            except json.JSONDecodeError:
                return []
    return []


async def write_systemdata_entry_async(entry):
    data = await read_existing_systemdata_async()
    if not any(d["ID"] == entry["ID"] for d in data):
        data.append(entry)
        async with aiofiles.open("systemdata.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))


async def read_existing_external_ids_async():
    if os.path.exists("external_ids.json"):
        async with aiofiles.open("external_ids.json", "r", encoding="utf-8") as f:
            try:
                content = await f.read()
                return json.loads(content)
            except json.JSONDecodeError:
                return []
    return []


async def write_external_ids_entry_async(entry):
    data = await read_existing_external_ids_async()
    if not any(d["external_id"] == entry["external_id"] for d in data):
        data.append(entry)
        async with aiofiles.open("external_ids.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    ensure_cache_dir()
    main_sync()
    asyncio.run(main_async())
