from enum import IntEnum
from graphql import GraphQLError

class MUErrorCode(IntEnum):
    AUTHENTIFICATION_ERROR = 100
    AUTHORIZATION_ERROR = 101
    NOT_ORGANIZER = 102
    INVALID_LOGIN = 103

    USER_DOES_NOT_EXIST = 200
    FRIEND_REQUEST_DOES_NOT_EXIST = 201
    EVENT_DOES_NOT_EXIST = 202
    PREFERRED_ACTIVITY_DOES_NOT_EXIST = 203
    LOCATION_DOES_NOT_EXIST = 204

    INVALID_FRIEND_REQUEST = 300
    MINIMAL_LOCAION_REQUIREMENTS_MISSING = 301
    EVENT_START_TIME = 302
    EVENT_END_TIME = 303
    EVENT_TIMES_RELATION = 303

    USERNAME_ALREADY_TAKEN = 1000
    USERNAME_MIN_LENGTH = 1001
    USERNAME_MAX_LENGTH = 1002
    USERNAME_ALLOWED_CHARACTERS = 1003

    FIRSTNAME_MIN_LENGTH = 1010
    FIRSTNAME_MAX_LENGTH = 1011
    LASTNAME_MIN_LENGTH = 1012
    LASTNAME_MAX_LENGTH = 1013
    USER_MAX_AGE = 1014
    USER_MIN_AGE = 1015
    BIO_MAX_LENGTH = 1016

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


EC = MUErrorCode

mu_error_code_messages = {
    EC.AUTHENTIFICATION_ERROR : "You need to be logged in to run this query.",
    EC.AUTHORIZATION_ERROR : "You are not allowed to perform this query.",
    EC.NOT_ORGANIZER : "You need to be the event organizer to perform with mutation",
    EC.INVALID_LOGIN : "User not found or password is wrong.",
    EC.USER_DOES_NOT_EXIST : "User does not exits.",
    EC.FRIEND_REQUEST_DOES_NOT_EXIST : "Friendship request does not exist.",
    EC.EVENT_DOES_NOT_EXIST : "Event does not exist.",
    EC.PREFERRED_ACTIVITY_DOES_NOT_EXIST: "Activity not on user's preferred activity list.",
    EC.LOCATION_DOES_NOT_EXIST: "Location does not found.",
    EC.INVALID_FRIEND_REQUEST : "Cannot send friend request to this user.",
    EC.MINIMAL_LOCAION_REQUIREMENTS_MISSING : "You either need to provide a location id or longitude and latitude.",
    EC.EVENT_START_TIME : "Event has to start in the future.",
    EC.EVENT_END_TIME : "Event has to end in the future.",
    EC.EVENT_TIMES_RELATION : "Event start time has to be before event end time.",
    EC.USERNAME_ALREADY_TAKEN : "Username already taken.",
    EC.USERNAME_MIN_LENGTH : "Username must be at least 3 characters long.",
    EC.USERNAME_MAX_LENGTH : "Username cannot be longer than 24 characters.",
    EC.USERNAME_ALLOWED_CHARACTERS : "Username can only contain alphanumeric characters and underscore.",
    EC.FIRSTNAME_MIN_LENGTH : "First name has to be at least 2 characters long.",
    EC.FIRSTNAME_MAX_LENGTH : "First name cannot be longer than 32 characters.",
    EC.LASTNAME_MIN_LENGTH : "Last name has to be at least 2 characters long.",
    EC.LASTNAME_MAX_LENGTH : "Last name cannot be longer than 32 characters.",
    EC.USER_MAX_AGE : "Surely not that old.",
    EC.USER_MIN_AGE : "You must be over 18 to use MoveUs.",
    EC.BIO_MAX_LENGTH : "User bio cannot be longer than 512 characters.",
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
}

class MUError(GraphQLError):

    def __init__(self, code: MUErrorCode, nodes = None, source = None, positions = None, path = None, original_error = None, extensions = None):
        message = mu_error_code_messages[code]
        super().__init__(message, nodes, source, positions, path, original_error, extensions)

        self.code = code;
        self.message = message;