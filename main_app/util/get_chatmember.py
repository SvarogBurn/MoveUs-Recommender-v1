from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import ChatMember
from main_app.models.enums import MemberRole

def get_chat_member(chat_id: int, user_id: int) -> ChatMember:

    try:
        return ChatMember.objects.get(
            user_id = user_id,
            chat_id = chat_id
        )
    except ChatMember.DoesNotExist:
        raise MUError(MUErrorCode.NOT_IN_CHAT)