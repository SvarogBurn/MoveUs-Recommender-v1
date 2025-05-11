import graphene
from graphene_django import DjangoObjectType

from main_app.models.enums import ActivityEnum

from ...models import Activity, PreferredActivity
from ..object_type import MUObjectType


class ActivityType(DjangoObjectType):
    class Meta:
        model = Activity
        fields = tuple()

    id = graphene.String()

    def resolve_id(self, info):
        return ActivityEnum(self.id).name
        
class PreferredActivityType(MUObjectType):
    class Meta:
        model = PreferredActivity
        fields = ("activity", "skill_level")