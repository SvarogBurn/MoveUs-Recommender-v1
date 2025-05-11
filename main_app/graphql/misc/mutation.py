import graphene

from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import Event, EventReport, User, UserReport
from main_app.util import require_auth


class ReportUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int(required=True)
        comment = graphene.String()

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info, user_id: int, comment: str = None):

        if comment and len(comment) > 512: 
            raise MUError(MUErrorCode.REPORT_COMMENT_MAX_LENGTH)
        
        if user_id == info.context.user.id:
            raise MUError(MUErrorCode.CANNOT_HAVE_RELATION_WITH_SELF)
        
        try:
            User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)
        
        UserReport.objects.create(
            reporter_id = info.context.user.id,
            reported_id = user_id,
            comment = comment
        )

        return ReportUserMutation(success=True)

class ReportEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        comment = graphene.String()

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info, event_id: int, comment: str = None):

        if comment and len(comment) > 512: 
            raise MUError(MUErrorCode.REPORT_COMMENT_MAX_LENGTH)
        
        try:
            Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)
        
        EventReport.objects.create(
            reporter_id = info.context.user.id,
            reported_id = event_id,
            comment = comment
        )

        return ReportEventMutation(success=True)

class Mutation(graphene.ObjectType):
    ReportUserMutation.Field()
    ReportEventMutation.Field()