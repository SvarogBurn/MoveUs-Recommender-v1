import graphene

from main.event.models import Event
from main.event.services import EventService
from shared.errors.mu_error import MUError, MUErrorCode
from shared.utils.decorators import require_auth

from .types import EventType, UnfinishedEventType


class EventQuery(graphene.ObjectType):
    event = graphene.Field(EventType, id=graphene.Int())
    anonymous_user_events = graphene.List(EventType)
    joined_events = graphene.List(EventType)
    owned_events = graphene.List(EventType)
    past_joined_events = graphene.List(EventType)
    ongoing_joined_events = graphene.List(EventType)
    future_joined_events = graphene.List(EventType)
    unfinished_events = graphene.List(UnfinishedEventType)
    unrated_events = graphene.List(EventType)
    my_recommended_events = graphene.List(EventType)

    def resolve_event(root, info: graphene.ResolveInfo, id: int, **kwargs) -> Event:
        return EventService.get_event_by_id(id)

    def resolve_anonymous_user_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_anonymous_events()

    def resolve_my_recommended_events(root, info: graphene.ResolveInfo, **kwargs):
        if not info.context.user.id:
            raise MUError(MUErrorCode.AUTHENTICATION_ERROR)
        return EventService.get_recommended_events()

    @require_auth
    def resolve_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_joined_events(info.context.user.id)

    @require_auth
    def resolve_owned_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_owned_events(info.context.user.id)

    @require_auth
    def resolve_past_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_past_joined_events(info.context.user.id)

    @require_auth
    def resolve_ongoing_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_ongoing_joined_events(info.context.user.id)

    @require_auth
    def resolve_future_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_future_joined_events(info.context.user.id)

    @require_auth
    def resolve_unrated_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_unrated_events(info.context.user.id)

    @require_auth
    def resolve_unfinished_events(root, info: graphene.ResolveInfo, **kwargs):
        return EventService.get_unfinished_events(info.context.user.id)
