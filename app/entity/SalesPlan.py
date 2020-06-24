from app.tools.Utils import multidict

class SalesPlan:
    """
    Class describing sales plan
    """

    def __init__(self, sales_plan, scenario):
        tenors = sales_plan.index.unique().tolist()
        self.timeline = tenors.sort()
        self.products_in_sales_plan = list()
        self.local_sp_per_product = self.get_local_sp_per_product()
        self.export_sp_per_product = self.get_export_per_product()
        self.chemical_needs_per_product = self.get_chemical_needs()
        self.spare_per_product = self.get_spare_per_product()
        #TODO: add in spreadsheets input places for strategic spare, local sp, etc.
        #TODO: complete class with corresponding methods
        #TODO: unify writing of products along supply chain

    def get_export_per_product(self):
        """ Elements in this dict are to be used for propagation from port
        :return: multidict(self.products_in_sales_plan, {})
        """
        return 1

    def get_local_sp_per_product(self):
        """ Elements in this dict are to be used for propagation alongside export in production entities
        :return: multidict(self.products_in_sales_plan, {})
        """
        return 1

    def get_chemical_needs(self):
        """contains needs of produced products that are produced wwithin ocp (Acid, rocks)
        :return: multidict(products, pd.Series[prices])
        """
        return 1

    def get_spare_per_product(self):
        """contains spare volumes for relevant products. pd.Series([0 for i in years]) if irrelevant
        :return: multidict(products, pd.Series[prices])
        """
