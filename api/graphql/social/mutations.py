import graphene
from django.conf import settings

from api.graphql.social.types import CommentType, CreatePostType, FollowType
from main.social.services import (
    BlockService,
    CommentService,
    FollowService,
    PostService,
)
from shared.utils.decorators import rate_limit, require_auth


class FollowUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    follow = graphene.Field(FollowType)

    @require_auth
    @rate_limit("follow", *settings.RATE_LIMIT_FOLLOW, by="user")
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        follow = FollowService.follow(info.context.user.id, user_id)
        return FollowUserMutation(follow=follow)


class UnfollowUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        FollowService.unfollow(info.context.user.id, user_id)
        return UnfollowUserMutation(success=True)


class BlockUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        BlockService.block_user(info.context.user.id, user_id)
        return BlockUserMutation(success=True)


class UnblockUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_id: int):
        BlockService.unblock_user(info.context.user.id, user_id)
        return UnblockUserMutation(success=True)


class CreatePostMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=False, default_value=None)
        content = graphene.String(required=True)

    post = graphene.Field(CreatePostType)

    @require_auth
    @rate_limit("create_post", *settings.RATE_LIMIT_CREATE_POST, by="user")
    def mutate(root, info: graphene.ResolveInfo, content: str, event_id: int | None = None):
        post = PostService.create_post(info.context.user.id, content, event_id)
        return CreatePostMutation(post=post)


class LikePostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, post_id: int):
        PostService.like_post(info.context.user.id, post_id)
        return LikePostMutation(success=True)


class UnlikePostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, post_id: int):
        PostService.unlike_post(info.context.user.id, post_id)
        return UnlikePostMutation(success=True)


class CommentOnPostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    @require_auth
    @rate_limit("comment", *settings.RATE_LIMIT_COMMENT, by="user")
    def mutate(root, info: graphene.ResolveInfo, post_id: int, text: str):
        comment = CommentService.comment_on_post(info.context.user.id, post_id, text)
        return CommentOnPostMutation(comment=comment)


class CommentOnEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    @require_auth
    @rate_limit("comment", *settings.RATE_LIMIT_COMMENT, by="user")
    def mutate(root, info: graphene.ResolveInfo, event_id: int, text: str):
        comment = CommentService.comment_on_event(info.context.user.id, event_id, text)
        return CommentOnEventMutation(comment=comment)


class ReplyOnCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    @require_auth
    @rate_limit("comment", *settings.RATE_LIMIT_COMMENT, by="user")
    def mutate(root, info: graphene.ResolveInfo, comment_id: int, text: str):
        comment = CommentService.reply_to_comment(
            info.context.user.id, comment_id, text
        )
        return ReplyOnCommentMutation(comment=comment)


class LikeCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, comment_id: int):
        CommentService.like_comment(info.context.user.id, comment_id)
        return LikeCommentMutation(success=True)


class UnlikeCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(root, info: graphene.ResolveInfo, comment_id: int):
        CommentService.unlike_comment(info.context.user.id, comment_id)
        return UnlikeCommentMutation(success=True)


class Mutation(graphene.ObjectType):
    follow_user = FollowUserMutation.Field()
    unfollow_user = UnfollowUserMutation.Field()
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
