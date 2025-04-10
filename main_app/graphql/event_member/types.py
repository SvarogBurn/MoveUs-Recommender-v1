from main_app.graphql.object_type import MUObjectType
from main_app.models.event import EventMember


class EventMemberType(MUObjectType):
    
    class Meta:
        model = EventMember
        exclude = ("pk",)