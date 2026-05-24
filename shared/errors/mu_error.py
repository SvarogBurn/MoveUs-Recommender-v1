from enum import IntEnum

from graphql import GraphQLError


class MUErrorCode(IntEnum):
    # 1xx – Authentication & Authorization Errors
    AUTHENTICATION_ERROR = 100
    AUTHORIZATION_ERROR = 101
    INVALID_LOGIN = 102

    NOT_ORGANIZER = 110
    NOT_MODERATOR = 111
    NOT_PARTICIPANT = 112
    NOT_MEMBER = 113

    # 2xx – Resource Not Found / Existence Errors
    USER_DOES_NOT_EXIST = 200
    EVENT_DOES_NOT_EXIST = 202
    PREFERRED_ACTIVITY_DOES_NOT_EXIST = 203
    LOCATION_DOES_NOT_EXIST = 204
    EVENT_MEMBER_DOES_NOT_EXIST = 205
    POST_DOES_NOT_EXIST = 206
    COMMENT_DOES_NOT_EXIST = 207
    CHAT_DOES_NOT_EXIST = 208

    # 3xx – Invalid Actions / Preconditions Not Met
    MINIMAL_LOCATION_REQUIREMENTS_MISSING = 301

    EVENT_START_TIME_INVALID = 310
    EVENT_END_TIME_INVALID = 311
    EVENT_TIMES_RELATION_INVALID = 312

    AGE_RANGE_INVALID = 321
    GENDER_NOT_ALLOWED = 322
    EVENT_MIN_AGE = 323
    EVENT_MAX_AGE = 324
    EVENT_MIN_MAX_AGE = 325
    EVENT_ACCEPTED_GENDERS = 326

    ALREADY_IN_EVENT = 330
    EVENT_FULL = 331
    EVENT_ALREADY_STARTED = 332
    EVENT_ALREADY_ENDED = 333
    SPECTATORS_NOT_ALLOWED = 334

    CANNOT_DEMOTE_YOURSELF = 340
    CANNOT_LEAVE_AS_ORGANIZATOR = 341
    CANNOT_KICK_YOURSELF = 342
    CANNOT_KICK_ORGANIZER = 343

    CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER = 350
    CANNOT_CONFIRM_BEFORE_END = 351
    CANNOT_CONFIRM_AFTER_FINISH = 352
    CANNOT_FINISH_BEFORE_END = 353
    CANNOT_FINISH_WITH_UNCONFIRMED = 354

    CANNOT_RATE_OWN_EVENT = 360
    CANNOT_RATE_UNFINISHED_EVENT = 361
    CANNOT_RATE_NO_PARTICIPATION = 362
    RATE_COMMENT_MAX_LENGTH = 363

    CANNOT_LIKE_BEFORE_FINISH = 370
    CANNOT_LIKE_YOURSELF = 371
    CANNOT_LIKE_NOT_PARTICIPANT = 372
    CANNOT_LIKE_DIDNT_PARTICIPATE = 373

    NOT_FOLLOWING = 380
    CANNOT_TARGET_SELF = 381
    ALREADY_FOLLOWING = 382
    NOT_BLOCKED = 383
    BLOCKED_USER = 384

    # 4xx – Chat & Messaging Errors
    NOT_IN_CHAT = 400
    NICKNAME_MAX_LENGTH = 401
    MESSAGE_MAX_LENGTH = 402
    CANNOT_MESSAGE_YOURSELF = 403
    NO_TEXT_OR_ATTACHMENT = 404
    CANNOT_LEAVE_DIRECT_CHAT = 405
    CANNOT_ADD_TO_DIRECT_CHAT = 406

    # 5xx – Post & Comment Errors
    POST_CONTENT_MAX_LENGTH = 501
    POST_ALREADY_LIKED = 502
    POST_NOT_LIKED = 503
    COMMENT_MAX_LENGTH = 504
    COMMENT_NESTING_TOO_DEEP = 505

    # 6xx – Attachment Errors
    ATTACHMENT_NOT_OWNED = 600
    ATTACHMENT_NOT_UPLOADED = 601

    # 7xx – User Registration & Validation Errors
    USERNAME_ALREADY_TAKEN = 700
    USERNAME_MIN_LENGTH = 701
    USERNAME_MAX_LENGTH = 702
    USERNAME_ALLOWED_CHARACTERS = 703

    EMAIL_ALREADY_TAKEN = 710
    EMAIL_INVALID = 711

    PASSWORD_MIN_LENGTH = 720
    PASSWORD_MISSING_LETTER = 721
    PASSWORD_MISSING_NUMBER = 722
    PASSWORD_MISSING_SPECIAL = 723

    FIRSTNAME_MIN_LENGTH = 730
    FIRSTNAME_MAX_LENGTH = 731
    LASTNAME_MIN_LENGTH = 732
    LASTNAME_MAX_LENGTH = 733

    USER_MAX_AGE = 740
    USER_MIN_AGE = 741
    BIO_MAX_LENGTH = 742
    TRAVEL_DISTANCE_RANGE = 743
    USER_PREFERRED_GENDERS_CHOICE = 744
    PREFERRED_EVENT_DURATION_RANGE = 745

    # 8xx – Address & Location Validation
    ADDRESS_LINE_MAX_LENGTH = 800
    ZIP_CODE_VALUE = 801
    REGION_MAX_LENGTH = 802
    LOCATION_NAME_MAX_LENGTH = 803
    LOCATION_NAME_MIN_LENGTH = 804
    LONGITUDE_VALUE = 805
    LATITUDE_VALUE = 806

    # 9xx – Event Input Validation Errors
    EVENT_TITLE_MIN_LENGTH = 900
    EVENT_TITLE_MAX_LENGTH = 901
    EVENT_DESCRIPTION_MAX_LENGTH = 902
    EVENT_MIN_MAX_PARTICIPANTS = 903

    # 10xx – Miscellaneous
    REPORT_COMMENT_MAX_LENGTH = 1000
    INVALID_PAGINATION = 1001
    RATE_LIMITED = 1002


