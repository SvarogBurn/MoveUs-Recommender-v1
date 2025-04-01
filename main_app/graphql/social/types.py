import graphene
from graphene_django import DjangoObjectType

from ...models import Relationship

from ..user.types import UserType

class RelationshipType(DjangoObjectType):

    other = graphene.Field(UserType)

    class Meta:
        model = Relationship
        exclude = ('user_1', 'user_2')
        convert_choices_to_enum = False

    def resolve_other(self: Relationship, info):
        other = self.user_1 if self.user_2 == info.context.user else self.user_2
        return other