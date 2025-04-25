from enum import IntEnum
from graphql import GraphQLError

class MUErrorCode(IntEnum):
    AUTHENTIFICATION_ERROR = 100
    AUTHORIZATION_ERROR = 101
    INVALID_LOGIN = 102
    NOT_ORGANIZER = 110
    NOT_MODERATOR = 111
    NOT_PARTICIPANT = 112
    NOT_MEMBER = 113

    USER_DOES_NOT_EXIST = 200
    FRIEND_REQUEST_DOES_NOT_EXIST = 201
    EVENT_DOES_NOT_EXIST = 202
    PREFERRED_ACTIVITY_DOES_NOT_EXIST = 203
    LOCATION_DOES_NOT_EXIST = 204
    EVENT_MEMBER_DOES_NOT_EXIST = 205

    INVALID_FRIEND_REQUEST = 300
    MINIMAL_LOCAION_REQUIREMENTS_MISSING = 301
    EVENT_START_TIME = 302
    EVENT_END_TIME = 303
    EVENT_TIMES_RELATION = 303
    NOT_FRIENDS = 304
    EVENT_MIN_AGE = 305
    EVENT_MAX_AGE = 306
    EVENT_MIN_MAX_AGE = 307
    EVENT_ACCEPTED_GENDERS = 308

    ALREADY_IN_EVENT = 310
    EVENT_FULL = 311
    EVENT_ALREADY_STARTED = 312
    SPECTATORS_NOT_ALLOWED = 313
    CANNOT_DEMOTE_YOURSELF = 314
    EVENT_ALREADY_ENDED = 315
    CANNOT_LEAVE_AS_ORGANIZATOR = 316
    CANNOT_KICK_YOURSELF = 317
    CANNOT_KICK_ORGANIZER = 318
    AGE_RANGE = 319
    GENDER_NOT_ALLOWED = 320

    CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER = 321
    CANNOT_CONFIRM_BEFORE_END = 322
    CANNOT_CONFIRM_AFTER_FINISH = 323
    CANNOT_FINISH_BEFORE_END = 324
    CANNOT_FINISH_WITH_UNCONFIRMED = 325

    CANNOT_RATE_OWN_EVENT = 330
    CANNOT_RATE_UNFINISHED = 331
    CANNOT_RATE_NO_PARTICIPATION = 332
    RATE_COMMENT_MAX_LENGTH = 333

    CANNOT_LIKE_BEFORE_FINISH = 340
    CANNOT_LIKE_YOURSELF = 341
    CANNOT_LIKE_NOT_PARTICIPANT = 342
    CANNOT_LIKE_DIDNT_PARTICIPATE = 343

    USERNAME_ALREADY_TAKEN = 1000
    USERNAME_MIN_LENGTH = 1001
    USERNAME_MAX_LENGTH = 1002
    USERNAME_ALLOWED_CHARACTERS = 1003
    EMAIL_ALREADY_TAKEN = 1004
    EMAIL_INVALID = 1005
    PASSWORD_MIN_LENGTH = 1006
    PASSWORD_MISSING_LETTER = 1007
    PASSWORD_MISSING_NUMBER = 1008
    PASSWORD_MISSING_SPECIAL = 1009

    FIRSTNAME_MIN_LENGTH = 1010
    FIRSTNAME_MAX_LENGTH = 1011
    LASTNAME_MIN_LENGTH = 1012
    LASTNAME_MAX_LENGTH = 1013
    USER_MAX_AGE = 1014
    USER_MIN_AGE = 1015
    BIO_MAX_LENGTH = 1016
    TRAVEL_DISTANCE_RANGE = 1017
    USER_PREFERRED_GENDERS_CHOICE = 1018
    PREFERRED_EVENT_DURATION_RANGE = 1019

    ADDRESS_LINE_MAX_LENGTH = 1020
    ZIP_CODE_VALUE = 1021
    REGION_MAX_LENGTH = 1022
    LOCATION_NAME_MAX_LENGTH = 1023
    LOCATION_NAME_MIN_LENGTH = 1024
    LONGITUDE_VALUE = 1025
    LATITUDE_VALUE = 1026

    EVENT_TITLE_MIN_LENGTH = 1030
    EVENT_TITLE_MAX_LENGTH = 1031
    EVENT_DESCRIPTION_MAX_LENGTH = 1032
    EVENT_MIN_MAX_PARTICIPANTS = 1033


