from django.core.management.base import BaseCommand
from core.models import DictionaryBrands
import json


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        #put the json in the same place where stay the excel in the folder app
        with open('data.json', 'r') as f:
            #only to count and print how registred and skipped
            newsBrands = 0
            skipBrands = 0
            #read the json file
            data = json.load(f)
            #check each item if exist
            for item in data:
                try:
                    searchItem = DictionaryBrands.objects.get(short_brand=item["short"])
                    skipBrands += 1
                #if dont exist, add to the dictionary
                except DictionaryBrands.DoesNotExist:
                    #change the long and short for the real names in the json
                    JsonToSave={
                        "long_brand":item["long"],
                        "short_brand":item["short"]
                    }
                    DictionaryBrands(**JsonToSave).save()
                    newsBrands += 1
        #print the results
        print("Se registraron: "+str(newsBrands)+" y se omitieron: "+str(skipBrands))