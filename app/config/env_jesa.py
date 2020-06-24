# -*- coding: utf-8 -*-


from enum import Enum, IntEnum, unique
import os


APP_NAME = "mine2farm"
NETWORK_NAME = "CenterAxis"
LOG_LEVEL_CONSOLE = "WARNING"
LOG_LEVEL_FILE = "INFO"
APP_FOLDER = os.getenv("JESA_MINE2FARM_HOME", "C:/GitRepos/mine2farm/")
LOG_FOLDER = APP_FOLDER + "app/log/"
LOG_FILE = "%(asctime)_" + APP_NAME + ".log"
OUTPUT_FOLDER = "%s%s" % (APP_FOLDER, "outputs/")
CANVAS_URL = "http://127.0.0.1/canvas.xlsm"


# DB
DB_NAME = None
DB_HOST = "172.29.161.208"
DB_PORT = 5006

DATA_SERVICE_ADD = "172.29.161.208"
DATA_SERVICE_PORT = 5001


# Results
DB_RESULT_NAME = "%s_results" % DB_NAME if DB_NAME is not None else None
DB_DETAILED_RESULT_COLLECTION_NAME = "detailed"
DB_GLOBAL_RESULT_COLLECTION_NAME = "global"
DB_GLOBAL_BEST_RESULT_COLLECTION_NAME = "global_best"
DB_DETAILED_BEST_RESULT_COLLECTION_NAME = "detailed_best"
DB_SENSITIVITY_COLLECTION_NAME = "sensitivity"
RESULT_BATCHES_SIZE = 25
HEAD_DATA_BITS = 17
DB_NAME_BITS = 20
RANDOMIZE_RESULTS = False


# RabbitMQ
RABBITMQ_SERVER = "localhost"
RABBITMQ_SIMULATOR_QUEUE_NAME = "SIMULATE"
RABBITMQ_CYCLE = 3
RABBITMQ_DETAILED_RESULT_QUEUE_NAME = "SAVE_DETAIL"
RABBITMQ_GLOBAL_RESULT_QUEUE_NAME = "SAVE_GLOBAL"
RABBITMQ_MAX_WORKER = RABBITMQ_CYCLE
RABBITMQ_PATH = "C:\\Program Files\\RabbitMQ Server\\rabbitmq_server-3.8.1\\sbin"


# Memcached
MEMCACHED_SERVER = 'localhost'
MEMCACHED_PORT = 11211


# Dashboard
DB_LOAD_FROM_SERVICE = True


# Monitoring
MONITORING_APP_NAME = "mine2farm_monitor"
MONITORING_SERVER = "172.29.161.208"
MONITORING_PORT = 5002
MONITORING_DB_NAME = "task_history"
MONITORING_COLLECTION_HISTORY_NAME = "task"
MONITORING_COLLECTION_HISTORY_BEST_NAME = "best_scenarios_history"
MONITORING_STEP = 1
MONITORING_NB_PAGE = 10


# Mongodb-bi
MONGODB_BI_PATH = "C:\\Program Files\\MongoDB\\Connector for BI\\2.13\\bin"


# Mongodb
MONGO_SERVER_PATH = "C:\\Program Files\\MongoDB\\Server\\4.0\\bin"


# params
LOGISTICS_LP = False
MODE_DEBUG = False
GRANUL_RELAX = False


class HTML_STATUS(IntEnum):
    ERROR = -1
    OK = 0


# Model
MONIKER_SEPARATOR = "/"
WACC = 0.1
T0 = 2020
TMAX = 2031

class PriceParams(Enum):
    WACC = 0
    TENOR = 1
    VOLUME = 2

class PipelineType(Enum):
    COMMON = 0
    PRODUCER = 1
    TRANSPORT = 2
    BALANCE = 3
    PRICE = 4
    SALES = 5

