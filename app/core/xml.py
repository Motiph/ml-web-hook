from lxml import etree
from rest_framework_xml.renderers import XMLRenderer
from django.utils import six
from django.utils.encoding import smart_text
from .models import DictionaryItems

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
    try:
        xml = '<ML><StockCheck><Header Src="'+env("SOURCE")+'" Branch="'+env("BRANCH")+'"  AcctNum="'+env("ACCTNUM")+'"></Header>'
        for item in items:
            try:
                itemData = DictionaryItems.objects.get(idMercadoLibre = str(item['item_id_mercadolibre']))
                xml += '<Part Desc="" LineCode="'+str(itemData.short_brand)+'" SeqNum="1" LineNum="1" PartNum="'+str(item['part_number'])+'" QtyReq="'+str(item['item_quatity'])+'"/>'
            except DictionaryItems.DoesNotExist:
                try:
                    itemSimilar = DictionaryItems.objects.get(long_brand = str(item['brand'])).first()
                    xml += '<Part Desc="" LineCode="'+str(itemSimilar.short_brand)+'" SeqNum="1" LineNum="1" PartNum="'+str(item['part_number'])+'" QtyReq="'+str(item['item_quatity'])+'"/>'
                except DictionaryItems.DoesNotExist:
                    xml += '<Part Desc="" LineCode="nan" SeqNum="1" LineNum="1" PartNum="'+str(item['part_number'])+'" QtyReq="'+str(item['item_quatity'])+'"/>'
        xml += '</StockCheck></ML>'
        rootxml = etree.fromstring(xml)
        xmlready = b'<?xml version="1.0" encoding="UTF-8" ?>' + etree.tostring(rootxml)
        return (xmlready.decode("utf-8"))
    except Exception as excep:
        print("Error en hacer excel")

def convertxmltoJson(xmlreceived):
    try:
        root = etree.fromstring(xmlreceived)
        JsonBuild = []
        count = 0
        for StockCheck in root:
            for element in StockCheck:
                if (element.tag == 'Part'):
                    newjson = str(element.attrib).replace('{','').replace('}','').split(', ')
                    PartJson = {}
                    for attribute in newjson:
                        attributeData = attribute.split(': ')
                        PartJson[attributeData[0].replace("'","")]=attributeData[1].replace("'","")
                    JsonBuild.append(PartJson)
                    count += 1
        return JsonBuild
    except Exception as excep:
        print("ERROR EN XML A JSON")