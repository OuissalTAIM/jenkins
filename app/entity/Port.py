# -*- coding: utf-8 -*-


from app.entity.Entity import *
import app.tools.Utils as Utils
from app.entity.Capacity import *
from numpy import nan


class PortEntity(Entity):
    """
    Port class
    """
    def __init__(self, name, info):
        """
        Port entity class
        :param name: entity name
        :param info: Dataframe
        """
        super().__init__(name=name, layer=env.PipelineLayer.GRANULATION, id=info.Moniker)
        capacity = info.filter(regex="Capacity.*")
        unit = Utils.extract_unit(capacity.keys()[0])
        starting_date = int(info["StartingDate"]) if Utils.is_numeric(info["StartingDate"]) else -float("Inf")
        closing_date = int(info["ClosingDate"]) if Utils.is_numeric(info["ClosingDate"]) else float("Inf")
        self.capacity = Capacity(capacity[0], unit, start=starting_date, end=closing_date)
        self.main_input = None #TODO: should come from canvas dictionary

        self.action = info["Action"]
        self.location = info["Location"]
        #self.status = info["Status"]

    def set_production(self, prod_df):
        """
        Setting production
        :param data: Dataframe
        :return: None
        """
        self.outputs = prod_df.Product.unique().tolist()

    def set_opex(self, opex_df, raw_materials_df):
        """
        Setting opex from data dictionary
        :param opex_df: Dataframe
        :param raw_materials_df: Dataframe
        :return: None
        """
        self.main_input = "ALL" #TODO: review this
        self.inputs = opex_df[opex_df.Product != "Total"].Product.unique().tolist()
        self.specific_consumptions = Utils.multidict(["MAP"], ["All"], self.inputs, {})
        for item in self.inputs:
            #TODO: add warning if item already in
            self.specific_consumptions["MAP"]["All"][item] = opex_df[opex_df.Product == item]["sc/opex"]
        if "Total" in opex_df.Product:
            self.opex = opex_df[opex_df.Product == "Total"].rename(columns={"sc/opex": "opex"})
            self.opex = self.opex.opex
        else:
            self.opex = pd.merge(opex_df, raw_materials_df, left_on=["Product", "Tenor"], right_on=["Item", "Tenor"], how="left")
            self.opex["opex"] = self.opex["sc/opex"] * self.opex["price"]
            self.opex.reset_index().set_index("Tenor")
            self.opex = self.opex.groupby("Tenor").sum()["opex"]

    def set_capex(self, capex_df):
        """
        Setting capex
        :param capex_df: Dataframe
        :return: None
        """
        #TODO: verify if below formula is correct
        tenors = [self.capacity.start + float(tenor) for tenor in capex_df.index.unique()]
        tenors.sort()
        self.capacity.schedule(tenors)
        if "Total" in capex_df.Item.unique():
            #TODO: warning that other items are not considered
            self.capex = capex_df[capex_df.Item == "Total"]
        else:
            #TODO: warning that Total is not considered
            self.capex = capex_df[capex_df.Item != "Total"]
        self.capex = self.capex.CAPEX * self.capex.capex.replace(r'^\s*$', nan, regex=True).fillna(0)
        #TODO: check if below is necessary
        self.capex = self.capex.groupby(self.capex.index).sum()
