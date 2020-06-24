# -*- coding: utf-8 -*-


import hashlib
from app.tools.Logger import logger_simulation as logger


class Path:
    """
    Path class handling paths
    """

    def __init__(self, path=[]):
        """
        ctor
        :param path: list
        """
        self.path = path
        self.hash_id = None

    def __repr__(self):
        """
        Representation
        :return: list of Node names
        """
        return [node.moniker() for node in self.path].__repr__()

    def __str__(self):
        """
        Stringigy
        :return: string
        """
        return str(self.path)

    def __iter__(self):
        """
        Iterator protocol
        :return: Node
        """
        for node in self.path:
            yield node

    def __getitem__(self, item):
        """
        Get item
        :param item: index
        :return: Node
        """
        return self.path[item]

    def length(self):
        """
        Path length
        :return: Integer
        """
        return len(self.path)

    def empty(self):
        """
        Check if path is empty
        :return: Boolean
        """
        return len(self.path) == 0

    def hash(self):
        """
        hash id
        :return: string
        """
        if self.hash_id == None:
            self.hash_id = "".join([node.moniker() for node in self.path])
        return self.hash_id

    def to_dict(self):
        """
        Transform current scenario into list of dictionaries
        :return: dict
        """
        path_dict = {}
        for node in self.path:
            path_dict[node.layer().name] = node.moniker()
        return path_dict

    def reverse(self):
        """
        Reverse the list order
        :return: None
        """
        self.path.reverse()
        self.hash_id = None


class ScenarioFromPath:
    """
    Scenario class handling list of paths
    """

    def __init__(self, paths=[]):
        """
        ctor
        :param paths: list of lists of Node objects [[Node 1, ..], ..]
        """
        self.paths = []
        for path in paths:
            self.paths.append(Path(path))
        self.cost_curve = []
        self.hash_id = None

    def __repr__(self):
        """
        Representation
        :return: list of lists of Node names
        """
        scenario = []
        for path in self.paths:
            scenario.append(path.__repr__())
        return scenario

    def __str__(self):
        """
        Stringify
        :return: string
        """
        return str(self.paths)

    def __iter__(self):
        """
        Iterator protocol
        :return: Path
        """
        for path in self.paths:
            yield path

    def empty(self):
        """
        Check emptiness
        :return: Boolean
        """
        #TODO: check if embedded paths are empty as well
        return len(self.paths) == 0

    def hash(self):
        """
        hash id
        :return: string
        """
        if self.hash_id == None:
            monikers = [path.hash() for path in self.paths]
            joined_monikers = "".join(monikers).encode()
            self.hash_id = hashlib.sha256(joined_monikers)
        return self.hash_id.hexdigest()

    def to_dict(self):
        """
        Transform current scenario into list of dictionaries
        :return: dict
        """
        paths = []
        for path in self.paths:
            path_dict = path.to_dict()
            paths.append(path_dict)
        return {"scenario": self.hash(), "paths": paths}

    def save(self, db, cost_curve=None):
        """
        Save scenario to db
        :param db: db connection
        :return: None
        """
        scenario_dict = self.to_dict()
        if cost_curve is not None:
            if len(cost_curve) != len(self.paths):
                logger.error("Cost curve for scenario %s is not of same size as path" % self.hash())
            scenario_dict["curve"] = cost_curve
        db.save_to_db("scenarios", [scenario_dict])
