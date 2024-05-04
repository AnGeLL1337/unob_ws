from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver import Chrome, ChromeOptions
import re
import json

import getpass

def get_data(url1) -> list:
    browser_options = ChromeOptions()
    browser_options.headless = True
    
    driver = Chrome(options=browser_options)
    driver.get(url1)
    
    data = driver.page_source
    driver.quit()
    
    return data

def remove_keyword(string, keyword):
    string = string.replace(keyword,"")
    return string

def remove_chars(string, chars):
    result = ""
    for char in string:
        if char not in chars:
            result += char
    return result
    
def main():
    with open("personal.json") as f:
        personal = json.load(f)
    loginUrl = personal["loginUrl"]
    url1 = personal['url1']
    url2 = personal['url2']
    user = personal['user']
    password = personal['password']
    
    driver = Chrome()
    driver.get(loginUrl)
    
    username_field = driver.find_element(By.NAME, "Username")
    password_field = driver.find_element(By.NAME, "Password")
    
    username_field.send_keys(user)
    password_field.send_keys(password)
         
    submit = driver.find_element(By.NAME, "button")
    submit.click()
    #password_field.submit()
    
    data = get_data(url1)
    
    print(data)
    
    # json_data_pattern = re.compile(r'7F83F655-BC00-11ED-AF62-EBF700000000","22823"]}],(.*?),"classrooms"')
    # json_data = json_data_pattern.findall(data)
    # with open("data.json", "w") as f:
    #     json.dump(json_data, f, indent=4)
    
    # pattern = re.compile(r'"teachers":(.*?)],"classrooms"')
    # matches = pattern.findall(data)
        
    # if matches:
    #     userData = matches[0].strip()
    #     print("Match found.")
    # else:
    #     print("Not match found.")
        
    # userDataSplits = userData.split("},{")
    
    # for userDataSplit in userDataSplits:
    #     #user_id, user_name = userDataSplit.split(",")
    #     #user_id  = remove_keyword(user_id, '"id":')
    #     #user_name = remove_keyword(user_name, '"name":')
    #     #user_name = remove_chars(user_name, '"')
    #     #print(f"Id: {user_id}| Name: {user_name}")
    #     print(userDataSplit)
        
    
if __name__ == '__main__':
    main()








# driver.get("url")

# elem = driver.find_element(By.ID, "userNameInput")
# elem.clear()
# elem.send_keys("email@web.cz")
# elem.send_keys(Keys.RETURN)

# elem = driver.find_element(By.ID, "passwordInput")
# elem.clear()
# elem.send_keys(password)
# elem.send_keys(Keys.RETURN)

# elem = driver.find_element(By.ID, "submitButton")
# elem.click()


# driver.get("url")

# # Seznam akreditovanych programu
# # elem = driver.find_element(By.ID, "ctl00_ctl40_g_ba0590ba_842f_4a3a_b2ea_0c665ea80655_ctl00_LvApplicationGroupList_ctrl0_ctl00_LvApplicationsList_ctrl7_btnApp")
# elem = WebDriverWait(driver, 10).until(
#         expected_conditions.presence_of_element_located((By.ID, "ctl00_ctl40_g_ba0590ba_842f_4a3a_b2ea_0c665ea80655_ctl00_LvApplicationGroupList_ctrl0_ctl00_LvApplicationsList_ctrl7_btnApp"))
#     )
# elem.click()

# assert "No results found." not in driver.page_source
# driver.close()