@unique
class PipelineLayer(IntEnum):
    UNDEFINED = -1
    MINE = 0
    BENEFICIATION = 1
    SAP = 2
    PAP = 3
    GRANULATION = 4
    LOGISTICS = 5
    RAW_MATERIALS = 8
    COMMON = 9
    SALES_PLAN = 10
    MINE_BENEFICIATION = 11
    UNIT_CONVERSION_MATRIX = 12

PIPELINE_SCHEMA = {
    PipelineLayer.COMMON: {
        "type": PipelineType.COMMON,
        "dico": ["location", "opex", "unit", "currency", "output", "names", "products"]
    },

    PipelineLayer.MINE: {
        "type": PipelineType.PRODUCER,
        "dico": ["mine.name", "mine.extraction", "mine.quality", "mine.capex"],
        "options": "mining_options",
        "production": "mining_specific_production",
        "opex": "mining_opex___specific_consumptions",
        "capex": "mining_capex",
        "priority_mines": "prioritymines"
    },

    PipelineLayer.BENEFICIATION: {
        "type": PipelineType.PRODUCER,
        "dico": ["beneficiation.name", "beneficitation.process", "beneficitation.quality", "beneficitation.capex"],
        "options": "beneficiation_options",
        "production": "beneficiation_production",
        "opex": "beneficiation_opex___specific_consumptions",
        "capex": "beneficiation_capex"
    },

    PipelineLayer.SAP: {
        "type": PipelineType.PRODUCER,
        "dico": ["sap.name", "sap.process", "sap.product", "sap.capex", "sap.capacity[kt]"],
        "options": "sap___power_plant_options",
        "production": "sap___power_plant_production",
        "opex": "sap___power_plant_opex___specific_consumptions",
        "capex": "sap___power_plant_capex",
        "product_type": "sap.product"
    },

    PipelineLayer.PAP: {
        "type": PipelineType.PRODUCER,
        "dico": ["pap.name", "pap.process", "pap.product", "pap.capex", "pap.size[kt]", "pap.input"],
        "options": "pap_options",
        "production": "pap_production",
        "opex": "pap_opex___specific_consumptions",
        "capex": "pap_capex",
        "product_type": "pap.product"
    },

    PipelineLayer.GRANULATION: {
        "type": PipelineType.PRODUCER,
        "dico": ["granulation.name", "granulation.process", "granulation.product", "granulation.capex", "granulation.input"],
        "options": "granulation_options",
        "production": "granulation_production",
        "opex": "granulation_opex",
        "capex": "granulation_capex"
    },

    PipelineLayer.LOGISTICS: {
        "type": PipelineType.TRANSPORT,
        "dico": ["logistics.name", "logistics.process", "logistics.product", "logistics.capex"],
        "options": "logistics_options",
        "production": None,
        "opex": "logistics_opex",
        "capex": "logistics_capex"
    },

    PipelineLayer.RAW_MATERIALS: {
        "type": PipelineType.PRICE,
        "data": "raw_materials"
    },

    PipelineLayer.SALES_PLAN: {
        "type": PipelineType.SALES,
        "data": "sales_plan"
    },
    PipelineLayer.UNIT_CONVERSION_MATRIX: {
        "type": PipelineType.COMMON,
        "data": "conv_matrix"
    },
}



SUPPLY_CHAIN = "mine2port"
DEPARTURE_ARRIVAL = {SUPPLY_CHAIN: (PipelineLayer.MINE),
                     "sap2pap": (PipelineLayer.SAP, PipelineLayer.PAP)}
COMBO_NODES = {
    PipelineLayer.MINE_BENEFICIATION: {
        "url": "mining_wp_connections",
        "upstream_layer": PipelineLayer.MINE,
        "downstream_layer": PipelineLayer.BENEFICIATION
    }
}
COMBO_NODES_SEPARATION = "--"

class FunctionType(Enum):
    COST_PV = 0
    CASH_COST = 1
    FULL_COST = 2

