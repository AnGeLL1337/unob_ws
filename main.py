from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver import Chrome, ChromeOptions
from bs4 import BeautifulSoup
import re
import json
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_id(url1, driver) -> list:

    driver.get(url1)
    ids = driver.page_source
    driver.quit()

    return ids

def remove_keyword(string, keyword):
    string = string.replace(keyword,"")
    return string

def remove_chars(string, chars):
    result = ""
    for char in string:
        if char not in chars:
            result += char
    return result


def get_data(finalurl, driver2) -> tuple:
    #print(finalurl)
    driver2.get(finalurl)
    data = BeautifulSoup(driver2.page_source, 'html.parser')
    elems = data.find_all("div", class_="col text-end")
    num_elems = len(elems) - 1
    #print(num_elems)
    if num_elems >= 13:
        name = elems[0].text.strip()
        title = elems[1].text.strip() + " / " + elems[2].text.strip()
        rank = elems[3].text.strip()
        department = elems[4].text.strip()
        email = elems[5].text.strip()
        phone = elems[6].text.strip()
        mobile = elems[7].text.strip()
        data_box = elems[8].text.strip()
        campus = elems[9].text.strip()
        building_room = elems[10].text.strip()
        faculty = elems[11].text.strip()
        taught_groups = data.find_all("div", id="StudiumSkupina")
        taught_group = [group.text.strip() for group in taught_groups]
    elif num_elems == 12:
        name = elems[0].text.strip()
        title = elems[1].text.strip()
        rank = elems[2].text.strip()
        department = elems[3].text.strip()
        email = elems[4].text.strip()
        phone = elems[5].text.strip()
        mobile = elems[6].text.strip()
        data_box = elems[7].text.strip()
        campus = elems[8].text.strip()
        building_room = elems[9].text.strip()
        faculty = elems[10].text.strip()
        taught_groups = data.find_all("div", id="StudiumSkupina")
        taught_group = [group.text.strip() for group in taught_groups]
    elif num_elems == 11:
        name = elems[0].text.strip()
        title = elems[1].text.strip()
        rank = None
        department = elems[2].text.strip()
        email = elems[3].text.strip()
        phone = elems[4].text.strip()
        mobile = elems[5].text.strip()
        data_box = elems[6].text.strip()
        campus = elems[7].text.strip()
        building_room = elems[8].text.strip()
        faculty = elems[9].text.strip()
        taught_groups = data.find_all("div", id="StudiumSkupina")
        taught_group = [group.text.strip() for group in taught_groups]
    elif num_elems <= 10:
        name = elems[0].text.strip()
        title = None
        rank = None
        department = elems[1].text.strip()
        email = elems[2].text.strip()
        phone = elems[3].text.strip()
        mobile = elems[4].text.strip()
        data_box = elems[5].text.strip()
        campus = elems[6].text.strip()
        building_room = elems[7].text.strip()
        faculty = elems[8].text.strip()
        taught_groups = data.find_all("div", id="StudiumSkupina")
        taught_group = [group.text.strip() for group in taught_groups]

    return name, title, rank, department, email, phone, mobile, data_box, campus, building_room, faculty, taught_group

def main():
    with open("personal.json") as f:
        personal = json.load(f)
    login1Url = personal["login1Url"]
    login2Url = personal["login2Url"]
    url1 = personal['url1']
    url2 = personal['url2']
    user = personal['user']
    password = personal['password']

    driver = Chrome()
    driver.get(login1Url)
    driver.get(login1Url)

    username_field = driver.find_element(By.ID, "floatingInput")
    password_field = driver.find_element(By.ID, "floatingPassword")

    username_field.send_keys(user)
    password_field.send_keys(password)

    submit = driver.find_element(By.NAME, "button")
    submit.click()

    ids = get_id(url1, driver)

    pattern = re.compile(r'"teachers":(.*?)],"classrooms"')
    matches = pattern.findall(ids)

    if matches:
        userID = matches[0].strip()
        print("Match found.")
    else:
        print("Not match found.")

    userIDSplits = userID.split("},{")

    with open("ids.txt", "a") as f:
        for userIDSplit in userIDSplits:
            user_id, user_surname, user_name = userIDSplit.split(",")
            user_id= remove_keyword(user_id, '"id":')
            user_id= remove_chars(user_id, '[{')
            f.write(user_id + "\n")

    print("IDs have been written.")

    driver2 = Chrome()
    driver2.get(login2Url)
    driver2.get(login2Url)

    username_field = driver2.find_element(By.ID, "floatingInput")
    password_field = driver2.find_element(By.ID, "floatingPassword")

    username_field.send_keys(user)
    password_field.send_keys(password)

    submit = driver2.find_element(By.NAME, "button")
    submit.click()

    data = {}
    with open("systemdata.json", "w") as f:
        f.write("[\n")

    external_ids = []

    with open("ids.txt", "r") as f:
        for line in f:
            value = line.strip()
            finalurl = url2 + value
            name, title, rank, department, email, phone, mobile, data_box, campus, building_room, faculty, taught_group = get_data(finalurl, driver2)

            data = {
                "ID" : value,
                "Jméno" : name,
                "Titul před / za" : title,
                "Hodnost / Titul za" : rank,
                "Katedra" : department,
                "Email" : email,
                "Telefon" : phone,
                "Mobil" : mobile,
                "Datová schránka" : data_box,
                "Areál" : campus,
                "Budova/Patro/Místnost" : building_room,
                "Fakulta" : faculty,
                "Seznam vyučovaných skupin" : taught_group
            }

            with open("systemdata.json", "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, indent=2) + ",\n")


            external_id = {
                "id": generate_uuid(),
                "name": name,
                "name_en": name,
                "urlformat": finalurl,
                "external_id": value
            }
            external_ids.append(external_id)

    with open("external_ids.json", "w", encoding="utf-8") as f:
        json.dump(external_ids, f, ensure_ascii=False, indent=2)


    # --- Part of code that erases last ',' between data of each user if there is no next
    with open("systemdata.json", "r", encoding="utf-8") as f:
        lines = f.readlines()

    if lines:
        last_line = lines[-1].strip()
        if last_line.endswith(","):
            lines[-1] = last_line[:-1] + "\n"

    with open("systemdata.json", "w", encoding="utf-8") as f:
        f.writelines(lines)
        f.write("]\n")
    # ---

    print("Teachers have been written.")

    driver2.quit()


if __name__ == '__main__':
    main()

