from datetime import timedelta
import json
import requests

from django.db.transaction import atomic, non_atomic_requests
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.parsers import FileUploadParser
from rest_framework.exceptions import ParseError
import environ
env = environ.Env()
environ.Env.read_env()


import rest_framework_xml

from .models import (AcmeWebhookMessage,
GetUserML,TokenMercadoLibre,
GetTokenML,ItemSellMercadoLibre,
OrderItemsMercadoLibre,DocumentItems)

from .xml import XMLCustomRenderer,makexml

#method to change token after 3 hours having been created
def changeToken():
    token = GetTokenML()
    user = GetUserML()
    actualdate = timezone.now()
    tokendate = token.received_at + timedelta(hours=3)
    #check if the actual hour its mayor to make a new token
    if (actualdate > tokendate):
        headers ={
            'accept':'application/json',
            'content-type':'application/x-www-form-urlencoded'
        }
        data ={
            'grant_type':'refresh_token',
            'client_id':user.client_id,
            'client_secret':user.client_secret,
            'refresh_token':token.refresh_token
        }
        url = env("APIURLML")+'oauth/token'
        response = requests.post(url, headers=headers,data=json.dumps(data))
        jsonResponse = response.json()
        tokenSave = GetTokenML()
        tokenSave.access_token=jsonResponse['access_token']
        tokenSave.token_type=jsonResponse['token_type']
        tokenSave.expires_in=jsonResponse['expires_in']
        tokenSave.scope=jsonResponse['scope']
        tokenSave.user_id=jsonResponse['user_id']
        tokenSave.refresh_token=jsonResponse['refresh_token']
        tokenSave.received_at=actualdate
        tokenSave.save()

# Method to save the webhook messages
@csrf_exempt
@require_POST
@non_atomic_requests
def acme_webhook(request):
    #clear the  messages from 5 days old
    AcmeWebhookMessage.objects.filter(
        received_at__lte=timezone.now() - timedelta(days=5)
    ).delete()
    #Get the JSON messages, check the token and save.
    payload = json.loads(request.body)
    changeToken()
    AcmeWebhookMessage.objects.create(
        received_at=timezone.now(),
        payload=payload,
    )
    #Go to another method to proccess the data.
    process_webhook_payload(payload)
    return HttpResponse("Message received okay.", content_type="text/plain")

#Method to proccess to save the order and item
@atomic
def process_webhook_payload(payload):
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

#method to show the webhook message recived.
class AcmeWebhookMessageView(APIView):
    def get(self, request,format=None):
        try:
            #get the new token
            changeToken()
            #get the messages, order to last to new.
            data = AcmeWebhookMessage.objects.order_by('-id').values()
            array_messages = []
            #make a format to show
            for message in data:
                dict_message = {
                    "id":message['id'],
                    #subtract 7 hours using mysql
                    "received_at":message['received_at'],
                    #"received_at":message['received_at']+ timedelta(hours=-7),
                    "payload":message['payload']
                    }
                array_messages.append(dict_message)
            return Response(array_messages,status=status.HTTP_200_OK)
        except AcmeWebhookMessage.DoesNotExist:
            return Response(None,status=status.HTTP_400_BAD_REQUEST)

