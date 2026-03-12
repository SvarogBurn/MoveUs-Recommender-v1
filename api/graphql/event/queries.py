import graphene
from django.db.models import Prefetch, QuerySet
from django.utils.timezone import now

from main.event.models import Event, EventMember
from shared.enums import MemberRole
from shared.errors.mu_error import MUError, MUErrorCode
from shared.utils.decorators import require_auth

from .types import EventType, UnfinishedEventType


def _event_queryset() -> QuerySet[Event]:
    return Event.objects.select_related("location", "activity").prefetch_related(
        Prefetch(
            "members",
            queryset=EventMember.objects.select_related("user"),
            to_attr="_members",
        )
    )


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
        try:
            return _event_queryset().get(pk=id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

    def resolve_anonymous_user_events(
        root, info: graphene.ResolveInfo, **kwargs
    ) -> QuerySet[Event]:
        # TODO: This should return 6 events near the anonymous user
        # This is only really used on the landing page, when the user
        # isn't signed in
        return _event_queryset().all()[:6]

    def resolve_my_recommended_events(
        root, info: graphene.ResolveInfo, **kwargs
    ) -> QuerySet[Event]:
        if not info.context.user.id:
            raise MUError(MUErrorCode.AUTHENTICATION_ERROR)
        return _event_queryset().all()

    @require_auth
    def resolve_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        user_id: int = info.context.user.id
        return _event_queryset().filter(
            id__in=EventMember.objects.filter(
                user_id=user_id,
            )
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id")
        )

    @require_auth
    def resolve_owned_events(root, info: graphene.ResolveInfo, **kwargs):
        user_id: int = info.context.user.id
        return _event_queryset().filter(
            id__in=EventMember.objects.filter(
                user_id=user_id, role=MemberRole.ORGANIZER
            ).values("event_id")
        )

    @require_auth
    def resolve_past_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        user_id: int = info.context.user.id
        time = now()
        return _event_queryset().filter(
            end_time__lte=time,
            id__in=EventMember.objects.filter(user_id=user_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @require_auth
    def resolve_ongoing_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        user_id: int = info.context.user.id
        time = now()
        return _event_queryset().filter(
            start_time__lt=time,
            end_time__gt=time,
            id__in=EventMember.objects.filter(user_id=user_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @require_auth
    def resolve_future_joined_events(root, info: graphene.ResolveInfo, **kwargs):
        user_id: int = info.context.user.id
        time = now()
        return _event_queryset().filter(
            start_time__gte=time,
            id__in=EventMember.objects.filter(user_id=user_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @require_auth
    def resolve_unrated_events(root, info: graphene.ResolveInfo, **kwargs):
        user_id: int = info.context.user.id
        return _event_queryset().filter(
            finished=True,
            id__in=EventMember.objects.filter(
                user_id=user_id, score__isnull=True, has_participated=True
            )
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @require_auth
    def resolve_unfinished_events(root, info: graphene.ResolveInfo, **kwargs):
        user_id: int = info.context.user.id

        return _event_queryset().filter(
            finished=False,
            id__in=EventMember.objects.filter(
                user_id=user_id, role__in=(MemberRole.ORGANIZER, MemberRole.MODERATOR)
            ).values("event_id"),
        )
