#!/usr/bin/env python
# coding: utf-8

import unittest
import xmlrunner

def runner(output='python_tests_xml'):
    return xmlrunner.XMLTestRunner(
        output=output
    )

def find_tests():
    return unittest.TestLoader().discover('tests') #find all tests in the folder tests



if __name__ == '__main__':
    runner().run(find_tests())