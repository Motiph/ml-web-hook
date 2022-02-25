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

# @shared_task
# def celeryCheckChange(request):
#     itemchanged = []
#     print(request)
#     for item in request.get('inv',None):
#         try:
#             foundItem = DictionaryItems.objects.filter(long_brand=item['lineName'],number_part=item['part'])
#             if(len(foundItem) > 0):
#                 for DataItem in foundItem:
#                     if (DataItem.stock != item['instk']):
#                         print("parte "+DataItem.idMercadoLibre+" cambio")
#                         itemchanged.append(getItemFromMLAPI(DataItem,item))
#                         UpdateItem(DataItem,item)
#                     else:
#                         print("parte "+item['part']+" sin cambio")
#             else:
#                 foundItem = DictionaryItems.objects.filter(long_brand=item['lineName'],model=item['part'])
#                 if(len(foundItem) > 0):
#                     for DataItem in foundItem:
#                         if (DataItem.stock != item['instk']):
#                             print("parte "+DataItem.idMercadoLibre+" cambio")
#                             itemchanged.append(getItemFromMLAPI(DataItem,item))
#                             UpdateItem(DataItem,item)
#                         else:
#                             print("parte "+item['part']+" sin cambio")
#                 else:
#                     print("No encontrado")
#         except DictionaryItems.DoesNotExist:
#             print("No encontrado")

#         except Exception as excep:
#             print(excep)

#     makeexcel(itemchanged)
#     message = "Cambiaron "+str(len(itemchanged))+"items"
#     return (message)
