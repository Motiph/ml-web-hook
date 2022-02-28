import os
import json
import requests

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.excel import getItemFromMLAPI,makeexcel,UpdateItem
from core.models import DictionaryItems,GetUserML,GetTokenML

import environ
env = environ.Env()
environ.Env.read_env()

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

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        #method to update token
        changeToken()
        #name of the json
        jsonName= 'update.json'
        with open(jsonName, 'r') as jsonRaw:
            request = json.load(jsonRaw)
            itemchanged = []
            for item in request.get('inv',None):
                try:
                    foundItem = DictionaryItems.objects.filter(short_brand=item['lineName'],number_part=item['part'])
                    if(len(foundItem) > 0):
                        for DataItem in foundItem:
                            if (DataItem.stock != item['instk']):
                                print("parte "+DataItem.idMercadoLibre+" cambio")
                                itemchanged.append(getItemFromMLAPI(DataItem,item))
                                UpdateItem(DataItem,item)
                            else:
                                print("parte "+item['part']+" sin cambio")
                    else:
                        foundItem = DictionaryItems.objects.filter(short_brand=item['lineName'],model=item['part'])
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
            message = "Cambiaron "+str(len(itemchanged))+" items"
            print(message)

        if os.path.exists(jsonName):
            os.remove(jsonName)
        else:
            print("The file does not exist")