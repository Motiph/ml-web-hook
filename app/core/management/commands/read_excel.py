from django.core.management.base import BaseCommand

from core.excel import readexcel


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        readexcel()