class ScenarioGeneratorType(IntEnum):
    FROM_PATHS = 0
    FROM_OPTIONS = 1
    SPECIFIC_SCENARIOS = 2
SCENARIO_GEN_TYPE = ScenarioGeneratorType.FROM_OPTIONS

PIPELINE_METADATA = {
    PipelineLayer.MINE: {
        "type": PipelineType.PRODUCER,
        "production": ["Name", "Extraction", "Quality", "Unit"],
        "opex": ["Name", "Extraction", "Capacity", "Item", "Unit"],
        "capex": ["Name", "Extraction", "Capacity", "Item", "Unit", "CAPEX"]
    },
    PipelineLayer.BENEFICIATION: {
        "type": PipelineType.PRODUCER,
        "production": ["Process", "InputQuality", "OutputQuality", "Humidity", "Unit"],
        "opex": ["Process", "InputQuality", "OutputQuality", "Item", "Unit"],
        "capex": ["Name", "Process", "Capacity", "Item", "Unit", "CAPEX"]
    },
    PipelineLayer.SAP: {
        "type": PipelineType.PRODUCER,
        "production": ["Location", "Process", "Product", "Unit"],
        "opex": ["Location", "Process", "Item", "Unit"],
        "capex": ["Location", "Process", "Capacity", "Item", "Unit", "CAPEX"]
    },
    PipelineLayer.PAP: {
        "type": PipelineType.PRODUCER,
        "production": ["Process", "Input", "Product", "Unit"],
        "opex": ["Location", "Process", "Capacity", "Input", "Item", "Product", "Unit"],
        "capex": ["Location", "Process", "Capacity", "Item", "Unit", "CAPEX"]
    },
    PipelineLayer.GRANULATION: {
        "type": PipelineType.PRODUCER,
        "production": ["Process", "Input", "Product", "Unit"],
        "opex": ["Location", "ProductionSite", "Process", "Capacity", "Product", "Item", "Unit"],
        "capex": ["Location", "ProductionSite", "Product", "Process", "Capacity", "Item", "Unit", "CAPEX"]
    },
    PipelineLayer.LOGISTICS: {
        "type": PipelineType.TRANSPORT,
        "opex": ["Upstream", "Downstream", "Method", "Product", "Capacity", "Item", "Unit"],
        "capex": ["Upstream", "Downstream", "Method", "Product", "Capacity", "Item", "Unit", "CAPEX"]
    },
    PipelineLayer.RAW_MATERIALS: {
        "type": PipelineType.PRICE,
        "columns": ["Item", "Unit"]
    },
    PipelineLayer.SALES_PLAN: {
        "type": PipelineType.PRICE,
        "columns": ["Type", "Product", "Unit"]
    },
    PipelineLayer.UNIT_CONVERSION_MATRIX: {
        "type": PipelineType.COMMON,
        "columns": ["Initial Unit", "Uniform Unit", "Conversion Rate"]
    },
}


class ShuffleLevel(IntEnum):
    UNDEFINED = 0
    SHUFFLE_WITHOUT_PERM = 1
    SHUFFLE_WITH_PERMUTATIONS = 2
    SHUFFLE_WITH_PERMUTATIONS_WITH_FILTERS = 3
    SHUFFLE_WITH_UNNAMED = 4


SHUFFLE_LEVELS = {
    PipelineLayer.MINE: ShuffleLevel.UNDEFINED,
    PipelineLayer.BENEFICIATION: ShuffleLevel.UNDEFINED,
    PipelineLayer.SAP: ShuffleLevel.SHUFFLE_WITH_UNNAMED,
    PipelineLayer.PAP: ShuffleLevel.SHUFFLE_WITH_UNNAMED,
    PipelineLayer.GRANULATION: ShuffleLevel.UNDEFINED,
    PipelineLayer.LOGISTICS: ShuffleLevel.UNDEFINED,
    PipelineLayer.MINE_BENEFICIATION: ShuffleLevel.UNDEFINED
}