import openpyxl
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import DictionaryItems

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        xlsx_file = Path('brands.xlsx')
        wb_obj = openpyxl.load_workbook(xlsx_file)
        sheet = wb_obj.active

        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            try:
                brand = DictionaryItems.objects.get(long_brand=row[0].lower())
                brand.short_brand = row[1]
                brand.save()
            except DictionaryItems.DoesNotExist:
                pass