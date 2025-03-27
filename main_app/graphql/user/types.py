from graphene_django import DjangoObjectType

from ...models import MoveusUser, UserPrivacySetting
from ...models.enums import PrivacySetting, PrivacyScope

class UserType(DjangoObjectType):
    class Meta:
        model = MoveusUser
        fields = (
            "id",
            "email",
            "bio",
            "date_of_birth",
            "first_name",
            "last_name",
            "xp",
            "last_online",
            "verified",
            "location",
            "gender",
            "privacy_settings",
            "username"
        )

class PrivacySetting(DjangoObjectType):

    class Meta:
        model = UserPrivacySetting
        fields = (
            "setting",
            "scope"
        )
        convert_choices_to_enum = False