import json
import re
import uuid
import os
from functools import cache

from async_lru import alru_cache
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import asyncio
import aiohttp
import aiofiles

CACHE_DIR = 'html_cache'
TYPEID_ID = "d00ec0b6-f27c-497b-8fc8-ddb4e2460717"


class DBWriter:
    def __init__(self, username="john.newbie@world.com", password="john.newbie@world.com"):
        self.username = username
        self.password = password
        self.token = None

    async def getToken(self):
        if self.token:
            return self.token

        keyurl = "http://localhost:33001/oauth/login3"
        async with aiohttp.ClientSession() as session:
            async with session.get(keyurl) as resp:
                keyJson = await resp.json()

            payload = {"key": keyJson["key"], "username": self.username, "password": self.password}
            async with session.post(keyurl, json=payload) as resp:
                tokenJson = await resp.json()
        self.token = tokenJson.get("token", None)
        return self.token

    async def queryGQL(self, query, variables):
        gqlurl = "http://localhost:33001/api/gql"
        token = await self.getToken()
        payload = {"query": query, "variables": variables}
        cookies = {'authorization': token}
        async with aiohttp.ClientSession() as session:
            async with session.post(gqlurl, json=payload, cookies=cookies) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"failed query \n{query}\n with variables {variables}".replace("'", '"'))
                    print(f"failed resp.status={resp.status}, text={text}")
                    raise Exception(f"Unexpected GQL response", text)
                else:
                    response = await resp.json()
                    return response

    async def queryGQL3(self, query, variables):
        times = 3
        result = None
        for i in range(times):
            try:
                result = await self.queryGQL(query=query, variables=variables)
                if result.get("errors", None) is None:
                    return result
                print(result)
            except Exception as e:
                print(f"Attempt {i+1} failed: {e}")
            await asyncio.sleep(10)

        raise Exception(f"Unable to run query={query} with variables {variables} for {times} times\n{result}".replace("'", '"'))

    @cache
    def GetQuery(self, tableName, queryType):
        assert queryType in ["read", "readp", "create", "update"], f"unknown queryType {queryType}"
        queryfile = f"./gqls/{tableName}/{queryType}.gql"
        with open(queryfile, "r", encoding="utf-8") as fi:
            lines = fi.readlines()
        query = ''.join(lines)
        assert query is not None, f"missing {queryType} query for table {tableName}"
        return query

    @alru_cache(maxsize=1024)
    async def asyncTranslateID(self, outer_id, type_id):
        query = 'query($type_id: ID!, $outer_id: String!){ result: internalId(typeidId: $type_id, outerId: $outer_id) }'
        jsonData = await self.queryGQL3(query=query, variables={"outer_id": outer_id, "type_id": type_id})
        data = jsonData.get("data", {"result": None})
        result = data.get("result", None)
        return result

    @alru_cache()
    async def getAllTypes(self):
        query = self.GetQuery(tableName="externalidtypes", queryType="readp")
        jsonData = await self.queryGQL3(query=query, variables={"limit": 1000})
        data = jsonData.get("data", {"result": None})
        result = data.get("result", None)
        assert result is not None, f"unable to get externalidtypes"
        asdict = {item["name"]: item["id"] for item in result}
        return asdict

    @alru_cache(maxsize=1024)
    async def getTypeId(self, typeName):
        alltypes = await self.getAllTypes()
        result = alltypes.get(typeName, None)
        assert result is not None, f"unable to get id of type {typeName}"
        return result

    async def registerID(self, inner_id, outer_id, type_id):
        mutation = '''
            mutation ($type_id: ID!, $inner_id: ID!, $outer_id: String!) {
                result: externalidInsert(
                    externalid: {innerId: $inner_id, typeidId: $type_id, outerId: $outer_id}
                ) {
                    msg
                    result: externalid {
                        id    
                        }
                    }
                }
        '''
        jsonData = await self.queryGQL3(query=mutation, variables={"inner_id": str(inner_id), "outer_id": outer_id, "type_id": str(type_id)})
        data = jsonData.get("data", {"result": {"msg": "fail"}})
        msg = data["result"]["msg"]
        if msg != "ok":
            print(f'register ID failed ({ {"inner_id": inner_id, "outer_id": outer_id, "type_id": type_id} })\n\tprobably already registered')
        else:
            print(f"registered {outer_id} for {inner_id} ({type_id})")
        return "ok"

    async def Read(self, tableName, variables, outer_id=None, outer_id_type_id=None):
        if outer_id:
            assert outer_id_type_id is not None, f"if outer_id ({outer_id}) defined, outer_id_type_id must be defined also"
            inner_id = await self.asyncTranslateID(outer_id=outer_id, type_id=outer_id_type_id)
            assert inner_id is not None, f"outer_id {outer_id} od type_id {outer_id_type_id} mapping failed on table {tableName}"
            variables = {**variables, "id": inner_id}

        queryRead = self.GetQuery(tableName, "read")
        response = await self.queryGQL3(query=queryRead, variables=variables)
        error = response.get("errors", None)
        assert error is None, f"error {error} during query \n{queryRead}\n with variables {variables}".replace("'", '"')
        data = response.get("data", None)
        assert data is not None, f"got no data during query \n{queryRead}\n with variables {variables}".replace("'", '"')
        result = data.get("result", None)
        return result

    async def Create(self, tableName, variables, outer_id=None, outer_id_type_id=None):
        queryType = "create"
        if outer_id:
            assert outer_id_type_id is not None, f"if outer_id ({outer_id}) defined, outer_id_type_id must be defined also"
            inner_id = await self.asyncTranslateID(outer_id=outer_id, type_id=outer_id_type_id)

            if inner_id:
                print(f"outer_id ({outer_id}) defined ({outer_id_type_id}) \t on table {tableName},\t going update")
                old_data = await self.Read(tableName=tableName, variables={"id": inner_id})
                if old_data is None:
                    print(f"found corrupted data, entity with id {inner_id} in table {tableName} is missing, going to create it")
                    variables = {**variables, "id": inner_id}
                else:
                    variables = {**old_data, **variables, "id": inner_id}
                    queryType = "update"
            else:
                print(f"outer_id ({outer_id}) undefined ({outer_id_type_id}) \t on table {tableName},\t going insert")
                registrationResult = await self.registerID(inner_id=variables["id"], outer_id=outer_id, type_id=outer_id_type_id)
                assert registrationResult == "ok", f"Something is really bad, ID registration failed"

        query = self.GetQuery(tableName, queryType)
        assert query is not None, f"missing {queryType} query for table {tableName}"
        response = await self.queryGQL3(query=query, variables=variables)
        data = response["data"]
        result = data["result"]
        result = result["result"]
        return result

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
    studium_skupinas = data.find(id="StudiumSkupinas")
    elems1 = studium_skupinas.find_all("div", class_="col text-end")
    kontaktni_informace = data.find(id="KontaktniInformace")
    elems2 = kontaktni_informace.find_all("div", class_="col text-end")
    vyucijici_clenstvi = data.find(id="VyucujiciClenstviCard")
    elems3 = vyucijici_clenstvi.find_all("div", class_="col text-end")
    num_elems = len(elems1) + len(elems2) + len(elems3) - 1
    if num_elems >= 13:
        return (
            elems1[0].text.strip(),
            elems1[1].text.strip() + " / " + elems1[2].text.strip(),
            elems1[3].text.strip(),
            elems1[4].text.strip(),
            elems2[0].text.strip(),
            elems2[1].text.strip(),
            elems2[2].text.strip(),
            elems2[3].text.strip(),
            elems2[4].text.strip(),
            elems2[5].text.strip(),
            elems3[0].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )
    elif num_elems == 12:
        return (
            elems1[0].text.strip(),
            elems1[1].text.strip(),
            elems1[2].text.strip(),
            elems1[3].text.strip(),
            elems2[0].text.strip(),
            elems2[1].text.strip(),
            elems2[2].text.strip(),
            elems2[3].text.strip(),
            elems2[4].text.strip(),
            elems2[5].text.strip(),
            elems3[0].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )
    elif num_elems == 11:
        return (
            elems1[0].text.strip(),
            elems1[1].text.strip(),
            None,
            elems1[2].text.strip(),
            elems2[0].text.strip(),
            elems2[1].text.strip(),
            elems2[2].text.strip(),
            elems2[3].text.strip(),
            elems2[4].text.strip(),
            elems2[5].text.strip(),
            elems3[0].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )
    else:
        return (
            elems1[0].text.strip(),
            None,
            None,
            elems1[1].text.strip(),
            elems2[0].text.strip(),
            elems2[1].text.strip(),
            elems2[2].text.strip(),
            elems2[3].text.strip(),
            elems2[4].text.strip(),
            elems2[5].text.strip(),
            elems3[0].text.strip(),
            [group.text.strip() for group in data.find_all("div", id="StudiumSkupina")]
        )


