from api.graphql.object_type import MUObjectType
from main.location.models import Location


class LocationType(MUObjectType):
    class Meta:
        model = Location
        exclude = ("event_set",)
