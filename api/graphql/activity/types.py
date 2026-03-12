import graphene
from graphene_django import DjangoObjectType

from api.graphql.object_type import MUObjectType
from main.activities.models import Activity
from main.users.models import PreferredActivity
from shared.enums import ActivityType as ActivityEnum


class ActivityModelType(DjangoObjectType):

    class Meta:
        model = Activity
        fields = tuple()

    id = graphene.Int()
    name = graphene.String()

    def resolve_id(self: Activity, info: graphene.ResolveInfo) -> int:
        return self.id

    def resolve_name(self: Activity, info: graphene.ResolveInfo) -> str:
        return ActivityEnum(self.id).name


class PreferredActivityType(MUObjectType):
    class Meta:
        model = PreferredActivity
        fields = ("activity", "skill_level")
