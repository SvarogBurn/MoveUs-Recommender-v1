from ..object_type import MUObjectType

from ...models import Activity, PreferredActivity

class ActivityType(MUObjectType):
    class Meta:
        model = Activity
        convert_choices_to_enum = False
        
class PreferredActivityType(MUObjectType):
    class Meta:
        model = PreferredActivity
        exclude = ("pk", "user")