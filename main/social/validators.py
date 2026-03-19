from shared.errors.mu_error import MUError, MUErrorCode


def validate_comment_length(comment: str = None, error_code: MUErrorCode = None):
    if comment and len(comment) > 512:
        raise MUError(error_code)


def validate_post(content: str):
    if len(content) > 2048:
        raise MUError(MUErrorCode.POST_CONTENT_MAX_LENGTH)


def validate_comment(text: str):
    if len(text) > 512:
        raise MUError(MUErrorCode.COMMENT_MAX_LENGTH)
