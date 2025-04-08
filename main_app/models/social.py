from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from .enums import ChatNotifications, RelationshipStatus

class Chat(models.Model):
    time_created = models.DateTimeField(auto_now_add=True)
    img_url = models.URLField(default="default.png")

class ChatMember(models.Model):
    pk = CompositePrimaryKey('user', 'chat')
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=64)
    last_open = models.DateTimeField(null=True)
    notifications = models.SmallIntegerField(choices=ChatNotifications.choices(), default=ChatNotifications.ALL)

class ChatMessage(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=False)
    text_content = models.CharField()
    time_sent = models.DateTimeField()

class Relationship(models.Model):
    pk = CompositePrimaryKey('user_1', 'user_2')
    user_1 = models.ForeignKey("User", on_delete=models.CASCADE, null=False, related_name='friends_added')
    user_2 = models.ForeignKey("User", on_delete=models.CASCADE, null=False, related_name='friends_added_by')
    last_update = models.DateTimeField(auto_now_add=True)
    status = models.SmallIntegerField(choices=RelationshipStatus.choices())
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, null=True)

class Post(models.Model):
    title = models.CharField(max_length=128)
    content = models.CharField()
    time_posted = models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey("Event", on_delete=models.CASCADE, null=True)
    liked_by = models.ManyToManyField("User")

class PostComment(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments" ,null=False)
    text = models.CharField(max_length=512)
    time_posted = models.DateTimeField(auto_now_add=True)
    is_reply_to = models.ForeignKey('PostComment', on_delete=models.CASCADE, related_name="replies", null=True)

    def get_tree(self):
        self.descendents = list(self.replies.all())
        for child in self.descendents:
            child.get_tree()
        

class Attachment(models.Model):
    url = models.URLField(null=False)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
