from graphene_django import DjangoObjectType

from ...models import Activity

class ActivityType(DjangoObjectType):
    class Meta:
        model = Activity
        convert_choices_to_enum = False
        
