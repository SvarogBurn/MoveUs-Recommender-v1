import graphene
from django.utils.timezone import now

from main_app.models.enums import MemberRole
from main_app.util import require_auth

from ...models import Event, EventMember
from ..error import MUError, MUErrorCode
from .types import EventType, UnfinishedEventType


class EventQuery(graphene.ObjectType):
    event = graphene.Field(EventType, id=graphene.Int())
    joined_events = graphene.List(EventType)
    owned_events = graphene.List(EventType)
    past_joined_events = graphene.List(EventType)
    ongoing_joined_events = graphene.List(EventType)
    future_joined_events = graphene.List(EventType)
    unfinished_events = graphene.List(UnfinishedEventType)
    unrated_events = graphene.List(EventType)
    my_recommended_events = graphene.List(EventType)

    def resolve_event(root, info, id, **kwargs):
        try:
            return Event.objects.get(pk=id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

    def resolve_my_recommended_events(root, info, **kwargs):
        if not info.context.user.id:
            raise MUError(MUErrorCode.AUTHENTICATION_ERROR)
        return Event.objects.all()
    
    @require_auth
    def resolve_joined_events(root, info, **kwargs):
        user_id: int = info.context.user.id
        return Event.objects.filter(
            id__in=EventMember.objects.filter(
                user_id=user_id,
            ).exclude(
                role=MemberRole.ORGANIZER
            ).values("event_id")
        )
    
    @require_auth
    def resolve_owned_events(root, info, **kwargs):
        user_id: int = info.context.user.id
        return Event.objects.filter(
            id__in=EventMember.objects.filter(
                user_id=user_id,
                role=MemberRole.ORGANIZER
            ).values("event_id")
        )
    
    @require_auth
    def resolve_past_joined_events(root, info, **kwargs):
        user_id: int = info.context.user.id
        time = now()
        return Event.objects.filter(
            end_time__lte=time,
            id__in=EventMember.objects.filter(
                user_id=user_id
            ).exclude(
                role=MemberRole.ORGANIZER
            ).values("event_id")
        )
    
    @require_auth
    def resolve_ongoing_joined_events(root, info, **kwargs):
        user_id: int = info.context.user.id
        time = now()
        return Event.objects.filter(
            start_time__lt=time,
            end_time__gt=time,
            id__in=EventMember.objects.filter(
                user_id=user_id
            ).exclude(
                role=MemberRole.ORGANIZER
            ).values("event_id")
        )
    
    @require_auth
    def resolve_future_joined_events(root, info, **kwargs):
        user_id: int = info.context.user.id
        time = now()
        return Event.objects.filter(
            start_time__gte=time,
            id__in=EventMember.objects.filter(
                user_id=user_id
            ).exclude(
                role=MemberRole.ORGANIZER
            ).values("event_id")
        )
    
    @require_auth
    def resolve_unrated_events(root, info, **kwargs):
        user_id: int = info.context.user.id
        return Event.objects.filter(
            finished=True,
            id__in=EventMember.objects.filter(
                user_id=user_id,
                score__isnull=True,
                has_participated=True
            ).exclude(role=MemberRole.ORGANIZER)
            .values("event_id")
        )
    
    @require_auth
    def resolve_unfinished_events(root, info, **kwargs):
        user_id: int = info.context.user.id

        return Event.objects.filter(
            finished=False,
            id__in=EventMember.objects.filter(
                user_id=user_id,
                role__in=(MemberRole.ORGANIZER, MemberRole.MODERATOR)
            ).values('event_id')
        )
