import graphene

from api.graphql.user.types import PrivacySettingType, ProfileType
from main.user.models import User
from main.user.services import UserService
from shared.enums import (
    AcquaintancePreference,
    ActivityKind,
    DayOfWeek,
    Gender,
    OrganizingOpenness,
    ParticipationGroupKind,
    PrivacyScope,
    PrivacySetting,
    SkillLevel,
    TimeOfTheDay,
)
from shared.utils.decorators import require_auth


class AvailabilityInput(graphene.InputObjectType):
    day_of_week = DayOfWeek.as_graphene_enum()(required=True)
    time_of_day = TimeOfTheDay.as_graphene_enum()(required=True)


class PreferredActivityInput(graphene.InputObjectType):
    activity = ActivityKind.as_graphene_enum()(required=True)
    skill_level = SkillLevel.as_graphene_enum()(required=True)


class AlterBasicInfoMutation(graphene.Mutation):

    class Arguments:
        date_of_birth = graphene.Date(required=False)
        first_name = graphene.String(required=False)
        last_name = graphene.String(required=False)
        bio = graphene.String(required=False)
        gender = Gender.as_graphene_enum()(required=False)

    my_profile = graphene.Field(ProfileType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        date_of_birth=None,
        first_name: str | None = None,
        last_name: str | None = None,
        bio: str | None = None,
        gender=None,
    ):

        user: User = info.context.user

        fields = {}
        if first_name is not None:
            fields["first_name"] = first_name
        if last_name is not None:
            fields["last_name"] = last_name
        if date_of_birth:
            fields["date_of_birth"] = date_of_birth
        if bio is not None:
            fields["bio"] = bio
        if gender is not None:
            fields["gender"] = gender

        UserService.alter_basic_info(user, **fields)

        return AlterBasicInfoMutation(my_profile=user)


class AlterPreferencesMutation(graphene.Mutation):

    class Arguments:
        # scalar / enum answers
        preferred_session_duration = graphene.Int(required=False)
        organizing_openness = OrganizingOpenness.as_graphene_enum()(required=False)
        leadership_inclination = graphene.Int(required=False)
        max_travel_distance = graphene.Int(required=False)
        weekly_activity_target = graphene.Int(required=False)
        preferred_difficulty = SkillLevel.as_graphene_enum()(required=False)
        pushes_through_discomfort = graphene.Int(required=False)
        preferred_group_size = graphene.Int(required=False)
        acquaintance_preference = AcquaintancePreference.as_graphene_enum()(
            required=False
        )
        mixed_gender_comfort = graphene.Int(required=False)
        enjoys_meeting_new_people = graphene.Int(required=False)
        activity_vs_social = graphene.Int(required=False)
        motivated_by_competition = graphene.Int(required=False)
        planning_horizon = graphene.Int(required=False)
        feels_like_burden = graphene.Int(required=False)
        # multi-valued answers (full replace when provided)
        preferred_activities = graphene.List(PreferredActivityInput, required=False)
        availabilities = graphene.List(AvailabilityInput, required=False)
        participation_groups = graphene.List(
            ParticipationGroupKind.as_graphene_enum(), required=False
        )

    my_profile = graphene.Field(ProfileType)

    SCALAR_ARGS = (
        "preferred_session_duration",
        "organizing_openness",
        "leadership_inclination",
        "max_travel_distance",
        "weekly_activity_target",
        "preferred_difficulty",
        "pushes_through_discomfort",
        "preferred_group_size",
        "acquaintance_preference",
        "mixed_gender_comfort",
        "enjoys_meeting_new_people",
        "activity_vs_social",
        "motivated_by_competition",
        "planning_horizon",
        "feels_like_burden",
    )

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        preferred_activities: list | None = None,
        availabilities: list | None = None,
        participation_groups: list | None = None,
        **kwargs,
    ):

        user: User = info.context.user

        fields = {
            name: kwargs[name]
            for name in AlterPreferencesMutation.SCALAR_ARGS
            if kwargs.get(name) is not None
        }

        UserService.alter_preferences(
            user,
            preferred_activities=preferred_activities,
            availabilities=availabilities,
            participation_groups=participation_groups,
            **fields,
        )

        return AlterPreferencesMutation(my_profile=user)


class AlterMaxTravelDistanceMutation(graphene.Mutation):

    class Arguments:
        distance = graphene.Int(required=False)

    my_profile = graphene.Field(ProfileType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, distance: int = None):
        user: User = info.context.user
        UserService.alter_max_travel_distance(user, distance)
        return AlterMaxTravelDistanceMutation(my_profile=user)


class AlterAllPrivacySettingsMutation(graphene.Mutation):

    class Arguments:
        scope = PrivacyScope.as_graphene_enum()(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, scope: PrivacyScope):

        UserService.alter_all_privacy_settings(info.context.user.id, scope)

        return AlterAllPrivacySettingsMutation(success=True)


class AlterPrivacySettingMutation(graphene.Mutation):

    class Arguments:
        setting = PrivacySetting.as_graphene_enum()(required=True)
        scope = PrivacyScope.as_graphene_enum()(required=True)

    privacy_setting = graphene.Field(PrivacySettingType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        setting: PrivacySetting,
        scope: PrivacyScope,
    ):
        ups = UserService.alter_privacy_setting(
            info.context.user.id, setting, scope
        )
        return AlterPrivacySettingMutation(privacy_setting=ups)


class Mutation(graphene.ObjectType):
    alter_survey_info = AlterPreferencesMutation.Field()
    alter_basic_info = AlterBasicInfoMutation.Field()
    alter_max_travel_distance = AlterMaxTravelDistanceMutation.Field()
    alter_all_privacy_settings = AlterAllPrivacySettingsMutation.Field()
    alter_privacy_setting = AlterPrivacySettingMutation.Field()
