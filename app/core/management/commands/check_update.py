import os
from django.core.management.base import BaseCommand
from core.excel import getItemFromMLAPI,makeexcel,UpdateItem
from core.models import DictionaryItems
import json

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
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
            message = "Cambiaron "+str(len(itemchanged))+"items"
            print(message)

        if os.path.exists(jsonName):
            os.remove(jsonName)
        else:
            print("The file does not exist")