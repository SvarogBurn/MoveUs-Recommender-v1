import graphene

from main.event.services import EventService
from main.user.services import UserService
from shared.utils.decorators import require_auth


# TODO: Change mutations to NOT return boolean
class ReportUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int(required=True)
        comment = graphene.String()

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, user_id: int, comment: str = None):

        UserService.report_user(info.context.user.id, user_id, comment)

        return ReportUserMutation(success=True)


class ReportEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        comment = graphene.String()

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, event_id: int, comment: str = None):

        EventService.report_event(info.context.user.id, event_id, comment)

        return ReportEventMutation(success=True)


class Mutation(graphene.ObjectType):
    report_user_mutation = ReportUserMutation.Field()
    report_event_mutation = ReportEventMutation.Field()
