from api.graphql.object_type import MUObjectType
from main.locations.models import Location


class LocationType(MUObjectType):
    class Meta:
        model = Location
        exclude = ("event_set",)
