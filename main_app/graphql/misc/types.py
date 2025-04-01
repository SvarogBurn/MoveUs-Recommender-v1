from graphene_django import DjangoObjectType

from ...models import BaseLocation, AdressLocation, InstituteLocation

class BaseLocationType(DjangoObjectType):
    class Meta:
        model = BaseException

class AdressLocationType(DjangoObjectType):
    class Meta:
        model = AdressLocation

class InstituteLocationType(DjangoObjectType):
    class Meta:
        model = InstituteLocation