#method to save the mercado libre token user
class Savetoken(APIView):
    #allow all user to user this view
    authentication_classes = []
    permission_classes = []
    def get(self, request,format=None):
        try:
            #get the data form the mercado libre user
            user = GetUserML()
            #get the code recived in the url from mercado libre redirect
            code = request.query_params['code']
            #headers and data to make a request
            headers = {'accept': 'application/json','content-type': 'application/x-www-form-urlencoded'}
            data = {'grant_type':'authorization_code',
            'client_id':user.client_id,
            'client_secret':user.client_secret,
            'code':code,
            'redirect_uri':user.redirect_uri}
            url = env("APIURLML")+'oauth/token'
            #request to mercado libre to get the token
            response = requests.post(url, headers=headers,data=json.dumps(data))
            jsonResponse = response.json()
            print(jsonResponse)
            #if the token data exist, only override the information
            if TokenMercadoLibre.objects.exists():
                tokenSave = GetTokenML()
                tokenSave.access_token=jsonResponse['access_token']
                tokenSave.token_type=jsonResponse['token_type']
                tokenSave.expires_in=jsonResponse['expires_in']
                tokenSave.scope=jsonResponse['scope']
                tokenSave.user_id=jsonResponse['user_id']
                tokenSave.refresh_token=jsonResponse['refresh_token']
                tokenSave.received_at=timezone.now()
                tokenSave.save()
            #if not, write the data
            else:
                tokenSave = TokenMercadoLibre(access_token=jsonResponse['access_token'],
                token_type=jsonResponse['token_type'],
                expires_in=jsonResponse['expires_in'],
                scope=jsonResponse['scope'],
                user_id=jsonResponse['user_id'],
                refresh_token=jsonResponse['refresh_token'],
                received_at=timezone.now())
                tokenSave.save()
            return Response(jsonResponse,status=status.HTTP_200_OK)
        except Exception as excep:
            return Response(excep,status=status.HTTP_400_BAD_REQUEST)

#method to get the information from mercado libre message
class GetInfoFromML(APIView):
    def get(self, request,pk,format=None):
        try:
            changeToken()
            tokenSave = GetTokenML()
            webhookMessage = AcmeWebhookMessage.objects.get(id=pk)
            headers = {'Authorization': 'Bearer '+tokenSave.access_token}
            data = json.loads(webhookMessage.payload.replace("'", '"'))
            data = data
            print(type(data))
            if (data['resource']):
                datasplit = data['resource'].split('/')
                print(datasplit[2])
                url = "https://api.mercadolibre.com"+data['resource']
                response = requests.get(url, headers=headers)
                jsonResponse = response.json()
                return Response(jsonResponse,status=status.HTTP_200_OK)
            else:
                return Response("Invalid message",status=status.HTTP_400_BAD_REQUEST)
        except AcmeWebhookMessage.DoesNotExist:
            return Response("Invalid message",status=status.HTTP_400_BAD_REQUEST)
        except data.NameError:
            return Response("Invalid message",status=status.HTTP_400_BAD_REQUEST)
        except Exception as excep:
            return Response(excep.json(),status=status.HTTP_400_BAD_REQUEST)

#method to get the items from the mercadolibre order, deprecated
class GetItemsSellFromML(APIView):
    def get(self, request,pk,format=None):
        try:
            changeToken()
            tokenSave = GetTokenML()
            webhookMessage = AcmeWebhookMessage.objects.get(id=pk)
            headers = {'Authorization': 'Bearer '+tokenSave.access_token}
            data = json.loads(webhookMessage.payload.replace("'", '"'))
            if (data['resource']):
                datasplit = data['resource'].split('/')
                urlpayments = env("APIURLMP")+"v1/payments/"+str(datasplit[2])
                responsepayments = requests.get(urlpayments, headers=headers)
                jsonresponsepayments = responsepayments.json()
                idorders = jsonresponsepayments['order']['id']
                urlorders = env("APIURLML")+'orders/'+str(idorders)
                responserorders  = requests.get(urlorders, headers=headers)
                jsonresponseorders = responserorders.json()
                print(str(jsonresponseorders['shipping']['id']))
                urlshipment = env("APIURLML")+'shipments/'+str(jsonresponseorders['shipping']['id'])
                shipments = requests.get(urlshipment, headers=headers)
                jsonshipments = shipments.json()
                itemsorders = jsonshipments['shipping_items']
                items = []
                brand = 'None'
                model = 'None'
                part_number = 'None'
                for item in itemsorders:
                    urlitems = env("APIURLML")+"items/"+str(item['id'])
                    responseitems = requests.get(urlitems, headers=headers)
                    jsonresponseitems = responseitems.json()
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
                        "part_number":part_number
                        }
                    items.append(newitem)

                if ItemSellMercadoLibre.objects.filter(payment_id=str(datasplit[2])).exists():
                    print("ya esta guardado")
                    pass
                else:
                    for item in items:
                        ItemSellMercadoLibre(**item).save()
                    makexml(items)
                return Response(items,status=status.HTTP_200_OK)
        except AcmeWebhookMessage.DoesNotExist:
            return Response("NO ENCONTRADO",status=status.HTTP_400_BAD_REQUEST)
        except data.NameError:
            return Response("ERROR EN DATOS",status=status.HTTP_400_BAD_REQUEST)
        except Exception as excep:
            return Response(excep.json(),status=status.HTTP_400_BAD_REQUEST)


