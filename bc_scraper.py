import requests
from bs4 import BeautifulSoup as BS4
from datetime import datetime
import pandas as pd
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

## The first argument is the main id of the project on basecamp
## The second argument is the file path of the CSV. Enclose in quotes.
## The third argument is the Basecamp username. Enclose in quotes.
## Once it shows the Basecamp login, please enter your password

if len(sys.argv) != 4:
	print("Please run the script with the following 3 arguments: <Basecamp ID> <CSV full path> <username>!!")
	sys.exit(2)

main_id = sys.argv[1]
csv_full_path = sys.argv[2]
username = sys.argv[3]

login_url = 'https://launchpad.37signals.com/signin'
base_url = 'https://3.basecamp.com'
initial_basecamp_page = os.path.join(base_url, main_id) + '/projects'

headers = {
	'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
}

def request(driver):  
	s = requests.Session()
	cookies = driver.get_cookies()
	for cookie in cookies:
	     s.cookies.set(cookie['name'], cookie['value'])
	return s;

def login():
	driver = webdriver.Chrome()
	driver.get(login_url)
	driver.find_element_by_id('username').send_keys(username)
	# time.sleep(3)
	driver.find_element_by_name('button').click()
	
	# You have two minutes until the selenium browser times out
	wait = WebDriverWait(driver, 120)
	wait.until(lambda driver: driver.find_element_by_class_name('project-index__section'))
	
	print("Successful login!")
	return request(driver);

def main():
	print('Logging into Basecamp...')
	req = login()
	
	print('Collecting data...')
	response = req.get(initial_basecamp_page, headers = headers)
	if response.status_code == 200:
		soup = BS4(response.content, 'html5lib')
		projects = soup.find('section', class_ = 'project-index__section--projects').findAll('article', class_ = 'project-list__project')

		list_of_rows = []
		for project in projects:
			project_name = project.find('a', class_ = 'project-list__link').get_text().strip()
			project_url = base_url + project.find('a', class_ = 'project-list__link')['href']
			project_response = req.get(project_url, headers = headers)
			
			if project_response.status_code == 200:
				project_soup = BS4(project_response.content, 'html5lib')
				todo_url = base_url + project_soup.find('article', class_='card--todoset')['data-url']
				todo_response = req.get(todo_url, headers = headers)
				
				if todo_response.status_code == 200:
					todo_soup = BS4(todo_response.content, 'html5lib')

					if todo_soup.findAll('article', class_ = 'todolist') is not None:
						todo_lists = todo_soup.findAll('article', class_ = 'todolist')

						for todo_list in todo_lists:
							if todo_list.find('a', class_ = 'todolist__permalink') is not None:
								todo_name = todo_list.find('a', class_ = 'todolist__permalink').get_text().strip()
								task_url = base_url + todo_list.find('a', class_ = 'todolist__permalink')['href']
								task_response = req.get(task_url, headers = headers)
								
								if task_response.status_code == 200:
									task_soup = BS4(task_response.content, 'html5lib')
									task_list = task_soup.findAll('li', class_= 'todo')
									task_status = 0

									for task in task_list:
										task_name = task.find('a').get_text().strip()

										completed = ''
										if len(task['class']) == 1:
											completed = None
										else:
											completed = task['class'][1]

										if completed == 'completed':
											task_status = 1

										list_of_rows.append((project_name, todo_name, task_name, task_status))
				
	print("Creating the CSV...")
	df = pd.DataFrame(list_of_rows, columns = ['project_name', 'todo_list', 'todo_name', 'status'])
	df.to_csv(csv_full_path, index = False)
	print("CSV saved at %s" % csv_full_path)

if __name__ == '__main__':
	main()