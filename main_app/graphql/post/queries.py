import graphene

from .types import PostType, PostCommentType
from ...models import Post

class PostQuery(graphene.ObjectType):
    post = graphene.Field(PostType, id=graphene.Int())
    event_posts = graphene.List(PostType, event_id=graphene.String(default_value=None), start=graphene.Int(default_value=0), end=graphene.Int(default_value=10))
    global_posts = graphene.List(PostType, start=graphene.Int(default_value=0), end=graphene.Int(default_value=10))

    def resolve_post(root, info, id):
        return Post.objects.get(pk=id)
    
    def resolve_event_posts(root, info, event_id, start, end):
        if event_id:
            return Post.objects.order_by('time_posted').reverse().filter(event = event_id)[start:end]
        return Post.objects.order_by('time_posted').reverse().filter(event__isnull=False)[start:end]
    
    def resolve_global_posts(root, info, start, end):
        return Post.objects.order_by('time_posted').reverse().filter()[start:end]
    
class CommentQuery(graphene.ObjectType):
    replies = graphene.List(PostCommentType, comment_id=graphene.ID())

    def resolve_replies(root, info, comment_id):
        pass