#method to show all orders
class ShowOrders(APIView):
    def get(self, request,format=None):
        data = {}
        #make a for to get the order and items from it
        for result in OrderItemsMercadoLibre.objects.all():
            items = ItemSellMercadoLibre.objects.filter(order_id = result.id).values()
            dataorder = {
                'pack_id_mercadolibre':result.pack_id_mercadolibre,
                'sending':result.sending,
                'received_at':result.received_at,
                'items':items
                }
            data[result.id] = dataorder
        return Response(data,status=status.HTTP_200_OK)


#method to show the new orders
class ShowNewOrders(APIView):
    parser_classes = [rest_framework_xml.parsers.XMLParser]
    renderer_classes = [XMLCustomRenderer]
    def get(self, request,format=None):
        dataxml = []
        root = [
                {
                    'Header':
                        {
                            "value":"",
                            'attributes': {
                                'Src': env("SOURCE"),
                                'Branch': env("BRANCH"),
                                'AcctNum':env("ACCTNUM")
                                }
                        },
                }]
        #make a for to get the order and items from it, excluding when are sent before
        for result in OrderItemsMercadoLibre.objects.exclude(sending=True):
            items = ItemSellMercadoLibre.objects.filter(order_id = result.id).values()
            makexml(items)
            result.sending = True
            result.save()

            for item in items:
                Part ={
                "value":"",
                        'attributes': {
                            'Desc': "",
                            'LineCode': str(item['brand']),
                            'SeqNum':"1",
                            "LineNum":"1",
                            "PartNum":str(item['part_number']),
                            "QtyReq":str(item['item_quatity'])
                            }
                }
                dataxml.append(Part)

            if len(dataxml) > 0:
                root = [
                {
                    'Header':
                        {
                            "value":"",
                            'attributes': {
                                'Src': env("SOURCE"),
                                'Branch': env("BRANCH"),
                                'AcctNum':env("ACCTNUM")
                                }
                        },
                    'Part':dataxml,
                }]

        return Response(root,status=status.HTTP_200_OK)



#method to update item in mercado libre, only update the quantity and price
class UpdateItemMercadoLibre(APIView):
    def put(self, request,format=None):
        try:
            #change and get the token
            changeToken()
            tokenSave = GetTokenML()
            #make a format to send to mercado libre API
            data = {}
            quantity = request.data.get('quantity',None)
            price = request.data.get('price',None)
            #if the price and quantity are none, ignore
            if quantity is not None:
                data["available_quantity"]= quantity
            if price is not None:
                data["price"]= price
            item = request.data['item']
            #send the request to mercado libre and show the result
            headers = {'Authorization': 'Bearer '+tokenSave.access_token}
            url = env("APIURLML")+'items/'+str(item)
            response = requests.put(url, headers=headers,data=json.dumps(data))
            responsejson = response.json()
            if 'id' in responsejson:
                return Response(responsejson,status=status.HTTP_200_OK)
            else:
                return Response(responsejson,status=status.HTTP_400_BAD_REQUEST)
        except Exception as excep:
            return Response(excep.json(),status=status.HTTP_400_BAD_REQUEST)

