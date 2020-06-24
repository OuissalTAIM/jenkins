# -*- coding: utf-8 -*-


from pymongo import MongoClient
import math
from app.tools.Logger import logger_datamanager as logger
from app.config import env

MONGO_CLIENT = MongoClient(host=env.DB_HOST, port=env.DB_PORT)


class DBAccess:
    def __init__(self, name):
        """
        Constructor
        """
        if name is None:
            msg = "Database name is not defined!"
            logger.error(msg)
            raise Exception(msg)
        self.db = MONGO_CLIENT[name]

    @staticmethod
    def get_dbs_names():
        """
        Get all dbs names
        :return: list
        """
        cursor = MONGO_CLIENT.list_database_names()
        names = []
        for db in cursor:
            names.append(db)
        return names

    def clear_collection(self, collection):
        """
        Clear collection in db
        :param collection:
        :return: None
        """
        self.db[collection].drop()

    def create_index(self, collection, index):
        """
        Creates index over collection
        :param collection: string
        :param index: Dictionary
        :return: None
        """
        self.db[collection].create_index(index)

    def save_to_db_no_check(self, collection, records):
        return self.db[collection].insert(records, check_keys=False)

    def save_to_db(self, collection, records):
        """
        Get df from XL (or other) and save it to db
        :param collection: name
        :param records: list of dictionaries
        :return: None
        """
        records_to_save = []
        for record in records:
            for key in record:
                if key == "_id":
                    continue

                value = record[key]
                check_if_valid = True if value is not None else False
                if check_if_valid and value.__class__ == float:
                    check_if_valid = not math.isnan(value)
                if check_if_valid and value.__class__ == str:
                    check_if_valid = len(value) > 0

                if check_if_valid:
                    records_to_save.append(record)
                    break
        self.db[collection].insert_many(records_to_save)

    def get_all_records(self, collection):
        """
        Get a collection from db
        :param collection: string
        :return: list, integer
        """
        return list(self.db[collection].find()), self.db[collection].count()

    def get_records(self, collection, filter_):
        """
        Get a collection from db
        :param collection: string
        :param filter_: Dictionary
        :return: Cursor
        """
        return self.db[collection].find(filter_)

    def get_records_with_mask(self, collection, filter_, mask):
        """
        Get a collection from db
        :param collection: string
        :param filter_: Dictionary
        :param mask: Dictionary
        :return: Cursor
        """
        return self.db[collection].find(filter_, mask)

    def get_one_record(self, collection, filter_):
        """
        Get records given fields
        :param collection: string
        :param filter_: dictionary
        :return: JSON
        """
        return self.db[collection].find_one(filter_)

    def get_fields(self, collection, filter_, sort_direction, limit_=0):
        """
        Get fields for all records
        :param collection: string
        :param filter_: Dictionary
        :param sort_direction: list
        :param limit_: integer
        :return: Cursor
        """
        if limit_ <= 0:
            if len(sort_direction) == 0:
                return self.db[collection].find({}, filter_)
            return self.db[collection].find({}, filter_).sort(sort_direction)
        return self.db[collection].find({}, filter_).limit(limit_)

    def get_records_sort(self, collection,  filter_, sort_key, sort_direction, limit_=0):
        """
        Get collection with sort and limit and count element
        :param collection: collection name
        :param filter_: filter option
        :param sort_key: key  to sort
        :param sort_direction: direction for sort
        :param limit_: limit value
        :return: tuple
        """
        return self.db[collection].find({}, filter_).sort([[sort_key, sort_direction]]).limit(limit_), self.db[collection].count()

    def get_records_with_pagination(self, collection,  filter_, sort_key, sort_direction, current_page, nb_pr_page):
        """
        Get collection with pagination and count element
        :param collection: collection name
        :param filter_: filter option
        :param sort_key: key  to sort
        :param sort_direction: direction for sort
        :param current_page: currant page
        :param nb_pr_page: number per page
        :return: tuple
        """
        skips = nb_pr_page * (current_page-1)
        total_items = self.db[collection].count()
        return self.db[collection].find({}, filter_).skip(skips).sort([[sort_key, sort_direction]]).limit(nb_pr_page), total_items

    def update_record(self, collection,  filter_, data):
        """
        Update record and return _id
        :param collection: collection name
        :param filter_: Dict
        :param data: dict
        :return: String
        """
        self.db[collection].update(filter_, {'$set': data})

    def delete_record(self,  collection,  filter_):
        """
        Delete one document by filter
        :param collection: collection name
        :param filter_: filter option
        :return: None
        """
        self.db[collection].delete_one(filter_)

    def copy_to_collection(self, source, destination):
        """
        Copy one collection to another
        :param source: string, collection name
        :param destination: string, collection name
        :return: None
        """
        pipeline = [
            {"$match": {}},
            {"$out": destination},
        ]
        self.db[source].aggregate(pipeline)

    def count(self, collection):
        """
        Count of collection
        :param collection: string
        :return: integer
        """
        return self.db[collection].count()
