from django.contrib import admin
from django.urls import path
from .views import (acme_webhook,
    AcmeWebhookMessageView,
    Savetoken,
    GetInfoFromML,
    GetItemsSellFromML,
    ShowOrders,
    UpdateItemMercadoLibre,
    CreateItemMercadoLibre,
    ShowNewOrders,
    DocumentUpload,
    CheckStock,
    ReadExcelToAdd,
    SendOrderToPaceSetter)
from django.conf.urls import url

urlpatterns = [
    path("webhooks/",acme_webhook),
    path('viewnotifications/',AcmeWebhookMessageView.as_view()),
    path('savetoken/',Savetoken.as_view()),
    url(r'getinfo/(?P<pk>\d+)/$', GetInfoFromML.as_view()),
    url(r'getitems/(?P<pk>\d+)/$', GetItemsSellFromML.as_view()),
    path(r'showneworders/',ShowNewOrders.as_view()),
    path(r'showorders/',ShowOrders.as_view()),
    path(r'updateitem/',UpdateItemMercadoLibre.as_view()),
    path(r'createitem',CreateItemMercadoLibre.as_view()),
    path(r'upload/',DocumentUpload.as_view()),
    path(r'check/',CheckStock.as_view()),
    path(r'readexcel/',ReadExcelToAdd.as_view()),
    path(r'send-pacesetter/',SendOrderToPaceSetter.as_view())
    ]