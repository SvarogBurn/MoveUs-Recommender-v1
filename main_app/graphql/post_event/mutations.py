import graphene
from django.utils.timezone import now

from main_app.graphql.error import MUError, MUErrorCode
from main_app.graphql.event.types import EventType
from main_app.models import EventMember, EventMemberLike, User
from main_app.models.enums import EventRating, MemberRole
from main_app.util import (
    get_event,
    get_event_with_member,
    require_auth,
    send_event_finished_notification,
)


class ConfirmMemberParticipationMutation(graphene.Mutation):
    
    class Arguments:
        event_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)
        participated = graphene.Boolean(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info, event_id: int, user_id: int, participated: bool):
        user: User = info.context.user

        get_event(event_id, user.id, MemberRole.MODERATOR)

        try:
            member = EventMember.objects.get(pk = (user_id, event_id))
            if member.role == MemberRole.PARTICIPANT:
                member.has_participated = participated
                member.save()
                return ConfirmMemberParticipationMutation(success=True)
        except EventMember.DoesNotExist:
            pass

        raise MUError(MUErrorCode.CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER)
    
class FinishEventMutation(graphene.Mutation):
    
    class Arguments:
        event_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info, event_id: int):
        user: User = info.context.user

        event = get_event(event_id, user.id, MemberRole.ORGANIZER)

        if now() < event.end_time:
            raise MUError(MUErrorCode.CANNOT_FINISH_BEFORE_END)
        
        if EventMember.objects.filter(
            event_id = event_id,
            participates = True,
            has_participated__isnull = True
        ).count() != 0: raise MUError(MUErrorCode.CANNOT_FINISH_WITH_UNCONFIRMED)

        event.finished = True;
        event.save();
        send_event_finished_notification(event_id)

        return FinishEventMutation(success = True)
    
class RateEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        score = EventRating.as_graphene_enum()(required=True)
        comment = graphene.String(required=False)

    event = graphene.Field(EventType)

    @require_auth
    def mutate(self, info, event_id: int, score: EventMember, comment: str = None):
        user: User = info.context.user;

        event, member = get_event_with_member(event_id, user.id, MemberRole.PARTICIPANT)

        if comment and len(comment) > 512:
            raise MUError(MUErrorCode.RATE_COMMENT_MAX_LENGTH)

        if not event.finished:
            raise MUError(MUErrorCode.CANNOT_RATE_UNFINISHED_EVENT)
        
        if member.role == MemberRole.ORGANIZER:
            return MUError(MUErrorCode.CANNOT_RATE_OWN_EVENT)
        
        if not member.has_participated:
            return MUError(MUErrorCode.CANNOT_RATE_NO_PARTICIPATION)
        
        member.score = score;
        if comment:
            member.comment = comment
        
        member.save()

        return RateEventMutation(event=event)
    
class LikeEventMemberMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)
        like = graphene.Boolean(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info, event_id: int, user_id: int, like: bool):
        user: User = info.context.user

        if user.id == user_id:
            raise MUError(MUErrorCode.CANNOT_LIKE_YOURSELF)

        event, member = get_event_with_member(event_id, user.id, MemberRole.PARTICIPANT)

        if not event.finished:
            raise MUError(MUErrorCode.CANNOT_LIKE_BEFORE_FINISH)

        if not member.has_participated:
            raise MUError(MUErrorCode.CANNOT_LIKE_DIDNT_PARTICIPATE)
        
        try:
            other = EventMember.objects.get(
                pk = (user_id, event_id)
            )
            if other.participates and other.has_participated:

                try: 
                    eml = EventMemberLike.objects.get(
                        pk = (event_id, user.id, user_id)
                    )
                    eml.like = like
                    eml.save()
                except EventMemberLike.DoesNotExist:
                    EventMemberLike.objects.create(
                        user_1_id = user.id,
                        user_2_id = user_id,
                        event_id = event_id,
                        like = like
                    )

                return LikeEventMemberMutation(success=True)
        except EventMember.DoesNotExist:
            pass

        raise MUError(MUErrorCode.CANNOT_LIKE_NOT_PARTICIPANT)
    
class Mutation(graphene.ObjectType):
    confirm_member_participation = ConfirmMemberParticipationMutation.Field()
    finish_event = FinishEventMutation.Field()
    rate_event = RateEventMutation.Field()
    like_event_member = LikeEventMemberMutation.Field()