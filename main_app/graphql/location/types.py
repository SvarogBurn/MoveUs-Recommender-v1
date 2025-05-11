from ...models import Location
from ..object_type import MUObjectType


class LocationType(MUObjectType):
    class Meta:
        model = Location
        exclude = ('event_set', )
        

