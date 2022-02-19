from django.db import models

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError
from django.utils import timezone

#Model to save in database the webhook Message
class AcmeWebhookMessage(models.Model):
    received_at = models.DateTimeField(help_text="Cuando se recibio el evento.")
    payload = models.TextField(default=None, null=True,help_text="Texto Json del evento.")

    def __str__(self):
        return str(self.received_at)

    class Meta:
        indexes = [
            models.Index(fields=["received_at"]),
        ]

#Reciver to create token to user
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

#Model to save the User form MercadoLibre, only save 1 element
class UserMercadoLibre(models.Model):
    client_id = models.CharField(max_length=50)
    client_secret = models.CharField(max_length=50)
    redirect_uri = models.URLField()

    def __str__(self):
        return "User"

    def save(self, *args, **kwargs):
        if not self.pk and UserMercadoLibre.objects.exists():
            raise ValidationError("Ya existe un registro de este tipo")
        else:
            return super(UserMercadoLibre,self).save(*args, **kwargs)

#method to get the Mercado Libre user
def GetUserML():
    return UserMercadoLibre.objects.all().first()

#Model to save the token to MercadoLibre API,  only save 1 element
class TokenMercadoLibre(models.Model):
    access_token = models.CharField(max_length=200)
    token_type = models.CharField(max_length=100)
    expires_in = models.CharField(max_length=50)
    scope = models.CharField(max_length=50)
    user_id = models.CharField(max_length=50)
    refresh_token = models.CharField(max_length=100)
    received_at = models.DateTimeField()

    def __str__(self):
        return str(self.received_at)

    def save(self, *args, **kwargs):
        if not self.pk and TokenMercadoLibre.objects.exists():
            raise ValidationError("Ya existe un registro de este tipo")
        else:
            return super(TokenMercadoLibre,self).save(*args, **kwargs)

#method to get the Mercado Libre token
def GetTokenML():
    return TokenMercadoLibre.objects.all().first()

#Model to save the Mercadolibre Orders, using the package ID
class OrderItemsMercadoLibre(models.Model):
    pack_id_mercadolibre = models.CharField(max_length=70)
    sending = models.BooleanField(default=False)
    xmlsending = models.TextField(null=True,help_text="XML enviado a Pacesetter.")
    received_at = models.DateTimeField()
    response = models.BooleanField(default=False)
    xmlresponse = models.TextField(null=True,help_text="XML recibido de Pacesetter")

    def __str__(self):
        return str(self.pack_id_mercadolibre)

#Model to save the items buyed in mercado libre
class ItemSellMercadoLibre(models.Model):
    item_id_mercadolibre = models.CharField(max_length=300)
    item_name_mercadolibre = models.CharField(max_length=300)
    item_quatity = models.IntegerField()
    item_price = models.DecimalField(max_digits=9, decimal_places=2, default=0.01)
    payment_id = models.CharField(max_length=300)
    received_at = models.DateTimeField(help_text="When we received the event.")
    brand = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    part_number = models.CharField(max_length=200)
    order_id = models.ForeignKey(OrderItemsMercadoLibre,on_delete=models.CASCADE,blank=True,null=True)

    def __str__(self):
        return str("% s % s"%(self.part_number,self.order_id))

#Model to save documents
class DocumentItems(models.Model):
    document = models.FileField(upload_to ='uploads/',verbose_name="Documento")
    description = models.CharField(max_length=200, blank=True, null=True,verbose_name="Descripción")
    created_at = models.DateTimeField(verbose_name="Creado en")
    updated_at = models.DateTimeField(verbose_name="Actualizado en")

    def __str__(self):
        return str(self.created_at)

    class Meta:
        verbose_name = 'Documento subido'
        verbose_name_plural = 'Documentos subidos'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
            self.updated_at = timezone.now()
            return super(DocumentItems,self).save(*args, **kwargs)
        else:
            self.updated_at = timezone.now()
            return super(DocumentItems,self).save(*args, **kwargs)


class DictionaryItems(models.Model):
    idMercadoLibre = models.CharField(max_length=200, verbose_name="ID de Mercado Libre")
    long_brand = models.CharField(max_length=200, verbose_name="Marca (Nombre Largo)")
    short_brand = models.CharField(max_length=200, verbose_name="Marca (Nombre corto)")
    number_part = models.CharField(max_length=200, blank=True, null=True,verbose_name="Número de parte")
    model = models.CharField(max_length=200, blank=True, null=True,verbose_name="Modelo")
    stock = models.IntegerField(verbose_name="Stock disponible")
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.01,verbose_name="Precio")
    
    def __str__(self):
        return str(self.idMercadoLibre)

class DictionaryBrands(models.Model):
    long_brand = models.CharField(max_length=200,verbose_name="Nombre completo de la marca")
    short_brand = models.CharField(max_length=100,verbose_name="Nombre corto de la marca")

    def __str__(self):
        return str(self.short_brand)