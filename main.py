from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver import Chrome, ChromeOptions
import re
import json

import getpass
# password = getpass.getpass()

# driver = webdriver.Chrome()

def get_data(url) -> list:
    browser_options = ChromeOptions()
    browser_options.headless = True
    
    driver = Chrome(options=browser_options)
    driver.get(url)
    
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
    data = get_data("https://apl.unob.cz/planovanivyuky/api/read/atributy")
    
    json_data_pattern = re.compile(r'"kindId":90}],(.*?),"proposals"')
    json_data = json_data_pattern.findall(data)
    with open("data.json", "w") as f:
        json.dump(json_data, f, indent=4)
    
    pattern = re.compile(r'"teachers":(.*?),"proposals"')
    matches = pattern.findall(data)
        
    if matches:
        userData = matches[0].strip()
        print("Match found.")
    else:
        print("Not match found.")
        
    userDataSplits = userData.split("},{")
    
    for userDataSplit in userDataSplits:
        if userDataSplit.count(",") == 3:
            user_id, user_name, department_id, academic = userDataSplit.split(",")
            user_id  = remove_keyword(user_id, '"id":')
            user_name = remove_keyword(user_name, '"name":')
            user_name = remove_chars(user_name, '"')
            department_id = remove_keyword(department_id, '"departmentId":')
            academic = remove_keyword(academic, '"academic":')
            academic = remove_chars(academic, '"')
            print(f"Id: {user_id}| Name: {user_name}| DepartmentId: {department_id}| Academic: {academic}")
        else:
            user_id, user_name, department_id = userDataSplit.split(",")
            user_id = remove_chars(user_id, '[{')
            user_id  = remove_keyword(user_id, '"id":')
            user_name = remove_keyword(user_name, '"name":')
            user_name = remove_chars(user_name, '"')
            department_id = remove_keyword(department_id, '"departmentId":')
            department_id = remove_chars(department_id, '}]')
            print(f"Id: {user_id}| Name: {user_name}| DepartmentId: {department_id}")
        
    
if __name__ == '__main__':
    main()








# driver.get("https://apl.unob.cz/planovanivyuky/api/read/atributy")

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


# driver.get("https://intranet.web.cz/aplikace/SitePages/DomovskaStranka.aspx")

# # Seznam akreditovanych programu
# # elem = driver.find_element(By.ID, "ctl00_ctl40_g_ba0590ba_842f_4a3a_b2ea_0c665ea80655_ctl00_LvApplicationGroupList_ctrl0_ctl00_LvApplicationsList_ctrl7_btnApp")
# elem = WebDriverWait(driver, 10).until(
#         expected_conditions.presence_of_element_located((By.ID, "ctl00_ctl40_g_ba0590ba_842f_4a3a_b2ea_0c665ea80655_ctl00_LvApplicationGroupList_ctrl0_ctl00_LvApplicationsList_ctrl7_btnApp"))
#     )
# elem.click()

# assert "No results found." not in driver.page_source
# driver.close()