EC = MUErrorCode

mu_error_code_messages = {
    EC.AUTHENTIFICATION_ERROR : "You need to be logged in to run this query.",
    EC.AUTHORIZATION_ERROR : "You are not allowed to perform this query.",
    EC.INVALID_LOGIN : "User not found or password is wrong.",
    EC.NOT_ORGANIZER : "You need to be the event organizer to perform with mutation",
    EC.NOT_MODERATOR : "You need to be the event organizer or moderator to perform with mutation",
    EC.NOT_PARTICIPANT : "You need to participate in the event to perform with mutation",
    EC.NOT_MEMBER : "You need to be in the event to perform with mutation",
    EC.USER_DOES_NOT_EXIST : "User does not exits.",
    EC.FRIEND_REQUEST_DOES_NOT_EXIST : "Friendship request does not exist.",
    EC.EVENT_DOES_NOT_EXIST : "Event does not exist.",
    EC.PREFERRED_ACTIVITY_DOES_NOT_EXIST: "Activity not on user's preferred activity list.",
    EC.LOCATION_DOES_NOT_EXIST: "Location does not found.",
    EC.EVENT_MEMBER_DOES_NOT_EXIST: "Event member does not exist.",
    EC.INVALID_FRIEND_REQUEST : "Cannot send friend request to this user.",
    EC.MINIMAL_LOCAION_REQUIREMENTS_MISSING : "You either need to provide a location id or longitude and latitude.",
    EC.EVENT_START_TIME : "Event has to start in the future.",
    EC.EVENT_END_TIME : "Event has to end in the future.",
    EC.EVENT_TIMES_RELATION : "Event start time has to be before event end time.",
    EC.NOT_FRIENDS : "You need to be friends with this user to run this mutation.",
    EC.EVENT_MIN_AGE : "Minimal age for an event has to be between 18 and 100 years.",
    EC.EVENT_MAX_AGE : "Maximum age for an event has to be between 18 and 100 years.",
    EC.EVENT_MIN_MAX_AGE : "Event minimal age must be lower than even maximal age.",
    EC.EVENT_ACCEPTED_GENDERS : "Prefer not to say cannot be in event accepted genders.",
    EC.ALREADY_IN_EVENT : "Cannot join event you are already participating.",
    EC.EVENT_FULL : "This event is full.",
    EC.EVENT_ALREADY_STARTED : "Event already started.",
    EC.SPECTATORS_NOT_ALLOWED : "This event does not accept spectators.",
    EC.CANNOT_DEMOTE_YOURSELF : "You cannot demote yourself to a spectator.",
    EC.EVENT_ALREADY_ENDED : "Event already ended.",
    EC.CANNOT_LEAVE_AS_ORGANIZATOR : "You cannot leave an event you organized.",
    EC.CANNOT_KICK_YOURSELF : "You cannot kick yourself from the event.",
    EC.CANNOT_KICK_ORGANIZER : "You cannot kick event organizer from the event.",
    EC.AGE_RANGE : "You are not withing the allowed age range of the event.",
    EC.GENDER_NOT_ALLOWED : "You are not allowed to join this event beacuse of your gender.",
    EC.CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER : "Can only confirm paarticipation of participants.",
    EC.CANNOT_CONFIRM_BEFORE_END : "Cannot confirm pariticipation before the event ends.",
    EC.CANNOT_CONFIRM_AFTER_FINISH : "Cannot confirm pariticipation after the event is finished.",
    EC.CANNOT_FINISH_BEFORE_END : "Cannot finish event before its end time.",
    EC.CANNOT_FINISH_WITH_UNCONFIRMED : "Cannot finish event with unconfirmed participants.",
    EC.CANNOT_RATE_OWN_EVENT : "Cannot rate your own event.",
    EC.CANNOT_RATE_UNFINISHED : "Cannot rate an event before it officially finishes.",
    EC.CANNOT_RATE_NO_PARTICIPATION : "Cannot rate an event you didn't participate in.",
    EC.RATE_COMMENT_MAX_LENGTH : "Event comment can be at most 512 characters long." ,
    EC.CANNOT_LIKE_BEFORE_FINISH : "Cannot like a member before the event officially finishes." ,
    EC.CANNOT_LIKE_YOURSELF : "Cannot like yourself." ,
    EC.CANNOT_LIKE_NOT_PARTICIPANT : "Cannot like a member who did not participate" ,
    EC.CANNOT_LIKE_DIDNT_PARTICIPATE : "Cannot like an event member of event you didn't participate in. " ,
    EC.USERNAME_ALREADY_TAKEN : "Username already taken.",
    EC.USERNAME_MIN_LENGTH : "Username must be at least 3 characters long.",
    EC.USERNAME_MAX_LENGTH : "Username cannot be longer than 24 characters.",
    EC.USERNAME_ALLOWED_CHARACTERS : "Username can only contain alphanumeric characters and underscore.",
    EC.EMAIL_ALREADY_TAKEN : "Email already taken.",
    EC.EMAIL_INVALID : "Email not valid.",
    EC.PASSWORD_MIN_LENGTH : "Password must be at least 8 characters long.",
    EC.PASSWORD_MISSING_LETTER : "Password must contain at least one letter.",
    EC.PASSWORD_MISSING_NUMBER : "Password must contain at least one number.",
    EC.PASSWORD_MISSING_SPECIAL : "Password must contain at least one special character.",
    EC.FIRSTNAME_MIN_LENGTH : "First name has to be at least 2 characters long.",
    EC.FIRSTNAME_MAX_LENGTH : "First name cannot be longer than 32 characters.",
    EC.LASTNAME_MIN_LENGTH : "Last name has to be at least 2 characters long.",
    EC.LASTNAME_MAX_LENGTH : "Last name cannot be longer than 32 characters.",
    EC.USER_MAX_AGE : "Surely not that old.",
    EC.USER_MIN_AGE : "You must be over 18 to use MoveUs.",
    EC.BIO_MAX_LENGTH : "User bio cannot be longer than 512 characters.",
    EC.TRAVEL_DISTANCE_RANGE : "Max travel distance must be between 1 and 20,000 km.",
    EC.USER_PREFERRED_GENDERS_CHOICE : "Prefer not to say cannot be in preferred genders.",
    EC.PREFERRED_EVENT_DURATION_RANGE : "Preferred event duration must be between 1 and 200 hours.",
    EC.ADDRESS_LINE_MAX_LENGTH : "Address line can be at most 64 characters.",
    EC.ZIP_CODE_VALUE : "Zip code must be a 5 digit number.",
    EC.REGION_MAX_LENGTH : "Region cannot be longer than 32 characters.",
    EC.LOCATION_NAME_MAX_LENGTH : "Location name cannot be longer than 32 characters.",
    EC.LOCATION_NAME_MIN_LENGTH : "Location cannot be shorter than 4 characters.",
    EC.LATITUDE_VALUE : "Latitude must be between -90 and 90 degrees.",
    EC.LONGITUDE_VALUE : "Longitude must be between -180 and 180 degrees.",
    EC.EVENT_TITLE_MAX_LENGTH : "Event title cannot be longer than 32 characters.",
    EC.EVENT_TITLE_MIN_LENGTH : "Event title cannot be shorter than 4 characters.",
    EC.EVENT_DESCRIPTION_MAX_LENGTH : "Event description cannot be longer than 1024 characters.",
    EC.EVENT_MIN_MAX_PARTICIPANTS : "Max participant count cannot be smaller than one or smaller than the number of currently joined participants.",
}

class MUError(GraphQLError):

    def __init__(self, code: MUErrorCode, nodes = None, source = None, positions = None, path = None, original_error = None, extensions = None):
        message = mu_error_code_messages[code]
        super().__init__(message, nodes, source, positions, path, original_error, extensions)

        self.code = code;
        self.message = message;