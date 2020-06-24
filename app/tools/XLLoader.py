# -*- coding: utf-8 -*-


import xlwings as xw
import pandas as pd
from app.data.DBAccess import DBAccess
from datetime import datetime
import app.config.env as env
from app.tools.Utils import trim_collection_name

COLLECTIONS_CACHE = set()


def add_time_decorator(function):
    def wrapper():
        result = function()
        return '%s %s' % (result, datetime.now().strftime("%H:%M:%S"))

    return wrapper



class XLLoader:
    def __init__(self):
        self.df = None

    def load_dataframe_from_XL(self, reference):
        wb = xw.Book.caller()
        range = wb.names(reference).refers_to_range
        table = range.sheet.range(range.address).expand('table').value
        df = pd.DataFrame(table[1:], columns=table[0])
        return df


@xw.func
@xw.arg('table', pd.DataFrame, index=False, header=True)
def JESA_UploadTable(name, table, db_name="mine2farm"):
    records = []
    header = list(table)
    for row in table.iterrows():
        record = {}
        for h in header:
            record[h] = row[1][h]
        records.append(record)

    env.DB_NAME = db_name
    db_access = DBAccess(env.DB_NAME)
    name_ = trim_collection_name(name)
    db_access.clear_collection(name_)
    db_access.save_to_db(name_, records)
    COLLECTIONS_CACHE.add(name_)
    return "%s Saved! @%s" % (name_, datetime.now().strftime("%H:%M:%S"))


@xw.func
def JESA_DropAll():
    db_access = DBAccess(env.DB_NAME)
    for collection in COLLECTIONS_CACHE:
        db_access.clear_collection(collection)
    collections = list(COLLECTIONS_CACHE)
    COLLECTIONS_CACHE.clear()
    return "|".join(collections)


if __name__ == '__main__':
    xw.serve()
