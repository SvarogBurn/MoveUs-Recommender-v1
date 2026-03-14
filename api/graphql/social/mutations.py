import graphene

from api.graphql.social.types import CommentType, CreatePostType, RelationshipType
from main.social.services import CommentService, PostService, RelationshipService
from shared.utils.decorators import require_auth


class SendFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        relationship = RelationshipService.send_friend_request(
            info.context.user, user_id
        )
        return SendFriendRequestMutation(relationship=relationship)


class AcceptFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        relationship = RelationshipService.accept_friend_request(
            info.context.user, user_id
        )
        return AcceptFriendRequestMutation(relationship=relationship)


class CancelFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        relationship = RelationshipService.cancel_friend_request(
            info.context.user, user_id
        )
        return CancelFriendRequestMutation(relationship=relationship)


class RejectFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        relationship = RelationshipService.reject_friend_request(
            info.context.user, user_id
        )
        return RejectFriendRequestMutation(relationship=relationship)


class RemoveFriendMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        relationship = RelationshipService.remove_friend(info.context.user, user_id)
        return RemoveFriendMutation(relationship=relationship)


class BlockUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        relationship = RelationshipService.block_user(info.context.user, user_id)
        return BlockUserMutation(relationship=relationship)


class UnblockUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        relationship = RelationshipService.unblock_user(info.context.user, user_id)
        return UnblockUserMutation(relationship=relationship)


class CreatePostMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=False, default_value=None)
        content = graphene.String(required=True)

    post = graphene.Field(CreatePostType)

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, content: str, event_id: int | None = None):
        post = PostService.create_post(info.context.user, content, event_id)
        return CreatePostMutation(post=post)


class LikePostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, post_id: int):
        PostService.like_post(info.context.user, post_id)
        return LikePostMutation(success=True)


class UnlikePostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, post_id: int):
        PostService.unlike_post(info.context.user, post_id)
        return UnlikePostMutation(success=True)


class CommentOnPostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, post_id: int, text: str):
        comment = CommentService.comment_on_post(info.context.user, post_id, text)
        return CommentOnPostMutation(comment=comment)


class CommentOnEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, event_id: int, text: str):
        comment = CommentService.comment_on_event(info.context.user, event_id, text)
        return CommentOnEventMutation(comment=comment)


class ReplyOnCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, comment_id: int, text: str):
        comment = CommentService.reply_to_comment(
            info.context.user, comment_id, text
        )
        return ReplyOnCommentMutation(comment=comment)


class LikeCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, comment_id: int):
        CommentService.like_comment(info.context.user, comment_id)
        return LikeCommentMutation(success=True)


class UnlikeCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, comment_id: int):
        CommentService.unlike_comment(info.context.user, comment_id)
        return UnlikeCommentMutation(success=True)


class Mutation(graphene.ObjectType):
    send_friend_request = SendFriendRequestMutation.Field()
    accept_friend_request = AcceptFriendRequestMutation.Field()
    cancel_friend_request = CancelFriendRequestMutation.Field()
    reject_friend_request = RejectFriendRequestMutation.Field()
    remove_friend = RemoveFriendMutation.Field()
    block_user = BlockUserMutation.Field()
    unblock_user = UnblockUserMutation.Field()
    create_post = CreatePostMutation.Field()
    like_post = LikePostMutation.Field()
    unlike_post = UnlikePostMutation.Field()
    comment_on_post = CommentOnPostMutation.Field()
    comment_on_event = CommentOnEventMutation.Field()
    reply_on_comment = ReplyOnCommentMutation.Field()
    like_comment = LikeCommentMutation.Field()
    unlike_comment = UnlikeCommentMutation.Field()
