import graphene

from api.graphql.object_type import MUObjectType
from main.activity.models import Activity
from main.user.models import UserPreferredActivity
from shared.enums import ActivityKind


class ActivityModelType(MUObjectType):

    class Meta:
        model = Activity
        fields = tuple()

    id = graphene.Int()
    name = graphene.String()

    def resolve_id(self: Activity, info: graphene.ResolveInfo) -> int:
        return self.id

    def resolve_name(self: Activity, info: graphene.ResolveInfo) -> str:
        return ActivityKind(self.id).name


class PreferredActivityType(MUObjectType):
    class Meta:
        model = UserPreferredActivity
        fields = ("activity", "skill_level")
