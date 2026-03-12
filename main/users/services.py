from main.users.models import User, UserPrivacySetting
from shared.enums import PrivacyScope, PrivacySetting


class UserService:
    @staticmethod
    def initialize_privacy_settings(user: User) -> None:
        for key in PrivacySetting:
            UserPrivacySetting.objects.create(
                user=user, setting=key.value, scope=PrivacyScope.EVERYONE
            )
