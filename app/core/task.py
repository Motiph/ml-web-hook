from __future__ import absolute_import, unicode_literals

from celery import shared_task
import requests
from django.utils import timezone
from .excel import readexcel,getItemFromMLAPI,makeexcel,UpdateItem
from .models import DictionaryItems,GetTokenML,ItemSellMercadoLibre,OrderItemsMercadoLibre
from .xml import makexml,convertxmltoJson
import json
import environ
env = environ.Env()
environ.Env.read_env()

@shared_task
def celeryReadExcel():
    message = readexcel()
    return message

@shared_task
def celeryCheckChange(request):
    itemchanged = []
    print(request)
    for item in request.get('inv',None):
        try:
            foundItem = DictionaryItems.objects.filter(long_brand=item['lineName'],number_part=item['part'])
            if(len(foundItem) > 0):
                for DataItem in foundItem:
                    if (DataItem.stock != item['instk']):
                        print("parte "+DataItem.idMercadoLibre+" cambio")
                        itemchanged.append(getItemFromMLAPI(DataItem,item))
                        UpdateItem(DataItem,item)
                    else:
                        print("parte "+item['part']+" sin cambio")
            else:
                foundItem = DictionaryItems.objects.filter(long_brand=item['lineName'],model=item['part'])
                if(len(foundItem) > 0):
                    for DataItem in foundItem:
                        if (DataItem.stock != item['instk']):
                            print("parte "+DataItem.idMercadoLibre+" cambio")
                            itemchanged.append(getItemFromMLAPI(DataItem,item))
                            UpdateItem(DataItem,item)
                        else:
                            print("parte "+item['part']+" sin cambio")
                else:
                    print("No encontrado")
        except DictionaryItems.DoesNotExist:
            print("No encontrado")

        except Exception as excep:
            print(excep)

    makeexcel(itemchanged)
    message = "Cambiaron "+str(len(itemchanged))+"items"
    return (message)

