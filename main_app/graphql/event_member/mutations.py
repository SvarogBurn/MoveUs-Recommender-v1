import graphene

from django.utils.timezone import now

from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import EventMember, Event, User
from main_app.models.enums import MemberRole
from main_app.graphql.event_member.types import EventMemberType
from main_app.util import require_auth, get_event

class JoinEventMutation(graphene.Mutation):
    
    class Arguments:
        event_id = graphene.Int(required=True)

    event_member = graphene.Field(EventMemberType)

    @require_auth
    def mutate(self, info, event_id: int):
        user: User = info.context.user
        event = get_event(event_id)

        if event.start_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_STARTED)

        if event.max_participants is not None and \
            event.participant_count() >= event.max_participants:

            raise MUError(MUErrorCode.EVENT_FULL)
        
        if event.accepted_genders is not None and not user.gender in event.accepted_genders:
            raise MUError(MUErrorCode.GENDER_NOT_ALLOWED)
        
        if event.min_age and not user.date_of_birth or user.age < event.min_age:
            raise MUError(MUErrorCode.AGE_RANGE)
        
        if event.max_age and not user.date_of_birth or user.age > event.max_age:
            raise MUError(MUErrorCode.AGE_RANGE)

        member: EventMember = None
        
        try:
            member = EventMember.objects.get(pk=(user.id, event_id))
            if member.role != MemberRole.SPECTATOR:
                raise MUError(MUErrorCode.ALREADY_IN_EVENT)
            member.role = MemberRole.PARTICIPANT
            member.save()
        except EventMember.DoesNotExist:
            member = EventMember.objects.create(
                user_id=user.id,
                event_id=event_id,
                role=MemberRole.PARTICIPANT
            )

        return JoinEventMutation(event_member=member)
    
class SpectateEventMutation(graphene.Mutation):
    
    class Arguments:
        event_id = graphene.Int(required=True)

    event_member = graphene.Field(EventMemberType)

    @require_auth
    def mutate(self, info, event_id: int):
        user: User = info.context.user
        event = get_event(event_id)

        if event.start_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_STARTED)

        member: EventMember = None
        
        try:
            member = EventMember.objects.get(pk=(user.id, event_id))
            if member.role != MemberRole.PARTICIPANT:
                raise MUError(MUErrorCode.CANNOT_DEMOTE_YOURSELF)
            member.role = MemberRole.SPECTATOR
            member.save()
        except EventMember.DoesNotExist:
            member = EventMember.objects.create(
                user_id=user.id,
                event_id=event_id,
                role=MemberRole.SPECTATOR
            )

        return SpectateEventMutation(event_member=member)
    
class LeaveEventMutation(graphene.Mutation):
    
    class Arguments:
        event_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info, event_id: int):
        user: User = info.context.user
        event = get_event(event_id)

        if event.end_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_ENDED)

        try:
            member = EventMember.objects.get(pk=(user.id, event_id))
            if member.role == MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.CANNOT_LEAVE_AS_ORGANIZATOR)
            member.delete()
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_MEMBER)

        return LeaveEventMutation(success=True)
    
class KickEventMemberMutation(graphene.Mutation):
    
    class Arguments:
        event_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info, event_id: int, user_id: int):
        user: User = info.context.user

        if user.id == user_id:
            raise MUError(MUErrorCode.CANNOT_KICK_YOURSELF)

        event = get_event(event_id, user.id, MemberRole.MODERATOR)

        if event.end_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_ENDED)

        try:
            member = EventMember.objects.get(pk=(user_id, event_id))
            if member.role == MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.CANNOT_KICK_ORGANIZER)
            member.delete()
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_MEMBER_DOES_NOT_EXIST)

        return LeaveEventMutation(success=True)
    
class Mutation(graphene.ObjectType):
    join_event = JoinEventMutation.Field()
    spectate_event = SpectateEventMutation.Field()
    leave_event = LeaveEventMutation.Field()
    kick_event_member = KickEventMemberMutation.Field()