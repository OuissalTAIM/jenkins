from app.entity.Entity import *
from app.entity.Capacity import *
import itertools


class GranulationDataPrep:

    def __init__(self, nodes, salesPlan):

        self.GranulationEntities = nodes[env.PipelineLayer.GRANULATION]
        self.Fertilizers_SP = salesPlan[(salesPlan.Type == 'Fertilizer')].copy()
        self.newEntities = self.get_new_entities_in_morocco()
        self.abroadEntities = self.get_entities_abroad()
        self.existingEntities = self.get_existing_entities()
        self.NodesList = self.getNodesList()
        self.SPsList = self.getSPsList()


        #self.Couples est la liste des couples liste de noeuds et sales plan, on runnera autant de PL qu'il y a d'éléments dans cette liste
        self.Couples = self.getNodes_SPs_couples()

    @staticmethod
    def get_new_entities_in_morocco(granulation_nodes):
        newEntitiesList = list(filter(lambda x: (x.entity.status == 'New'), granulation_nodes))
        newEntitiesInMorocco = list(filter(lambda x: (x.entity.productionSite =='Morocco'), newEntitiesList))
        newEntities = {}
        locations = list(set(node.entity.location for node in newEntitiesInMorocco))
        processes = list(set(node.entity.process for node in newEntitiesInMorocco))
        for location in locations:
            for process in processes:
                newEntities['/'.join([location, process])] = \
                    list(filter(lambda x: (x.entity.location == location and x.entity.process == process),
                                newEntitiesInMorocco))

        return list(newEntities.values())

    @staticmethod
    def get_existing_entities(granulation_nodes):
        existingEntities = list(filter(lambda x: (x.entity.status == 'Existing'), granulation_nodes))
        existing = {}
        dates = list(set(node.entity.closingDate for node in existingEntities))
        for date in dates:
            existing[date] = list(filter(lambda x: (x.entity.closingDate == date), existingEntities))

        return list(existing.values())

    @staticmethod
    def get_entities_abroad(granulation_nodes):
       return list(filter(lambda x: (x.entity.productionSite != 'Morocco'), granulation_nodes))

    def getSPsList(self):
        combinations = []
        for i in range(1,len(self.abroadEntities)+1):
            combinations.extend(list(itertools.combinations(self.abroadEntities, i)))
        SPs = []
        for combi in combinations:
            capa = pd.DataFrame({'volume': [1]*len(combi[0].entity.timeline), 'Tenor': combi[0].entity.timeline}).set_index('Tenor')
            for entity in combi :
                capacity = entity.entity.capacity.rename_axis('Tenor')
                capacity = pd.DataFrame(capacity).rename(columns = {0: 'volume'})
                capa = capa + capacity
            SPs.append(self.Fertilizers_SP.loc[self.Fertilizers_SP['Product'] == combi[0].entity.products[0], ['volume']] - capa)

        return SPs


    def getNodesList(self):
        nodes = []
        for element in self.newEntities:
            for element1 in self.existingEntities:
                nodes.append(element+element1)
        return nodes


    def getNodes_SPs_couples(self):
        couples = []
        for nodelist in self.NodesList:
            for sp in self.SPsList:
                a = (nodelist, sp)
                couples.append(a)

        return couples