@shared_task
def celeryProcessWebhookPayload(payload):
    try:
        #Get the token
        tokenSave = GetTokenML()
        headers = {'Authorization': 'Bearer '+tokenSave.access_token}
        #if exist resource in the JSON, search the payment
        if (payload['resource']):
            datasplit = payload['resource'].split('/')
            urlpayments = env("APIURLMP")+"v1/payments/"+str(datasplit[2])
            responsepayments = requests.get(urlpayments, headers=headers)
            jsonresponsepayments = responsepayments.json()
            idorders = jsonresponsepayments['order']['id']
            #print(idorders)
            statuspayment = str(jsonresponsepayments['status'])
            #if the payment are aprroved, get the order
            if statuspayment == 'approved':
                urlorders = env("APIURLML")+'orders/'+str(idorders)
                responserorders  = requests.get(urlorders, headers=headers)
                jsonresponseorders = responserorders.json()
                #print(jsonresponseorders)
                #get all items from the package
                urlshipment = env("APIURLML")+'shipments/'+str(jsonresponseorders['shipping']['id'])
                shipments = requests.get(urlshipment, headers=headers)
                jsonshipments = shipments.json()
                itemsorders = jsonshipments['shipping_items']
                #print(itemsorders)
                orderid = None
                packid = jsonresponseorders['pack_id']
                firstrecord = False
                if packid is None:
                    packid = idorders
                #if the order exist, get the data from it
                if OrderItemsMercadoLibre.objects.filter(pack_id_mercadolibre=str(packid)).exists():
                    orderid = OrderItemsMercadoLibre.objects.get(pack_id_mercadolibre=str(packid))
                #else, save the order
                else:
                    orderid = OrderItemsMercadoLibre.objects.create(
                        pack_id_mercadolibre = packid,
                        received_at=timezone.now()
                    )
                    firstrecord = True
                #save the items
                items = []
                brand = 'None'
                model = 'None'
                part_number = 'None'
                #get the item data
                for item in itemsorders:
                    urlitems = env("APIURLML")+"items/"+str(item['id'])
                    responseitems = requests.get(urlitems, headers=headers)
                    jsonresponseitems = responseitems.json()
                    #get the attributes from the item
                    for attributes in jsonresponseitems['attributes']:
                        if attributes['id'] == 'BRAND':
                            brand = attributes['value_name']
                        if attributes['id'] == 'MODEL':
                            if (attributes['value_name']) is not None:
                                model = attributes['value_name']
                        if attributes['id'] == 'PART_NUMBER':
                            if (attributes['value_name']) is not None:
                                part_number = attributes['value_name']

                    newitem = {
                        "item_id_mercadolibre":item['id'],
                        "item_name_mercadolibre":item['description'],
                        "item_quatity":item['quantity'],
                        "item_price":jsonresponseitems['price'],
                        "payment_id":datasplit[2],
                        "received_at":timezone.now(),
                        "brand":brand,
                        "model":model,
                        "part_number":part_number,
                        "order_id":orderid
                        }
                    items.append(newitem)
                #if the item from the order exist, ignore.
                if firstrecord != True:
                    return("Ya se registro antes")
                #if not, save.
                else:
                    for item in items:
                        ItemSellMercadoLibre(**item).save()
                    orderid.sending = True
                    orderid.save()
                    xmlToSend = makexml(items,orderid)
                    print(xmlToSend)
                    #send to pacesetter and save xml in order, the response its fake
                    #remove the # to activate pacesetter
                    #r = requests.post('http://131.226.252.227:9319', data=xmlToSend)
                    #xmlreceived = r.text
                    xmlreceived = b'<?xml version= \"1.0\"?>\r\n<ML TransId= \"MLM937625594\"><orderconf><header account= \"900\" branch= \"01\" errcode= \"\" orderdate= \"2022-01-21 13:58:49 MST\" orderno= \"220121135808\" ponumber= \"99994\" state= \"success\" type= \"Normal\"><routing /></header><part core= \"0\" cost= \"307.06\" errcode= \"success\" errmsg= \"success\" linecode= \"CEN\" list= \"315.41\" partno= \"102.00300\" qtyavail= \"2\" qtyreq= \"1\" qtysup= \"1\" /></orderconf></ML>'
                    xmltostring = xmlreceived.decode("utf-8")
                    jsonToXML = convertxmltoJson(xmlreceived)
                    orderid.response = True
                    orderid.xmlresponse = xmltostring
                    orderid.save()
                    print(type(jsonToXML))
                    #update item in mercadolibre
                    success = 0
                    fail = 0
                    for item in jsonToXML:
                        #make a format to send to mercado libre API
                        print(item["partno"])
                        if int(item['qtyreq']) > 0:
                            try:
                                itemsDict = DictionaryItems.objects.filter(number_part=item['partno'],short_brand=item['linecode'])
                                for itemDict in itemsDict:
                                    print(itemDict.idMercadoLibre)
                                    data = {}
                                    data["available_quantity"]= int(item['qtyavail']) - int(item['qtyreq'])
                                    url = env("APIURLML")+'items/'+str(itemDict.idMercadoLibre)
                                    response = requests.put(url, headers=headers,data=json.dumps(data))
                                    responsejson = response.json()
                                    if 'id' in responsejson:
                                        success += 1
                                    else:
                                        fail += 1
                                    #update in dictionary model the stock
                                    objItemDict = DictionaryItems.objects.get(pk=itemDict.id)
                                    objItemDict.stock = int(item['qtyavail']) - int(item['qtyreq'])
                                    objItemDict.save()
                            except DictionaryItems.DoesNotExist:
                                fail += 1
                        else:
                            print(item["partno"]+"menor a cero")
                    return("Se actualizaron "+str(success)+" y hubo error en "+str(fail))
            #if not, only are a change in the payment
            else:
                return("Cambio en el pago")
    except Exception as excep:
        print(excep)