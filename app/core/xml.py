from lxml import etree
from rest_framework_xml.renderers import XMLRenderer
from django.utils import six
from django.utils.encoding import smart_text

import environ
env = environ.Env()
environ.Env.read_env()

class XMLCustomRenderer(XMLRenderer):
    root_tag_name = 'ML'

    def _to_xml(self, xml, data):

        # This will True if the current element is an instance of a model
        if isinstance(data, list):

            for item in data:

                xml.startElement('StockCheck', {})
                self._to_xml(xml, item)
                xml.endElement("StockCheck")

        # This will True if the current element is an instance of a model's field
        elif isinstance(data, (dict,tuple)):
            for key, value in six.iteritems(data):
                if key != 'Part':
                    xml.startElement(key,value['attributes'] )
                    self._to_xml(xml, value['value'])
                    xml.endElement(key)
                else:
                    for data in value:
                        xml.startElement("Part",data['attributes'])
                        self._to_xml(xml, "")
                        xml.endElement("Part")

        elif data is None:
            # Don't output any value
            pass

        else:
            xml.characters(smart_text(data))


def makexml(items):
    xml = '<ML><StockCheck><Header Src="'+env("SOURCE")+'" Branch="'+env("BRANCH")+'"  AcctNum="'+env("ACCTNUM")+'"></Header>'
    for item in items:
        xml += '<Part Desc="" LineCode="'+str(item['brand'])+'" SeqNum="1" LineNum="1" PartNum="'+str(item['part_number'])+'" QtyReq="'+str(item['item_quatity'])+'"/>'
    xml += '</StockCheck></ML>'
    rootxml = etree.fromstring(xml)
    xmlready = b'<?xml version="1.0" encoding="UTF-8" ?>' + etree.tostring(rootxml)
    return (xmlready.decode("utf-8"))