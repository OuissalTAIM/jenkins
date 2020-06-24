# -*- coding: utf-8 -*-
from functools import reduce

import pandas as pd
import app.config.env as env
from app.data.Client import Driver
from app.tools.Utils import production_header
from app.tools.Logger import logger_datamanager as logger

class DataManager:
    """
    Managing data in transformed dataframes
    """
    def __init__(self):
        """
        ctor
        """
        # get data
        self.original_data = {}
        self.data = {}
        self.raw_materials = None
        self.sales_plan = None

    def load_data(self):
        """
        Load data from Driver and transform it
        :return: None
        """
        self.load_original_data()
        self.transform_data()

    def load_original_data(self):
        """
        Load original data
        :return:
        """
        if len(self.original_data) > 0:
            raise Exception("Original data already loaded")

        for layer in env.PipelineLayer:
            if layer in [env.PipelineLayer.UNDEFINED, env.PipelineLayer.MINE_BENEFICIATION]:
                continue
            schema = env.PIPELINE_SCHEMA[layer]
            self.original_data[layer] = {}
            for key in schema:
                value = schema[key]
                if value is None:
                    continue
                #TODO: instead of "dico" find a more generic way
                if key == "dico":
                    collections = []
                    for url in value:
                        collections.append(Driver.get_data(url))
                    self.original_data[layer][key] = collections
                    continue
                #TODO: instead of "type" find a more generic way
                if key == "type":
                    self.original_data[layer][key] = value
                    continue
                self.original_data[layer][key] = Driver.get_data(value)

    def bump_raw_materials(self, shocks):
        """
        Bump original data
        :param shocks: Dictionary
        :return: None
        """
        # bump
        all_items = self.raw_materials["Item"].unique()
        for item in shocks:
            if item not in all_items:
                logger.warning("Item %s not found in raw materials data" % item)
                continue
            self.raw_materials.loc[self.raw_materials["Item"] == item, "price"] = \
                self.raw_materials[self.raw_materials["Item"] == item]["price"] + shocks[item]

    def transform_data(self):
        """
        Transform data into more efficient dataframes
        :return: None
        """
        if any([self.raw_materials is not None, self.sales_plan is not None, len(self.data) > 0]):
            raise Exception("Data already transformed")

        convlayer = self.original_data[env.PipelineLayer.UNIT_CONVERSION_MATRIX]
        unitmatrix = pd.DataFrame(convlayer['data'])

        for layer in self.original_data:
            if layer not in env.PIPELINE_METADATA:
                continue

            if layer == env.PipelineLayer.UNIT_CONVERSION_MATRIX:
                continue

            original_data = self.original_data[layer]
            headers = env.PIPELINE_METADATA[layer]

            if layer == env.PipelineLayer.RAW_MATERIALS:
                self.raw_materials = DataManager.melt_without_moniker(pd.DataFrame(original_data["data"]),
                                                                      "price", headers)
                self.raw_materials = DataManager.merge_rawmat_unit_data(unitmatrix, self.raw_materials)

            elif layer == env.PipelineLayer.SALES_PLAN:
                self.sales_plan = DataManager.melt_without_moniker(pd.DataFrame(original_data["data"]),
                                                                   "volume", headers)
                self.sales_plan = DataManager.merge_salesplan_unit_data(unitmatrix, self.sales_plan)

            else:
                self.data[layer] = {}
                # handling options
                options = pd.DataFrame(original_data["options"])
                self.data[layer]["Options"] = options[(options["Moniker"] != "") & (~options["Moniker"].isna())]
                self.data[layer]["Options"] = DataManager.merge_options_unit_data(unitmatrix,
                                                                                  self.data[layer]["Options"])

                # handling opex/specific consumptions
                opexs = pd.DataFrame(original_data["opex"])
                self.data[layer]["SpecCons"] = DataManager.melt_and_include_moniker(opexs, "opex", "sc/opex", options,
                                                                                    headers)
                self.data[layer]["SpecCons"] = DataManager.merge_sc_opex_unit_data(unitmatrix,
                                                                                   self.data[layer]["SpecCons"])

                # handling specific production
                if headers["type"] == env.PipelineType.PRODUCER:
                    self.data[layer]["SpecProd"] = DataManager.melt_and_include_moniker(
                        pd.DataFrame(original_data["production"]), "production", production_header(layer), options,
                        headers)
                    self.data[layer]["SpecProd"] = DataManager.merge_sc_opex_unit_data(unitmatrix,
                                                                                     self.data[layer]["SpecProd"])
                else:
                    self.data[layer]["SpecProd"] = None

                # handling capex
                self.data[layer]["Capex"] = DataManager.melt_and_include_moniker(pd.DataFrame(original_data["capex"]),
                                                                                 "capex", "capex", options, headers)
                self.data[layer]["Capex"] = DataManager.merge_capex_unit_data(unitmatrix, self.data[layer]["Capex"])

                # Adding priority mines to data for mine layer
                if layer == env.PipelineLayer.MINE:
                    self.data[layer]["priority_mines"] = \
                        reduce(lambda x, y: x+y, [list(dict.values())
                                                  for dict in self.original_data[layer]["priority_mines"]])

                # Adding byproducts list to data for SAP and PAP layers:
                if layer in [env.PipelineLayer.SAP, env.PipelineLayer.PAP]:
                    self.data[layer]["product_type"] = pd.DataFrame(original_data['product_type']).set_index('Product').to_dict()['Type']


    @staticmethod
    def melt_and_include_moniker(df_, metadata, value_name, df2, headers):
        """
        :param df_: df to melt_and_include_moniker
        :param metadata: name of key (i.e. sheet) in PIPELINE_METADATA
        :param value_name: name to use as value column
        :param df2: assumed to be options
        :param headers: assumed to be headers
        :return: transformed df
        """
        df = df_[(df_[headers[metadata][0]] != "") & (~df_[headers[metadata][0]].isna())]
        intersection = list(df.columns & df2.columns)
        if 'Unit' in intersection: intersection.remove('Unit')
        if 'Product' in intersection: intersection.remove('Product')
        output = pd.merge(df, df2[["Moniker"] + intersection], on=intersection)
        output = pd.melt(output, id_vars=["Moniker"] + headers[metadata], var_name="Tenor"). \
            rename(columns={"value": value_name}).set_index("Tenor")
        output.index = pd.to_numeric(output.index)
        output.sort_index(inplace=True, ascending=True)
        return output

    @staticmethod
    def melt_without_moniker(df_, value_name, headers):
        """ Applies for sales plan and raw materials only """
        df = pd.melt(df_, id_vars=headers["columns"], var_name="Tenor"). \
            rename(columns={"value": value_name}).set_index("Tenor")
        df.index = pd.to_numeric(df.index)
        return df.sort_index(ascending=True)

    @staticmethod
    def merge_salesplan_unit_data(convmatrixdf, targetdf):
        # unit conversion fct takes as argument the conversion matrix df & the target df to be treated

        if 'Unit' in convmatrixdf.columns and 'Unit' in targetdf.columns:
            unittest = targetdf['Unit'].isin(convmatrixdf['Unit'])
            if unittest[unittest.isin([False])].empty:
                df3 = pd.merge(convmatrixdf, targetdf, on='Unit', left_index=True)
                df3['volume'] = df3['volume'] * df3['Conversion Rate']
                df3['Unit'] = df3['Uniform Unit']
                df3 = df3.drop(columns=['Uniform Unit', 'Conversion Rate'])
                return df3
            else:
                error_msg = "This unit is not handled by the canvas: %s" % targetdf['Unit'][
                    targetdf['Unit'].isin(convmatrixdf['Unit']) is False]
                logger.error(error_msg)
                raise Exception(error_msg)

        else:
            if 'Unit' not in convmatrixdf.columns:
                error_msg = "Unit column is missing in conversion matrix: %s" % list(convmatrixdf.columns)
            else:
                error_msg = "Unit column is missing in table: %s" % list(targetdf.columns)
            logger.error(error_msg)
            raise Exception(error_msg)

    @staticmethod
    def merge_rawmat_unit_data(convmatrixdf, targetdf):
        # unit conversion fct takes as argument the conversion matrix df & the target df to be treated

        if 'Unit' in convmatrixdf.columns and 'Unit' in targetdf.columns:
            unittest = targetdf['Unit'].isin(convmatrixdf['Unit'])
            if unittest[unittest.isin([False])].empty:
                df3 = pd.merge(convmatrixdf, targetdf, on='Unit', left_index=True)
                df3['price'] = df3['price'] * df3['Conversion Rate']
                df3['Unit'] = df3['Uniform Unit']
                df3 = df3.drop(columns=['Uniform Unit', 'Conversion Rate'])
                return df3
            else:
                error_msg = "This unit is not handled by the canvas: %s" % targetdf['Unit'][
                    targetdf['Unit'].isin(convmatrixdf['Unit']) is False]
                logger.error(error_msg)
                raise Exception(error_msg)

        else:
            if 'Unit' not in convmatrixdf.columns:
                error_msg = "Unit column is missing in conversion matrix: %s" % list(convmatrixdf.columns)
            else:
                error_msg = "Unit column is missing in table: %s" % list(targetdf.columns)
            logger.error(error_msg)
            raise Exception(error_msg)

    @staticmethod
    def merge_options_unit_data(convmatrixdf, targetdf):
        #unit conversion fct takes as argument the conversion matrix df & the target df to be treated

        if 'Unit' in convmatrixdf.columns and 'Unit' in targetdf.columns:
            unittest = targetdf['Unit'].isin(convmatrixdf['Unit'])
            if unittest[unittest.isin([False])].empty:
                df3 = pd.merge(convmatrixdf, targetdf, on='Unit', left_index=True)
                df3['Capacity'] = df3['Capacity'] * df3['Conversion Rate']
                df3['Unit'] = df3['Uniform Unit']
                df3 = df3.drop(columns=['Uniform Unit', 'Conversion Rate'])
                return df3
            else:
                error_msg = "This unit is not handled by the canvas: %s" % targetdf['Unit'][targetdf['Unit'].isin(convmatrixdf['Unit']) is False]
                logger.error(error_msg)
                raise Exception(error_msg)

        else:
            if 'Unit' not in convmatrixdf.columns:
                error_msg = "Unit column is missing in conversion matrix: %s" % list(convmatrixdf.columns)
            else:
                error_msg = "Unit column is missing in table: %s" % list(targetdf.columns)
            logger.error(error_msg)
            raise Exception(error_msg)

    @staticmethod
    def merge_capex_unit_data(convmatrixdf, targetdf):
        # unit conversion fct takes as argument the conversion matrix df & the target df to be treated
        if 'Unit' in convmatrixdf.columns and 'Unit' in targetdf.columns:
            unittest = targetdf['Unit'].isin(convmatrixdf['Unit'])
            if unittest[unittest.isin([False])].empty:
                df3 = pd.merge(convmatrixdf, targetdf, on='Unit', left_index=True)
                df3['CAPEX'] = df3['CAPEX'] * df3['Conversion Rate']
                df3['Unit'] = df3['Uniform Unit']
                df3 = df3.drop(columns=['Uniform Unit', 'Conversion Rate'])
                return df3
            else:
                error_msg = "This unit is not handled by the canvas: %s" % targetdf['Unit'][targetdf['Unit'].isin(convmatrixdf['Unit']) is False]
                logger.error(error_msg)
                raise Exception(error_msg)
        else:
            if 'Unit' not in convmatrixdf.columns:
                error_msg = "Unit column is missing in conversion matrix: %s" % list(convmatrixdf.columns)
            else:
                error_msg = "Unit column is missing in table: %s" % list(targetdf.columns)
            logger.error(error_msg)
            raise Exception(error_msg)

    @staticmethod
    def merge_sc_opex_unit_data(convmatrixdf, targetdf):
        if 'Unit' in convmatrixdf.columns and 'Unit' in targetdf.columns:
            unittest = targetdf['Unit'].isin(convmatrixdf['Unit'])
            if unittest[unittest.isin([False])].empty:
                df3 = pd.merge(convmatrixdf, targetdf, on='Unit', left_index=True)
                for column in df3._get_numeric_data():
                    if column == 'Conversion Rate' or column == 'Capacity':
                        continue
                    else:
                        df3[column] = df3[column] * df3['Conversion Rate']
                df3['Unit'] = df3['Uniform Unit']
                df3 = df3.drop(columns=['Uniform Unit', 'Conversion Rate'])
                return df3
            else:
                error_msg = "This unit is not handled by the canvas: %s" % targetdf['Unit'][targetdf['Unit'].isin(convmatrixdf['Unit']) is False]
                logger.error(error_msg)
                raise Exception(error_msg)
        else:
            if 'Unit' not in convmatrixdf.columns:
                error_msg = "Unit column is missing in conversion matrix: %s" % list(convmatrixdf.columns)
            else:
                error_msg = "Unit column is missing in table: %s" % list(targetdf.columns)
            logger.error(error_msg)
            raise Exception(error_msg)

