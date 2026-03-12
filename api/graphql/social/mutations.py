import graphene

from api.graphql.social.types import CreatePostType, PostCommentType, RelationshipType
from main.event.services import EventService
from main.social.models import Post, PostComment
from main.social.services import RelationshipService
from main.social.validators import validate_comment, validate_post
from main.user.models import User
from shared.enums import MemberRole
from shared.errors.mu_error import MUError, MUErrorCode
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
        event_id = graphene.Int(required=True)
        title = graphene.String(required=True)
        content = graphene.String(required=True)

    post = graphene.Field(CreatePostType)

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, event_id: int, title: str, content: str):
        validate_post(title, content)

        user_id: int = info.context.user.id
        EventService.get_event(event_id, user_id, MemberRole.MODERATOR)

        post = Post.objects.create(title=title, content=content, event_id=event_id)

        return CreatePostMutation(post=post)


class LikePostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        root,
        info: graphene.ResolveInfo,
        post_id: int,
    ):

        user: User = info.context.user

        try:
            post = Post.objects.get(pk=post_id)
            post.liked_by.add(user)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)

        return LikePostMutation(success=True)


class UnlikePostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        root,
        info: graphene.ResolveInfo,
        post_id: int,
    ):

        user: User = info.context.user

        try:
            post = Post.objects.get(pk=post_id)
            post.liked_by.remove(user)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)

        return UnlikePostMutation(success=True)


class CommentOnPostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(PostCommentType)

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, post_id: int, text: str):
        validate_comment(text)

        user: User = info.context.user

        try:
            Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)

        post_comment = PostComment.objects.create(
            user_id=user.id,
            text=text,
            post_id=post_id,
        )

        return CommentOnPostMutation(comment=post_comment)


class ReplyOnPostCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(PostCommentType)

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, comment_id: int, text: str):
        validate_comment(text)

        user: User = info.context.user

        post_id = None
        try:
            post_id = PostComment.objects.get(pk=comment_id).post_id
        except PostComment.DoesNotExist:
            raise MUError(MUErrorCode.POST_COMMENT_DOES_NOT_EXIST)

        post_comment = PostComment.objects.create(
            user_id=user.id, text=text, is_reply_to_id=comment_id, post_id=post_id
        )

        return ReplyOnPostCommentMutation(comment=post_comment)


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
    reply_on_post_comment = ReplyOnPostCommentMutation.Field()
