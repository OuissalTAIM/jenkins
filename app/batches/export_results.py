# -*- coding: utf-8 -*-
from app.config.env_func import reset_db_name
from app.data.Client import Driver
import sys
import csv
import app.config.env as env
import json


def write_in_csv(collection, scenario):
    records = Driver.get_results(collection, scenario)
    output_file = "%s%s" % (env.OUTPUT_FOLDER, "%s.csv" % collection)
    with open(output_file, mode='w', newline='', encoding='utf-8') as output_file:
        writer = csv.DictWriter(output_file, fieldnames=records[0].keys() if len(records) > 0 else ["empty"])
        writer.writeheader()
        for record in records:
            if "Moniker" in record and isinstance(record["Moniker"], list):
                record["Moniker"] = json.dumps(record["Moniker"])
            writer.writerow(record)

if __name__ == "__main__":
    option = "--all"
    scenario = 0
    reset_db_name("mine2farm")
    options_len = len(sys.argv)
    if options_len > 1:
        option = sys.argv[1]
        scenario = sys.argv[2] if options_len > 2 else ""
    if option == "--one":
        # global results
        write_in_csv("global", scenario)
        # detailed results
        write_in_csv("detailed", scenario)
    elif option == "--all":
        # global results
        write_in_csv("global", None)
        # detailed results
        write_in_csv("detailed", None)
