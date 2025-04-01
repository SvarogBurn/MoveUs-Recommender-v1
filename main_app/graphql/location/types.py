from graphene_django import DjangoObjectType

from ...models import Location

class LocationType(DjangoObjectType):
    class Meta:
        model = Location
        exclude = ('moveususer_set', 'event_set')