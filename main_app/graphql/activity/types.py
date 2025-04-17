import graphene

from main_app.models.enums import ActivityEnum
from ..object_type import MUObjectType

from ...models import Activity, PreferredActivity

class ActivityType(MUObjectType):
    class Meta:
        model = Activity
        exclude = ("pk",)

    id = graphene.String()

    def resolve_id(self, info):
        return ActivityEnum(self.id).name
        
class PreferredActivityType(MUObjectType):
    class Meta:
        model = PreferredActivity
        exclude = ("pk", "user")