#method to create a new item in mercadolibre
class CreateItemMercadoLibre(APIView):
    def post (self, request,format=None):
        try:
            #change and get the token
            changeToken()
            tokenSave = GetTokenML()
            print("paso token y cambio")
            headers = {'Authorization': 'Bearer '+tokenSave.access_token}
            url = env("APIURLML")+'items'
            itemsCreated = {}
            #make a for to get all new items to add
            for item in request.data.get('items',None):
                title = item['title']
                category_string = item['category']
                price = item['price']
                available_quantity = item['quantity']
                warranty_time = item['warranty']
                warranty_type = item['warranty_type']
                pictures = item['pictures']
                attributes = item['attributes']
                description = item['description']

                #to save multiple pictures, we need a format
                jsonpictures = []
                for picture in pictures:
                    jsonpictures.append({'source':picture})
                print(item)

                #search the category, in the original string are " category > subcategory"
                category_id = ""
                firstcategory = True
                #split the string
                stringcategories = category_string.split(' > ')
                #search following the order in the string
                for category in stringcategories:
                    if firstcategory == True:
                        categoryresponse = requests.get(env("APIURLML")+'sites/MLM/categories')
                        categoryresponsejson =categoryresponse.json()
                        for responsecat in categoryresponsejson:
                            if category == responsecat['name']:
                                category_id = responsecat['id']
                                firstcategory = False
                                break
                    else:
                        categoryresponse = requests.get(env("APIURLML")+'categories/'+category_id)
                        categoryresponsejson =categoryresponse.json()
                        for responsecat in categoryresponsejson['children_categories']:
                            if category == responsecat['name']:
                                category_id = responsecat['id']
                                break


                #get the attributes from the item
                attributesarray = []
                attributesarray.append({'id':"BRAND",'value_name':attributes['Marca']})
                attributesarray.append({'id':"PART_NUMBER",'value_name':attributes['Numero_parte']})
                attributes.pop("Marca")
                attributes.pop("Numero_parte")
                if attributes.get('Modelo'):
                    attributesarray.append({'id':"MODEL",'value_name':attributes['Modelo']})
                    attributes.pop('Modelo')
                if attributes.get('SKU'):
                    attributesarray.append({'id':"SELLER_SKU",'value_name':attributes['SKU']})
                    attributes.pop('SKU')


                #get the optional attributes from the item
                attributesresponse = requests.get(env("APIURLML")+'categories/'+category_id+'/attributes')
                attributesresponsejson = attributesresponse.json()
                for id,attribute in attributes.items():
                    for atribbuteml in attributesresponsejson:
                        if id == atribbuteml['name']:
                            attributesarray.append({'id':atribbuteml['id'],'value_name':attribute})


                #format the item data
                data = {
                    'title':title,
                    'category_id':category_id,
                    'price':price,
                    'currency_id':"MXN",
                    'available_quantity':available_quantity,
                    'buying_mode':"buy_it_now",
                    'condition':"new",
                    'listing_type_id':"gold_pro",
                    'sale_terms':[
                        {
                            'id':"WARRANTY_TYPE",
                            'value_name':str(warranty_type)
                        },
                        {
                            'id':"WARRANTY_TIME",
                            'value_name':str(warranty_time)
                        }
                    ],
                    'pictures':jsonpictures,
                    'attributes':attributesarray
                }

                #upload to the mercado libre API
                response = requests.post(url, headers=headers,data=json.dumps(data))
                responsejson = response.json()
                #upload the description
                itemML = responsejson['id']
                jsondescription = {'plain_text':description}
                urldescription = env("APIURLML")+"items/"+str(itemML)+"/description"
                responsedescription = requests.post(urldescription, headers=headers,data=json.dumps(jsondescription))
                responsedescriptionjson = responsedescription.json()
                #add the description to the response from the item request
                responsejson["description"] = responsedescriptionjson
                itemsCreated[responsejson["title"]] = responsejson

            return Response(itemsCreated,status=status.HTTP_200_OK)
        except Exception as excep:
            return Response(excep,status=status.HTTP_400_BAD_REQUEST)

#Method to Upload documents
class DocumentUpload(APIView):
    parser_class = (FileUploadParser)
    def put(self, request, format=None):
        print(request.data)
        #if not exist document, make a error
        description = request.data.get('description',None)
        if 'document' not in request.data:
            raise ParseError("Empty content")
        #if the document exist, save in a variable and add to the data format
        document = request.data['document']
        created_at = timezone.now()
        updated_at = created_at
        data = {
                "document" : document,
                "description":description,
                "created_at" : created_at,
                "updated_at" : updated_at
            }
        #save the document
        DocumentItems(**data).save()
        return Response(status=status.HTTP_201_CREATED)

