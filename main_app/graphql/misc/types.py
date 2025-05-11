import graphene
from ..object_type import MUObjectType

from ...models import Location

class LocationType(MUObjectType):
    class Meta:
        model = Location

class AttachmentType(graphene.ObjectType):
    id = graphene.String()
    url = graphene.String()