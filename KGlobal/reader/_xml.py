from ..filehandler import FileHandler
from xml.etree.ElementTree import parse as xml_parse
from pandas import DataFrame
from os.path import exists, join
from datetime import datetime
from portalocker import Lock
from xml.sax.saxutils import escape


class XMLReader(FileHandler):
    def __init__(self, file_path, xmlns_rs=None, dict_var=None):
        super().__init__(file_path=file_path, xmlns_rs=xmlns_rs, dict_var=dict_var)

    def parse(self):
        if self.streams:
            for handler, buffer in self.streams:
                self.__parse(handler=handler, buffer=buffer)
        else:
            return self.__parse()

    def __parse(self, handler=None, buffer=None):
        from ..filehandler import is_an_xml

        if is_an_xml(self.file_path):
            tree = xml_parse(self.file_path)
            root = tree.getroot()
            xml_objs = root.findall(self.xmlns_rs)

            if isinstance(self.dict_var, dict):
                for item in xml_objs:
                    self.dict_var = self.__parse_element(item, self.dict_var)

                return self.dict_var
            else:
                self.__parse_xml_root(xml_objs, handler, buffer)

    @staticmethod
    def __parse_xml_root(xml_objs, handler=None, buffer=None):
        xml_dicts = list()
        row_num = 0

        for xml_obj in xml_objs:
            xml_dicts.append(self.__parse_element(xml_obj))

            if handler and buffer <= len(xml_dicts):
                handler(self.__parse_df(xml_dicts), row_num - len(xml_dicts) + 1)
                xml_dicts.clear()

            row_num += 1

        if handler:
            handler(self.__parse_df(xml_dicts), row_num - len(xml_dicts) + 1)
        else:
            return self.__parse_df(xml_dicts)

    @staticmethod
    def __parse_df(xml_dicts):
        if xml_dicts:
            df = DataFrame(xml_dicts)
            df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        else:
            df = DataFrame()

        return df

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


class XMLWriter(FileHandler):
    def __init__(self, file_dir, file_name, df=None):
        super().__init__(file_dir=file_dir, file_name=file_name, df=df)

    def write(self):
        xml_file = self.__xml_file()

        with Lock(xml_file, 'w') as xmlfile:
            xmlfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            xmlfile.write('<records>\n')
            xmlfile.write(
                '\n'.join(dataframe.apply(self.__xml_encode, axis=1))
            )
            xmlfile.write('\n</records>')

    def __xml_file(self):
        from ..filehandler import unique_id

        xml_file = join(self.file_dir, self.file_name)
        date = datetime.now()

        while exists(xml_file):
            uid = unique_id()
            xml_file = join(self.file_dir, '%s-%s-%s_%s.xml' % (date.year, date.month, date.day, uid))

        return xml_file

    def __xml_encode(self, row):
        xmlitem = ['  <record>']

        for field in row.index:
            if row[field]:
                xmlitem.append('    <var var_name="{0}">{1}</var>'.format(field, self.__handle_illegals(row[field])))

        xmlitem.append('  </record>')

        return '\n'.join(xmlitem)

    @staticmethod
    def __handle_illegals(data):
        return escape(str(data).replace('"', '&quot;').replace("'", '&apos;').replace("’", '&apos;')
                      .replace(chr(160), ' '))
