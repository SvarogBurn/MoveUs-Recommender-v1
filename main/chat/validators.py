from shared.errors.mu_error import MUError, MUErrorCode


def validate_nickname(nickname: str):
    if len(nickname) > 24:
        raise MUError(MUErrorCode.NICKNAME_MAX_LENGTH)


def validate_message(text_content: str = None, attachment_id: str = None):
    if text_content is None and attachment_id is None:
        raise MUError(MUErrorCode.NO_TEXT_OR_ATTACHMENT)

    if text_content and len(text_content) > 512:
        raise MUError(MUErrorCode.MESSAGE_MAX_LENGTH)