def initialize_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)


def get_id(url, driver):
    print(f"Getting IDs from URL: {url}")
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
            return json.load(f)
    return {"users": [], "externalids": []}

def write_systemdata(data):
    with open("systemdata.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def transform_users_to_systemdata(users):
    transformed_users = []
    for user in users:
        if "Jméno" in user:
            # Transform user if it has the "Jméno" key
            transformed_users.append({
                "id": user["ID"],
                "name": user["Jméno"].split()[1] if len(user["Jméno"].split()) > 1 else user["Jméno"],
                "surname": user["Jméno"].split()[0] if len(user["Jméno"].split()) > 1 else "",
                "email": user["Email"]
            })
        else:
            transformed_users.append(user)
    return transformed_users


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

    systemdata = read_existing_systemdata()
    users = systemdata["users"]
    externalids = systemdata.get("externalids", [])

    with open("ids.txt", "r") as f:
        for line in f:
            value = line.strip()
            finalurl = url2 + value
            page_source = fetch_page_sync(finalurl, driver)
            print(f"Value: {value}, finalurl: {finalurl}, page_source: {page_source[:100]}")
            data_tuple = parse_data(page_source)
            entry_id = generate_uuid()
            data_dict = {
                "ID": entry_id,  # Added UUID as ID
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
            if not any("ID" in d and d["ID"] == entry_id for d in users):
                users.append(data_dict)
                externalids.append({
                    "id": generate_uuid(),
                    "inner_id": entry_id,
                    "outer_id": value,
                    "typeid_id": TYPEID_ID
                })

    systemdata["users"] = transform_users_to_systemdata(users)
    systemdata["externalids"] = externalids

    write_systemdata(systemdata)

    print("Teachers have been written.")
    driver.quit()


async def main_async():
    ensure_cache_dir()

    with open("personal.json") as f:
        personal = json.load(f)
    url2 = personal['url2']

    systemdata = await read_existing_systemdata_async()
    users = systemdata["users"]
    externalids = systemdata.get("externalids", [])

    async with aiohttp.ClientSession() as session:
        async with aiofiles.open("ids.txt", "r") as f:
            async for line in f:
                value = line.strip()
                finalurl = url2 + value
                page_source = await fetch_page_async(finalurl, session)
                data_tuple = parse_data(page_source)
                entry_id = generate_uuid()
                data_dict = {
                    "ID": entry_id,  # Added UUID as ID
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
                if not any("ID" in d and d["ID"] == entry_id for d in users):
                    users.append(data_dict)
                    externalids.append({
                        "id": generate_uuid(),
                        "inner_id": entry_id,
                        "outer_id": value,
                        "typeid_id": TYPEID_ID
                    })

    systemdata["users"] = transform_users_to_systemdata(users)
    systemdata["externalids"] = externalids

    await write_systemdata_async(systemdata)

    print("Teachers have been written.")


async def read_existing_systemdata_async():
    if os.path.exists("systemdata.json"):
        async with aiofiles.open("systemdata.json", "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    return {"users": [], "externalids": []}

async def write_systemdata_async(data):
    async with aiofiles.open("systemdata.json", "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))


async def db_writer_async():
    with open("systemdata.json", "r", encoding="utf-8") as f:
        systemdata = json.load(f)

    users = systemdata["users"]
    externalids = systemdata["externalids"]

    db_writer = DBWriter()

    for user in users:
        user["id"] = user["id"]
        await db_writer.Create(tableName="users", variables=user)

    for externalid in externalids:
        externalid["id"] = externalid["id"]
        externalid["inner_id"] = externalid["inner_id"]
        externalid["typeid_id"] = externalid["typeid_id"]
        await db_writer.registerID(inner_id=externalid["inner_id"], outer_id=externalid["outer_id"],
                                   type_id=externalid["typeid_id"])


if __name__ == '__main__':
    #ensure_cache_dir()
    #main_sync()
    #asyncio.run(main_async())
    asyncio.run(db_writer_async())
