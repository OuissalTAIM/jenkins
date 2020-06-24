# -*- coding: utf-8 -*-


from enum import Enum


class UnitType(Enum):
    SIMPLE = 0
    RATIO = 1
    NO_UNIT = 2
    
class Value:
    """
    Handles values with units
    """

    def __init__(self, value, unit):
        self.value = value
        self.unit = unit
        if "/" in self.unit:
            units = unit.split("/")
            self.nominator = units[0]
            self.denominator = units[1]
            self.type = UnitType.RATIO
        else:
            self.type = UnitType.SIMPLE

    def __repr__(self):
        return str((self.value, self.unit))

    def __add__(self, other):
        """
        add operator
        :param other: Value object
        :return: Value object
        """
        if self.unit == other.unit:
            return Value(self.value + other.value, self.unit)
        new_other = UnitConvertor.convert(other, self.unit)
        return self.__add__(new_other)

    def __sub__(self, other):
        """
        subtract operator
        :param other: Value object
        :return: Value object
        """
        return self.__add__(Value(-other.value, other.unit))

    def __mul__(self, other):
        """
        multiply operator
        :param other: Value object, should be the ratio
        :return: Value object
        """
        #TODO: review this "y"
        if self.type == UnitType.RATIO and self.denominator != "y":
            return other.__mul__(self)
        if other.type != UnitType.RATIO:
            raise Exception("Cannot handle multiplication of units %s and %s" % (self.unit, other.unit))
        if self.unit != other.denominator:
            new_self = UnitConvertor.convert(self, other.denominator)
            return new_self.__mul__(other)
        return Value(self.value * other.value, other.nominator)

    def __truediv__(self, other):
        """
        Division operator
        :param other: Value object, should be the ratio
        :return: Value object
        """
        #TODO: handle division
        raise Exception("Cannot handle division of units %s and %s" % (self.unit, other.unit))


class UnitConvertor:
    @staticmethod
    def convert(value, target_unit):
        """
        Convert value into target_unit
        :param value: Value object
        :param target_unit: string
        :return: Value object
        """
        #TODO: implement here conversion from value.unit to target_unit
        return Value(value.value, target_unit)
