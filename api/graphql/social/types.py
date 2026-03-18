import graphene

from api.graphql.object_type import MUObjectType
from main.social.models import Comment, Follow, Post
from main.social.services import CommentService, PostService
from main.user.models import User
from shared.storage import storage_backend


class CommentType(MUObjectType):
    has_replies = graphene.Boolean()
    likes = graphene.Int()
    is_liked = graphene.Boolean()

    class Meta:
        model = Comment
        include = ("id", "user", "text", "time_posted", "replies")

    def resolve_has_replies(self: Comment, info: graphene.ResolveInfo) -> bool:
        return CommentService.has_replies(self.id)

    def resolve_likes(self: Comment, info: graphene.ResolveInfo) -> int:
        return CommentService.get_like_count(self.id)

    def resolve_is_liked(self: Comment, info: graphene.ResolveInfo) -> bool:
        return CommentService.is_liked_by(self.id, info.context.user.id)


class PostTypeMixin(MUObjectType):
    author = graphene.Field(
        graphene.lazy_import("api.graphql.user.types.UserType")
    )
    likes = graphene.Int()
    is_liked = graphene.Boolean()
    comments = graphene.List(
        CommentType,
        start=graphene.Int(default_value=0),
        end=graphene.Int(default_value=10),
    )

    class Meta:
        model = Post

    def resolve_likes(self: Post, info: graphene.ResolveInfo, **kwargs) -> int:
        return PostService.get_like_count(self.id)

    def resolve_is_liked(self: Post, info: graphene.ResolveInfo, **kwargs) -> bool:
        return PostService.is_liked_by(self.id, info.context.user.id)

    def resolve_comments(
        self: Post, info: graphene.ResolveInfo, start: int, end: int, **kwargs
    ):
        return CommentService.get_comments_for_post(self.id, start, end)


class CreatePostType(PostTypeMixin):
    image_upload_URL = graphene.String()

    class Meta:
        model = Post

    def resolve_image_upload_URL(self: Post, info: graphene.ResolveInfo) -> str:
        return storage_backend.generate_post_picture_url(self.id)


class PostType(PostTypeMixin):

    class Meta:
        model = Post

class FollowType(MUObjectType):

    user = graphene.Field(graphene.lazy_import("api.graphql.user.types.UserType"))

    class Meta:
        model = Follow
        fields = ("time_created",)

    def resolve_user(self: Follow, info: graphene.ResolveInfo) -> User | None:
        if info.context.user is None:
            return None
        if self.follower_id == info.context.user.id:
            return self.following
        return self.follower
