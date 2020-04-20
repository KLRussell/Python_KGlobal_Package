from __future__ import unicode_literals

from pandas import DataFrame
from portalocker import Lock as Open

import xml.etree.ElementTree as ET
import os


class XML(object):
    """
    Read and Write XML objects by using XML.etree.ElementTree module
    """

    def __init__(self, xml_file):
        if not os.path.exists(xml_file):
            raise Exception("'xml_file' %r is not a valid filepath" % xml_file)

        try:
            self.xml_file = xml_file
        except AssertionError as e:
            raise Exception('\t[-] %s: Parsing XML Failed' % e)

    def read(self, xmlns_rs, dict_var=None):
        """
        Reads XML files and store in a dict or pandas DataFrame

        :param xmlns_rs: XMLNS_RS sentence in XML file
        :param dict_var: (Optional) Dict object
        :return: Dataframe or Dict
        """

        tree = ET.parse(self.xml_file)
        root = tree.getroot()

        if isinstance(dict_var, dict):
            for item in root.findall(xmlns_rs):
                dict_var = self.__parse_element(item, dict_var)

            return dict_var
        else:
            parsed = [self.__parse_element(item) for item in root.findall(xmlns_rs)]
            df = DataFrame(parsed)

            return df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    def write(self, dataframe):
        """
        Write Dataframe to XML

        :param dataframe: Pandas DataFrame
        """

        if not isinstance(dataframe, DataFrame):
            raise ValueError("'dataframe' %r is not an instance of DataFrame from pandas" % dataframe)

        with Open(self.xml_file, 'w') as xmlfile:
            xmlfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            xmlfile.write('<records>\n')
            xmlfile.write(
                '\n'.join(dataframe.apply(self.__xml_encode, axis=1))
            )
            xmlfile.write('\n</records>')

    def __parse_element(self, element, parsed=None):
        if not parsed:
            parsed = dict()

        if element.keys():
            for key in element.keys():
                if key not in parsed:
                    parsed[key] = element.attrib.get(key)

                if element.text and element.tag not in parsed:
                    parsed[element.tag] = element.text

        elif element.text and element.tag not in parsed:
            parsed[element.tag] = element.text

        for child in list(element):
            self.__parse_element(child, parsed)

        return parsed

    @staticmethod
    def __xml_encode(row):
        xmlitem = ['  <record>']

        for field in row.index:
            if row[field]:
                xmlitem.append('    <var var_name="{0}">{1}</var>'.format(field, row[field]))

        xmlitem.append('  </record>')

        return '\n'.join(xmlitem)
