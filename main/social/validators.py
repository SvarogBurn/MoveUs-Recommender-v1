from shared.errors.mu_error import MUError, MUErrorCode


def validate_comment_length(comment: str = None, error_code: MUErrorCode = None):
    if comment and len(comment) > 512:
        raise MUError(error_code)


def validate_post(content: str):
    if len(content) > 2048:
        raise MUError(MUErrorCode.POST_CONTENT_MAX_LENGTH)


def validate_not_self(
    user_id: int,
    target_user_id: int,
    error_code: MUErrorCode = MUErrorCode.CANNOT_TARGET_SELF,
):
    if target_user_id == user_id:
        raise MUError(error_code)


def validate_comment_nesting(parent_comment):
    if parent_comment.parent is not None:
        raise MUError(MUErrorCode.COMMENT_NESTING_TOO_DEEP)
