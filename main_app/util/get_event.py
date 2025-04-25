from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import Event, EventMember
from main_app.models.enums import MemberRole

def get_event_error_code(role: MemberRole) -> MUErrorCode:
    match role:
        case MemberRole.ORGANIZER: return MUErrorCode.NOT_ORGANIZER
        case MemberRole.MODERATOR: return MUErrorCode.NOT_MODERATOR
        case MemberRole.PARTICIPANT: return MUErrorCode.NOT_PARTICIPANT
    return MUErrorCode.NOT_MEMBER

def get_event(
        event_id: int,
        user_id: int = None,
        minimal_role: MemberRole = None
    ) -> Event:
    event = None

    try:
        event = Event.objects.get(pk = event_id)
    except Event.DoesNotExist:
        raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

    if minimal_role is not None:
        if user_id is None:
            raise MUError(role_error_code)

        role_error_code = get_event_error_code(minimal_role)

        try:
            em = EventMember.objects.get(pk=(user_id, event.id))
            if em.role < minimal_role:
                raise MUError(role_error_code)
        except EventMember.DoesNotExist:
            raise MUError(role_error_code)
    
    return event

def get_event_with_member(
        event_id: int,
        user_id: int,
        minimal_role: MemberRole = None
    ) -> tuple[Event,  EventMember]:
    event = None

    try:
        event = Event.objects.get(pk = event_id)
    except Event.DoesNotExist:
        raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

    try:
        em = EventMember.objects.get(pk=(user_id, event.id))
        if minimal_role is None or em.role >= minimal_role:
            return event, em
    except EventMember.DoesNotExist:
        pass
    
    raise MUError(get_event_error_code(minimal_role))
    
    return event