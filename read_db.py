import os
import pymongo
from pymongo import MongoClient

if __name__== '__main__':
	client = MongoClient('mongodb://localhost:27017/')
	db = client.db_ideas
	sharities = db.sharities
	print(len([sharity for sharity in sharities.find()]))
	for sharity in sharities.find():
		print()
		for key in sharity:
			try:
				print(key,sharity[key])
			except:
				pass

