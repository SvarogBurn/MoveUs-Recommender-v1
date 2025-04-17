import graphene

from main_app.models.enums import RelationshipStatus as RS

from ..object_type import MUObjectType

from ...models import Relationship

class RelationshipType(MUObjectType):

    other = graphene.Field(
        graphene.lazy_import("main_app.graphql.user.types.UserType")
    )
    status = graphene.String()

    class Meta:
        model = Relationship
        exclude = ('pk', 'user_1', 'user_2')
        convert_choices_to_enum = False

    def resolve_status(self: Relationship, info):
        status = RS(self.status).name
        if self.status == RS.PENDING:
            status = RS(RS.REQUEST_SENT).name if self.user_1 == info.context.user else RS(RS.REQUEST_RECEIVED).name
        return status
    
    def resolve_other(self: Relationship, info):
        other = self.user_1 if self.user_2 == info.context.user else self.user_2
        return other
    
    