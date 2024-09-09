import numpy as np
import tensorflow as tf
import nltk
from nltk.corpus import stopwords
import string
from bs4 import BeautifulSoup
import requests
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import os
import ctypes

nltk.download('punkt')
nltk.download('stopwords')

logging.basicConfig(
    filename='scraping.log',
    level=logging.INFO,
    format='%(asctime)s Seconds - %(levelname)s: %(message)s',
    datefmt='%m/%d/%Y %I:%M%p %S'
)

stop_words = set(stopwords.words('english'))
stm_mcu_part_urls = set()
page_num = 1
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

#Note: page1 yields completely different results compared to the default landing page

def setup_driver():
    service = Service(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=service)
    wait = WebDriverWait(driver, 12)  # Wait up to 12 seconds for conditions to be met
    return driver, wait

# Function to create a session with retry strategy
def requests_retry_session(retries=5, backoff_factor=0.5, status_forcelist=(500, 502, 504), session=None):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Initial session
session = requests_retry_session()

url = f"https://estore.st.com/en/products/microcontrollers-microprocessors.html"

output_dir = 'stm_part_specs'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

driver, wait = setup_driver()  # Initialize driver and wait

try:
    # Prevent the computer from going to sleep
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000002)
    
    try:
        page = requests.get(url, headers=headers).text
        time.sleep(1)
        doc = BeautifulSoup(page, 'html.parser')
        page_text = doc.find_all(class_="product-item-link")
        a_tags = doc.find_all('a', class_="page page-list-num")
        stm_mcu_part_page_urls = [a['href'] for a in a_tags]
        num_of_pages = len(stm_mcu_part_page_urls)

        
        with open('stm32_part_urls.txt', 'w') as file:
            while page_num != num_of_pages + 1:
                url = stm_mcu_part_page_urls[page_num - 1]
                try:
                    page = requests.get(url, headers=headers).text
                    time.sleep(1)
                    doc = BeautifulSoup(page, 'html.parser')
                    page_text = doc.find_all(class_="product-item-link")

                    for item in page_text:
                        href = item.get('href')
                        if href in stm_mcu_part_urls:
                            print(f"Page Number: {page_num} Element already in the set: {href}")
                        else:
                            file.write(f"{href}\n")
                            stm_mcu_part_urls.add(href)
                except requests.exceptions.RequestException as e:
                    logging.error(f"Error occurred while fetching the page {url}: {e}")
                    print(f"Error occurred while fetching the page {url}: {e}")
                    # Recreate the session if it fails
                    session = requests_retry_session()
                    page = requests.get(url, headers=headers).text
                    time.sleep(5)  # Delay to prevent rapid requests that might be cached
                    doc = BeautifulSoup(page, 'html.parser')
                    page_text = doc.find_all(class_="product-item-link")

                    for item in page_text:
                        href = item.get('href')
                        if href in stm_mcu_part_urls:
                            print(f"Page Number: {page_num} Element already in the set: {href}")
                            print(f"Page Error mediated at Page Number: {page_num} and url: {href}")
                        else:
                            file.write(f"{href}\n")
                            stm_mcu_part_urls.add(href)
                            print(f"Page Error mediated at Page Number: {page_num} and url: {href}")
                page_num += 1
                        
        print(f"Page Number: {page_num - 1}, Length of set: {len(stm_mcu_part_urls)}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred while fetching the main page: {e}")
        session = requests_retry_session()

    with open('stm32_part_urls.txt', 'r') as file:
        lines_in_file = file.readlines()
        number_of_lines_in_file = len(lines_in_file)
    try:
        for current_line, line in enumerate(lines_in_file, start=1):
            if current_line <= number_of_lines_in_file:
                url = line.strip()
                page = requests.get(url, headers=headers).text
                time.sleep(1)
                doc = BeautifulSoup(page, 'html.parser')

                if doc.find(class_="page-title"):
                    part_name = doc.find(class_="page-title").string.strip()
                else:
                    last_item = soup.select_one('.items li:last-child')
                    part_name = last_item.find('strong').string.strip()

                if doc.find(class_="value"):
                    part_name_caption = doc.find(class_="value").string.strip()
                else:
                    last_item = soup.select_one('.items li:last-child')
                    part_name_caption = last_item.find('strong').string.strip()

                part_name_parameters = doc.find(class_="table table-striped table-bordered")
                part_name_key_features = doc.find(class_="data table additional-attributes")

                output_filename = os.path.join('stm_part_specs', f"{part_name}.txt")
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(f"Part Name: {part_name.strip()}\n")
                    f.write(f"Caption: {part_name_caption.strip()}\n")

                    f.write(f"Parameters:\n")
                    for part_name in part_name_parameters.find_all('tr'):
                        part_name_data = [cell.text.strip() for cell in part_name.find_all(['th', 'td'])]
                        part_name_data = ': '.join(part_name_data) + '\n'
                        f.write(f"{part_name_data}\n")

                    if part_name_key_features:
                        f.write(f"{part_name_key_features.caption.string}:\n")
                        part_name_key_features = part_name_key_features.find('td', class_='col data')

                    def print_list_elements(element, indent=0):
                        if element and element.name == 'li':
                            text = element.get_text(strip=True)
                            if text is None:
                                text = ''
                            else:
                                text = text.replace('®', '® ')
                                text = text.replace('™', '™ ')
                                text = text.replace('\n', ' ')
                            # Printing with bullet points and appropriate indentation
                            f.write('    ' * indent + '• ' + text + '\n')
                        for child in element.children:
                            if child.name in ['ul', 'li']:
                                print_list_elements(child, indent + 1)
                    if part_name_key_features:
                        print_list_elements(part_name_key_features)

                    # Check if the loader exists before waiting for it to disappear
                    try:
                        driver.quit()
                        driver, wait = setup_driver()  # Restart driver
                        # Open the page
                        driver.get(url)
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'loading-mask')))
                        wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, 'loading-mask')))
                    except TimeoutException:
                        pass
                    try:
                        # Scroll into view and click the 'Read More' link
                        read_more_link = driver.find_element(By.CSS_SELECTOR, 'a.readmore')
                        driver.execute_script("arguments[0].scrollIntoView(true);", read_more_link)
                        driver.execute_script("arguments[0].click();", read_more_link)

                        time.sleep(1)
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        part_name_description = soup.find('div', class_='more')

                        if part_name_description:
                            f.write(f"Description: \n{part_name_description.text}")  #Include .strip() at the end
                    except NoSuchElementException:
                        print(f"Read more link not found for {url}")
                    except Exception as e:
                        print(f"Exception occurred for {url}: {str(e)}")
            print(f"Part Data has been processed at iteration # {current_line}")
            current_line += 1
            if current_line > number_of_lines_in_file:
                print('Hooray! The Webscrapper has finished properly and correctly.')
                driver.quit()
                break
    finally:
        driver.quit()
finally:
     # Revert to normal behavior
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

#Use S-Bert to create Document Embeddings
#Use RAGs to retrieve the most relevant document embedding within the set of documents while adding to the prompt to the LLM

def preprocess_dataset(data):
    tokens = nltk.word_tokenize(data)
    
    tokens = [word.lower() for word in tokens]
    
    tokens = [word for word in tokens if word not in stop_words and word not in string.punctuation]
    
    '''
    # Lemmatize words
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    '''
    return tokens