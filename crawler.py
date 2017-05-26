import os
import sys
from bs4 import BeautifulSoup 
from selenium.common.exceptions import WebDriverException
from selenium import webdriver
from unidecode import unidecode
from datetime import datetime
from geopy.geocoders import Nominatim
import pymongo
from pymongo import MongoClient
import argparse
import time
import urllib
import re

ROOT_PATH = 'http://www.ideas.asso.fr'
PATH = 'http://www.ideas.asso.fr/fr/associations/'



class page():
	def __init__(self,driver):
		self._driver = driver
		self.get_all()

	def get_all(self):
		self._client = MongoClient('mongodb://localhost:27017/')
		db = self._client.db_ideas
		sharities = db.sharities
		self._MAX_PAGES,self._link = self.get_number_pages()
		self.parse_page(self._driver,sharities)
		print(self._MAX_PAGES,self._link)
		for i in range(2,self._MAX_PAGES+1):
			self._link_page = self.create_link(i)
			print(ROOT_PATH+self._link_page)
			self._driver.get(ROOT_PATH+self._link_page)
			self.parse_page(self._driver,sharities)
			time.sleep(2)

	def decode(self,s):
		t = unidecode(s)
		t.encode("ascii")
		return t
	def tryprint(self,s):
		try:
			print(s)
		except:
			pass

	def parse_page(self,driver,sharities):
		page = driver.page_source
		soup = BeautifulSoup(page,'html.parser')
		divs = soup.find_all('div',class_="association")
		for div in divs:
			sharity = {}
			link_page = div.find_all('a')[0].get('href')
			img_src = div.find('img').get('src')
			description = div.find('div',class_="description")
			name = self.decode(description.find('h2').text)
			classes = self.decode(description.find('h2').next_sibling)
			classes_splits = classes.split('|')
			class_cleaned = [self.strip_c(c) for c in classes_splits]
			
			#real_ones = ','.join(classes_splits+last_one)
			sharity['LINK_PAGE'] = ROOT_PATH+link_page
			sharity['IMG_SRC'] = ROOT_PATH+img_src
			sharity['NAME'] = name
			sharity['CATEGORIES'] = class_cleaned
			#self.tryprint(link_page)
			#self.tryprint(img)
			#self.tryprint(name)
			#self.tryprint(class_cleaned)
			#driver.get(sharity['IMG_SRC'])

			#driver.save_screenshot('./imgs/'+sharity['NAME']+'.png')
			infos = self.get_infos_sharity(sharity['LINK_PAGE'],driver)
			d = {}
			for key in sharity:
				d[key]=sharity[key]
			for key in infos:
				if key == 'IMG_SRC':
					print(infos[key])
					d[key]=ROOT_PATH+infos[key]
				else:
					d[key]=infos[key]
			sharity_id = sharities.insert_one(d).inserted_id
			try:
				urllib.request.urlretrieve(d['IMG_SRC'], './imgs/'+str(sharity_id)+'.png')
			except:
				pass
			time.sleep(1)

	def cleanhtml(self,raw_html):
	  cleanr = re.compile('<.*?>')
	  cleantext = re.sub(cleanr, '', raw_html)
	  return cleantext		
		
	def get_infos_sharity(self,link_page,driver):
		driver.get(link_page)
		infos = {}
		page = driver.page_source
		soup = BeautifulSoup(page,'html.parser')

		## FIND INTERVENTION ZONES
		intervention = soup.find('div',{"id": 'zone-right'})
		parts = intervention.find_all('p',{"class": 'part'})
		country_list = []
		#print(parts)
		for part in parts:
			if ':' in str(part.text):
				text = part.text.split(':')
				continent = self.strip_c(text[0])
				countries = [self.strip_c(c) for c in self.strip_c(text[1]).split(',')]
				for c in countries:
					country_list.append(c)
			else:
				country_list.append(self.strip_c(part.text))
		infos['COUNTRIES'] = country_list

		## FIND COORD

		coord = soup.find('div',{"id": 'address-content'})
		links = coord.find_all('a')
		try:
			text = str(coord.find_all('p')[0])
			#print(text)
			o = text.split('<br>')
			adress = ' '.join([self.cleanhtml(i) for i in o])
		#print(adress)
		except:
			adress= None
		try:
			website = links[0].get('href')
		except:
			website = None
		ps = coord.find_all('p',{"class": 'img'})
		reg = re.compile('[0-9]{2,}')
		phone = None
		mail = None

		for p in ps:
			try:
				if  re.match(reg,p.text.replace(' ','')):
					phone = p.text
			except:
				pass
		for link in links:
			try:
				if 'mailto:' in link.get('href'):
					mail = link.get('href').split('mailto:','')
			except:
				pass
		#print(adress)
		#print(phone)
		#print(website)
		#print(mail) 
		infos['ADRESS'] = adress
		infos['WEBSITE'] = website
		infos['PHONE'] = phone
		infos['MAIL'] = mail

		##GEO
		geolocator = Nominatim()
		try:
			location = geolocator.geocode(infos['ADRESS'])[-1]
		except:
			location = -1
		infos['LOCALISATION']=location

		## GET IMGS 
		try:
			img_src = soup.find('img',{"alt": 'Logo'}).get('src')
		except:
			img_src = None
		infos['IMG_SRC'] = img_src
		#urllib.request.urlretrieve(sharity['IMG_SRC'], './imgs/'+str(sharity_id)+'.png')

		## GET ACTIONS
		actions = soup.find('div',{"id": 'actions-content'})
		infos['ACTIONS'] = self.strip_c(actions.text)

		## GET OBJET
		try:
			infos['OBJET'] = self.decode(soup.find('div',{"class": 'content'}).findChildren()[3].text)
		except:
			pass
		##GET MAIN 3
		driver.find_element_by_link_text('voir les 3 actions majeures').click()
		time.sleep(1)
		page = driver.page_source
		soup = BeautifulSoup(page,'html.parser')
		divs = soup.find_all('p',{"class": 'title2'})
		infos['MISSION']=[]
		#print(divs)
		for div in divs:
			try:
				infos['MISSION'].append([div.text,div.next_sibling.next_sibling.next_sibling.text])
			except:
				pass
		## GET RESOURCES
		infos['AMOUNT'] = str(self.decode(soup.find('div',{'id':'activity'}).text)).split('\n')[0]
		return infos














	def strip_c(self,sentence):
		return " ".join(sentence.replace('\n\t\t','').split())

	def create_link(self,number):
		return self._link[:-2]+str(number)	

	def get_number_pages(self):
		page = self._driver.page_source
		soup = BeautifulSoup(page,'html.parser')
		MAX_PAGES = 1
		uls = soup.find_all('ul')
		link = ''
		for ul in uls:
			try:
				if ul.get('class', [])[0] == 'pagination-number':
					lis = ul.find_all('li')
					MAX_PAGES = lis[-1].text
					link = lis[-1].findChildren()[0].get('href')
			except:
				pass
		return int(MAX_PAGES),link


def main():
	driver = webdriver.Firefox()
	driver.get(PATH)
	page(driver)
	# _id = 'id_domain_'
	# for i in range(1,11):
	# 	_id_n = _id+str(i)
	# 	driver.find_element_by_id(_id_n).click()
	# 	time.sleep(1)
	# 	page(i,driver)
	# 	break
		
		#driver.find_element_by_id(_id_n).click()





if __name__ == '__main__':
	main()



