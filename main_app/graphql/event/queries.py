import graphene

from .types import EventType
from ..error import MUError, MUErrorCode
from ...models import Event

class EventQuery(graphene.ObjectType):
    event = graphene.Field(EventType, id=graphene.Int())
    my_recommended_events = graphene.List(EventType)

    def resolve_event(root, info, id, **kwargs):
        try:
            return Event.objects.get(pk=id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

    def resolve_my_recommended_events(root, info, **kwargs):
        if not info.context.user.id:
            raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)
        return Event.objects.all()