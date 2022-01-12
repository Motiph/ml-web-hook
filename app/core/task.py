from __future__ import absolute_import, unicode_literals

from celery import shared_task
import requests
from django.utils import timezone
from .excel import readexcel,getItemFromMLAPI,makeexcel,UpdateItem
from .models import DictionaryItems,GetTokenML,ItemSellMercadoLibre,OrderItemsMercadoLibre
from .xml import makexml
import environ
env = environ.Env()
environ.Env.read_env()

@shared_task
def celeryReadExcel():
    readexcel()

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
            print(idorders)
            statuspayment = str(jsonresponsepayments['status'])
            #if the payment are aprroved, get the order
            if statuspayment == 'approved':
                urlorders = env("APIURLML")+'orders/'+str(idorders)
                responserorders  = requests.get(urlorders, headers=headers)
                jsonresponseorders = responserorders.json()
                print(jsonresponseorders)
                #get all items from the package
                urlshipment = env("APIURLML")+'shipments/'+str(jsonresponseorders['shipping']['id'])
                shipments = requests.get(urlshipment, headers=headers)
                jsonshipments = shipments.json()
                itemsorders = jsonshipments['shipping_items']
                print(itemsorders)
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
                            model = attributes['value_name']
                        if attributes['id'] == 'PART_NUMBER':
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
                    print("Ya se registro antes")
                #if not, save.
                else:
                    for item in items:
                        ItemSellMercadoLibre(**item).save()
                    orderid.sending = True
                    orderid.save()
                    xmlreceived = b'<?xml version="1.0" encoding="UTF-8" ?><ML><StockCheck><Header Src="ML" Branch="01" AcctNum="5000"/><Part Desc="" LineCode="Fram" SeqNum="1" LineNum="1" PartNum="PH9C" QtyReq="1"/></StockCheck></ML>'
                    xmltostring = xmlreceived.decode("utf-8")
                    xmlslpit = xmltostring.split('<')
                    print(makexml(items))
                    orderid.response = True
                    orderid.xmlresponse = xmltostring
                    orderid.save()

            #if not, only are a change in the payment
            else:
                print("Cambio en el pago")
    except Exception as excep:
        print(excep)