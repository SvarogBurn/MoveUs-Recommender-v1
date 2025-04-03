from enum import IntEnum
from graphql import GraphQLError

class MUErrorCode(IntEnum):
    AUTHENTIFICATION_ERROR = 100
    AUTHORIZATION_ERROR = 101

    USER_DOES_NOT_EXIST = 200
    FRIEND_REQUEST_DOES_NOT_EXIST = 201

    INVALID_FRIEND_REQUEST = 300

    USERNAME_ALREADY_TAKEN = 1000
    USERNAME_MIN_LENGTH = 1001
    USERNAME_MAX_LENGTH = 1002
    USERNAME_ALLOWED_CHARACTERS = 1003

    FIRSTNAME_MIN_LENGTH = 1010
    FIRSTNAME_MAX_LENGTH = 1011

    LASTNAME_MIN_LENGTH = 1020
    LASTNAME_MAX_LENGTH = 1021

    USER_MAX_AGE = 1030
    USER_MIN_AGE = 1031

    BIO_MAX_LENGTH = 1040

EC = MUErrorCode

mu_error_code_messages = {
    EC.AUTHENTIFICATION_ERROR : "You need to be logged in to run this query.",
    EC.AUTHORIZATION_ERROR : "You are not allowed to perform this query.",
    EC.USER_DOES_NOT_EXIST : "User does not exits.",
    EC.FRIEND_REQUEST_DOES_NOT_EXIST : "Friendship request does not exist.",
    EC.INVALID_FRIEND_REQUEST : "Cannot send friend request to this user.",
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
    EC.BIO_MAX_LENGTH : "User bio cannot be longer than 512 characters."
}

class MUError(GraphQLError):

    def __init__(self, code: MUErrorCode, nodes = None, source = None, positions = None, path = None, original_error = None, extensions = None):
        message = mu_error_code_messages[code]
        super().__init__(message, nodes, source, positions, path, original_error, extensions)

        self.code = code;
        self.message = message;