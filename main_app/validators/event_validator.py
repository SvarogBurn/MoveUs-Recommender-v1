from main_app.models.enums import CountryCode
from ..graphql.error import MUError, MUErrorCode
from datetime import datetime
from django.utils.timezone import now as tz_now

def event_validator(
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ):
    
    if len(title) < 4:
        raise MUError(MUErrorCode.EVENT_TITLE_MIN_LENGTH)
    
    if len(title) > 32:
        raise MUError(MUErrorCode.EVENT_TITLE_MAX_LENGTH)
    
    if len(description) > 1024:
        raise MUError(MUErrorCode.EVENT_DESCRIPTION_MAX_LENGTH)
    
    now = tz_now()

    if start_time < now:
        raise MUError(MUErrorCode.EVENT_START_TIME)
    
    if end_time < now:
        raise MUError(MUErrorCode.EVENT_END_TIME)
    
    if end_time < start_time:
        raise MUError(MUErrorCode.EVENT_TIMES_RELATION)