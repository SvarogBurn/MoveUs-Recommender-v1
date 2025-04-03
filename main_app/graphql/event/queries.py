import graphene

from .types import EventType
from ..error import MUError, MUErrorCode
from ...models import Event

class EventQuery(graphene.ObjectType):
    my_recommended_events = graphene.List(EventType)

    def resolve_my_recommended_events(root, info, **kwargs):
        if not info.context.user.id:
            raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)
        return Event.objects.all()