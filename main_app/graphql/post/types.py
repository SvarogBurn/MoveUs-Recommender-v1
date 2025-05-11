import graphene

from main_app.util import generate_post_picture_url

from ...models import Post, PostComment
from ..object_type import MUObjectType


class PostCommentType(MUObjectType):
    has_replies = graphene.Boolean()

    class Meta:
        model = PostComment
        include = ('id', 'user', 'text', 'time_posted', 'replies')

    def resolve_has_replies(self: PostComment, info):
        return self.replies.count() != 0

class PostTypeMixin(MUObjectType):
    likes = graphene.Int()
    comments = graphene.List(PostCommentType, start=graphene.Int(default_value=0), end=graphene.Int(default_value=10))

    class Meta:
        model = Post

    def resolve_likes(self: Post, info, **kwargs):
        return self.liked_by.count()
    
    def resolve_comments(self: Post, info, start, end, **kwargs):
        return PostComment.objects.order_by('time_posted').reverse().filter(post=self, is_reply_to__isnull = True)[start:end]

class CreatePostType(PostTypeMixin):
    image_upload_URL = graphene.String()

    class Meta:
        model = Post

    def resolve_image_upload_URL(self: Post, info):
        return generate_post_picture_url(self.id)


class PostType(PostTypeMixin):

    class Meta:
        model = Post


    