EC = MUErrorCode

mu_error_code_messages = {
    EC.AUTHENTICATION_ERROR: "You need to be logged in to run this query.",
    EC.AUTHORIZATION_ERROR: "You are not allowed to perform this query.",
    EC.INVALID_LOGIN: "User not found or password is wrong.",
    EC.NOT_ORGANIZER: "You need to be the event organizer to perform this mutation",
    EC.NOT_MODERATOR: "You need to be the event organizer or moderator to perform this mutation",
    EC.NOT_PARTICIPANT: "You need to participate in the event to perform this mutation",
    EC.NOT_MEMBER: "You need to be in the event to perform this mutation",
    EC.USER_DOES_NOT_EXIST: "User does not exits.",
    EC.EVENT_DOES_NOT_EXIST: "Event does not exist.",
    EC.PREFERRED_ACTIVITY_DOES_NOT_EXIST: "Activity not on user's preferred activity list.",
    EC.LOCATION_DOES_NOT_EXIST: "Location does not found.",
    EC.EVENT_MEMBER_DOES_NOT_EXIST: "Event member does not exist.",
    EC.POST_DOES_NOT_EXIST: "Post does not exist.",
    EC.COMMENT_DOES_NOT_EXIST: "Comment does not exist.",
    EC.MINIMAL_LOCATION_REQUIREMENTS_MISSING: "You need to provide a longitude and latitude.",
    EC.EVENT_START_TIME_INVALID: "Event has to start in the future.",
    EC.EVENT_END_TIME_INVALID: "Event has to end in the future.",
    EC.EVENT_TIMES_RELATION_INVALID: "Event start time has to be before event end time.",
    EC.NOT_FOLLOWING: "You are not following this user.",
    EC.EVENT_MIN_AGE: "Minimal age for an event has to be between 18 and 100 years.",
    EC.EVENT_MAX_AGE: "Maximum age for an event has to be between 18 and 100 years.",
    EC.EVENT_MIN_MAX_AGE: "Event minimal age must be lower than even maximal age.",
    EC.EVENT_ACCEPTED_GENDERS: "Prefer not to say cannot be in event accepted genders.",
    EC.ALREADY_IN_EVENT: "Cannot join event you are already participating.",
    EC.EVENT_FULL: "This event is full.",
    EC.EVENT_ALREADY_STARTED: "Event already started.",
    EC.SPECTATORS_NOT_ALLOWED: "This event does not accept spectators.",
    EC.CANNOT_DEMOTE_YOURSELF: "You cannot demote yourself to a spectator.",
    EC.EVENT_ALREADY_ENDED: "Event already ended.",
    EC.CANNOT_LEAVE_AS_ORGANIZATOR: "You cannot leave an event you organized.",
    EC.CANNOT_KICK_YOURSELF: "You cannot kick yourself from the event.",
    EC.CANNOT_KICK_ORGANIZER: "You cannot kick event organizer from the event.",
    EC.AGE_RANGE_INVALID: "You are not withing the allowed age range of the event.",
    EC.GENDER_NOT_ALLOWED: "You are not allowed to join this event beacuse of your gender.",
    EC.CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER: "Can only confirm paarticipation of participants.",
    EC.CANNOT_CONFIRM_BEFORE_END: "Cannot confirm pariticipation before the event ends.",
    EC.CANNOT_CONFIRM_AFTER_FINISH: "Cannot confirm pariticipation after the event is finished.",
    EC.CANNOT_FINISH_BEFORE_END: "Cannot finish event before its end time.",
    EC.CANNOT_FINISH_WITH_UNCONFIRMED: "Cannot finish event with unconfirmed participants.",
    EC.CANNOT_RATE_OWN_EVENT: "Cannot rate your own event.",
    EC.CANNOT_RATE_UNFINISHED_EVENT: "Cannot rate an event before it officially finishes.",
    EC.CANNOT_RATE_NO_PARTICIPATION: "Cannot rate an event you didn't participate in.",
    EC.RATE_COMMENT_MAX_LENGTH: "Event comment can be at most 512 characters long.",
    EC.CANNOT_LIKE_BEFORE_FINISH: "Cannot like a member before the event officially finishes.",
    EC.CANNOT_LIKE_YOURSELF: "Cannot like yourself.",
    EC.CANNOT_LIKE_NOT_PARTICIPANT: "Cannot like a member who did not participate",
    EC.CANNOT_LIKE_DIDNT_PARTICIPATE: "Cannot like an event member of event you didn't participate in. ",
    EC.CHAT_DOES_NOT_EXIST: "That chat does not exist.",
    EC.NOT_IN_CHAT: "You are not a member of this chat.",
    EC.NICKNAME_MAX_LENGTH: "Nickname cannot be longer than 24 characters.",
    EC.MESSAGE_MAX_LENGTH: "Messages cannot be longer than 512 characters.",
    EC.POST_CONTENT_MAX_LENGTH: "Post content cannot be longer than 2048 characters.",
    EC.POST_ALREADY_LIKED: "You cannot like the same post twice.",
    EC.POST_NOT_LIKED: "You cannot unlike post you didn't like.",
    EC.COMMENT_MAX_LENGTH: "Comment cannot be longer than 512 characters.",
    EC.COMMENT_NESTING_TOO_DEEP: "Replies can only be one level deep.",
    EC.ATTACHMENT_NOT_OWNED: "You can only send messages with attachments you have created.",
    EC.ATTACHMENT_NOT_UPLOADED: "You need to upload a file to the attachment link before you can use it.",
    EC.USERNAME_ALREADY_TAKEN: "Username already taken.",
    EC.USERNAME_MIN_LENGTH: "Username must be at least 3 characters long.",
    EC.USERNAME_MAX_LENGTH: "Username cannot be longer than 24 characters.",
    EC.USERNAME_ALLOWED_CHARACTERS: "Username can only contain alphanumeric characters and underscore.",
    EC.EMAIL_ALREADY_TAKEN: "Email already taken.",
    EC.EMAIL_INVALID: "Email not valid.",
    EC.PASSWORD_MIN_LENGTH: "Password must be at least 8 characters long.",
    EC.PASSWORD_MISSING_LETTER: "Password must contain at least one letter.",
    EC.PASSWORD_MISSING_NUMBER: "Password must contain at least one number.",
    EC.PASSWORD_MISSING_SPECIAL: "Password must contain at least one special character.",
    EC.FIRSTNAME_MIN_LENGTH: "First name has to be at least 2 characters long.",
    EC.FIRSTNAME_MAX_LENGTH: "First name cannot be longer than 32 characters.",
    EC.LASTNAME_MIN_LENGTH: "Last name has to be at least 2 characters long.",
    EC.LASTNAME_MAX_LENGTH: "Last name cannot be longer than 32 characters.",
    EC.USER_MAX_AGE: "Surely not that old.",
    EC.USER_MIN_AGE: "You must be over 18 to use MoveUs.",
    EC.BIO_MAX_LENGTH: "User bio cannot be longer than 512 characters.",
    EC.TRAVEL_DISTANCE_RANGE: "Max travel distance must be between 1 and 20,000 km.",
    EC.USER_PREFERRED_GENDERS_CHOICE: "Prefer not to say cannot be in preferred genders.",
    EC.PREFERRED_EVENT_DURATION_RANGE: "Preferred event duration must be between 1 and 200 hours.",
    EC.ADDRESS_LINE_MAX_LENGTH: "Address line can be at most 64 characters.",
    EC.ZIP_CODE_VALUE: "Zip code must be a 5 digit number.",
    EC.REGION_MAX_LENGTH: "Region cannot be longer than 32 characters.",
    EC.LOCATION_NAME_MAX_LENGTH: "Location name cannot be longer than 32 characters.",
    EC.LOCATION_NAME_MIN_LENGTH: "Location cannot be shorter than 4 characters.",
    EC.LATITUDE_VALUE: "Latitude must be between -90 and 90 degrees.",
    EC.LONGITUDE_VALUE: "Longitude must be between -180 and 180 degrees.",
    EC.EVENT_TITLE_MAX_LENGTH: "Event title cannot be longer than 256 characters.",
    EC.EVENT_TITLE_MIN_LENGTH: "Event title cannot be shorter than 4 characters.",
    EC.EVENT_DESCRIPTION_MAX_LENGTH: "Event description cannot be longer than 131072 characters.",
    EC.EVENT_MIN_MAX_PARTICIPANTS: "Max participant count cannot be smaller than one or smaller than the number of currently joined participants.",
    EC.REPORT_COMMENT_MAX_LENGTH: "Report comment cannot be longer than 512 characters.",
    EC.INVALID_PAGINATION: "Invalid pagination range.",
    EC.RATE_LIMITED: "Too many requests. Please try again later.",
    EC.CANNOT_TARGET_SELF: "Cannot run this query on yourself.",
    EC.ALREADY_FOLLOWING: "You are already following this user.",
    EC.NOT_BLOCKED: "You have not blocked this user.",
    EC.BLOCKED_USER: "Cannot interact with a blocked user.",
    EC.CANNOT_MESSAGE_YOURSELF: "Cannot message yourself.",
    EC.NO_TEXT_OR_ATTACHMENT: "Chat message must include either text or an attachment.",
    EC.CANNOT_LEAVE_DIRECT_CHAT: "You cannot leave a direct chat.",
    EC.CANNOT_ADD_TO_DIRECT_CHAT: "You cannot add members to a direct chat.",
}


class MUError(GraphQLError):

    def __init__(
        self,
        code: MUErrorCode,
        nodes=None,
        source=None,
        positions=None,
        path=None,
        original_error=None,
        extensions=None,
    ):
        message = mu_error_code_messages[code]
        super().__init__(
            message, nodes, source, positions, path, original_error, extensions
        )

        self.code = code
        self.message = message
