# -*- coding: utf-8 -*-


from app.data.Client import *


if __name__ == "__main__":
    mining_capex = Driver.get_data("mining_capex", format="json")
    for mine in mining_capex:
        mine_capex = MiningCapex.Schema().loads(mine)
        print(mine_capex)
