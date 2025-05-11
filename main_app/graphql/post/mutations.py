import graphene

from main_app.graphql.error import MUError, MUErrorCode
from main_app.graphql.post.types import CreatePostType, PostCommentType
from main_app.models import Post, PostComment, User
from main_app.models.enums import MemberRole
from main_app.util import get_event, require_auth


class CreatePostMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        title = graphene.String(required=True)
        content = graphene.String(required=True)

    post = graphene.Field(CreatePostType)

    @require_auth
    def mutate(
        root,
        info,
        event_id: int,
        title: str,
        content: str
    ):
        if len(title) > 128:
            raise MUError(MUErrorCode.POST_TITLE_MAX_LENGTH)
        
        if len(content) > 2048:
            raise MUError(MUErrorCode.POST_CONTENT_MAX_LENGTH)

        user_id: int = info.context.user.id
        get_event(event_id, user_id, MemberRole.MODERATOR)

        post = Post.objects.create(
            title = title,
            content = content,
            event_id = event_id
        )

        return CreatePostMutation(post=post)

class LikePostMutation(graphene.Mutation):

    class Arguments:
        post_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        root,
        info,
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
        info,
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
    def mutate(
        root,
        info,
        post_id: int,
        text: str
    ):
        if len(text) > 512:
            raise MUError(MUErrorCode.POST_COMMENT_MAX_LENGTH)

        user: User = info.context.user

        try:
            Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)
        
        post_comment = PostComment.objects.create(
            user_id = user.id,
            text = text,
            post_id = post_id,
        )

        return CommentOnPostMutation(comment=post_comment)
    
class ReplyOnPostCommentMutation(graphene.Mutation):

    class Arguments:
        comment_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(PostCommentType)

    @require_auth
    def mutate(
        root,
        info,
        comment_id: int,
        text: str
    ):
        if len(text) > 512:
            raise MUError(MUErrorCode.POST_COMMENT_MAX_LENGTH)

        user: User = info.context.user

        post_id = None
        try:
            post_id = PostComment.objects.get(pk=comment_id).post_id
        except PostComment.DoesNotExist:
            raise MUError(MUErrorCode.POST_COMMENT_DOES_NOT_EXIST)
        
        post_comment = PostComment.objects.create(
            user_id = user.id,
            text = text,
            is_reply_to_id = comment_id,
            post_id = post_id
        )

        return ReplyOnPostCommentMutation(comment=post_comment)

class Mutation(graphene.ObjectType):
    create_post = CreatePostMutation.Field()
    like_post = LikePostMutation.Field()
    unlike_post = UnlikePostMutation.Field()
    comment_on_post = CommentOnPostMutation.Field()
    reply_on_post_comment = ReplyOnPostCommentMutation.Field()


