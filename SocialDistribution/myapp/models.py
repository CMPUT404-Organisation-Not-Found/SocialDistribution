import uuid
from django.db import models
from django.utils.timezone import localtime
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


# Create your models here.
class Author(models.Model):
    type = models.CharField(default="author", max_length=200)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=True)
    id = models.CharField(max_length=200)
    username = models.CharField(unique=True, max_length=200, primary_key=True)

    # id = models.UUIDField(default=uuid.uuid4,
    #                       editable=False,
    #                       unique=True,
    #                       primary_key=True)
    host = models.CharField(max_length=200)
    displayName = models.CharField(max_length=200, null=True)
    github = models.CharField(max_length=200, null=True)
    profileImage = models.CharField(max_length=500, null=True, blank=True)


class Authors(models.Model):
    type = models.CharField(default='authors', max_length=200)
    items = models.ManyToManyField(to=Author)


class Category(models.Model):
    cat = models.CharField(max_length=50)

    def __str__(self):
        return self.cat


class Followers(models.Model):
    type = models.CharField(default='followers', max_length=200)
    user = models.OneToOneField(to=Author,
                                on_delete=models.CASCADE,
                                related_name='user')
    items = models.ManyToManyField(to=Author, related_name='items', blank=True)

    def to_dict(self):
        return {
            'type': self.type,
            'users_following': self.items,
            'user_followed': self.user,
        }

    def __str__(self):
        return self.user.username

    # def add_friend(self):
    #     pass


class Inbox(models.Model):
    type = models.CharField(default='inbox', max_length=200)
    author = models.ForeignKey(to=Author, on_delete=models.CASCADE)

    # for reverse lookup of inbox items
    # https://stackoverflow.com/questions/15306897/django-reverse-lookup-of-foreign-keys

    def __str__(self) -> str:
        return f"{self.author.username}'s inbox"

    def to_dict(self):
        return {
            'type': self.type,
            'author': self.author.username,
            # 'items_object': self.items_object.to_dict()
        }


class InboxItem(models.Model):
    inbox = models.ForeignKey(to=Inbox, on_delete=models.CASCADE)
    # model field in choices {like, post, comment, friendfollowrequest}
    choices = [("like", "like"), ("post", "post"), ("comment", "comment"),
               ("friendfollowrequest", "friendfollowrequest")]
    inbox_item_type = models.CharField(max_length=20, choices=choices)

    # if inbox item is read
    is_read = models.BooleanField(default=False)

    # GFK to {like, post, comment, friendfollowrequest}
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    item_id = models.CharField(max_length=255)
    item = GenericForeignKey('content_type', 'item_id')

    def __str__(self) -> str:
        return f"{self.inbox.author.username}'s {self.inbox_item_type}: {self.content_type}, {self.item_id}"

    def to_dict(self) -> dict:
        return {
            'inbox_item_type': self.inbox_item_type,
            'content_type': self.content_type,
            'item_id': self.item_id,
            'item': self.item.to_dict()
        }


class FollowerCount(models.Model):
    # follower is who logged in now # user.usernamr
    follower = models.CharField(max_length=100)
    user = models.CharField(max_length=100)

    def __str__(self):
        return self.user


class FriendFollowRequest(models.Model):
    type = models.CharField(default='Follow', max_length=200)
    summary = models.TextField()
    actor = models.ForeignKey(to=Author,
                              on_delete=models.CASCADE,
                              related_name='%(class)s_request_sender')
    object = models.ForeignKey(to=Author,
                               on_delete=models.CASCADE,
                               related_name='%(class)s_request_receiver')
    inbox = GenericRelation(InboxItem)

    def __str__(self):
        return self.actor.username

    def accept(self):
        Followers.objects.get(user=self.object).items.add(self.actor)
        self.delete()


# if object_friend_list:
# 	object_friend_list.add_friend(self.sender)
# 	sender_friend_list = Followers.objects.get(user=self.sender)
# 	if sender_friend_list:
# 		sender_friend_list.add_friend(self.receiver)
# 		self.is_active = False
# 		self.save()


class Post(models.Model):
    type = models.CharField(default='post', max_length=200)
    title = models.CharField(max_length=200)
    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=True,
                            unique=True,
                            primary_key=True)
    id = models.CharField(max_length=200)
    source = models.CharField(max_length=200)
    origin = models.CharField(max_length=200)
    description = models.TextField()
    content = models.TextField()
    CONTENT_CHOICES = [("text/plain", "Plaintext"),
                       ("text/markdown", "Markdown"),
                       ("application/base64", "app"),
                       ("image/png;base64", "png"),
                       ("image/jpeg;base64", "jpeg")]
    contentType = models.CharField(max_length=30, choices=CONTENT_CHOICES)
    author = models.ForeignKey(to=Author, on_delete=models.CASCADE)
    unparsedCategories = models.CharField(max_length=100, default="")
    categories = models.ManyToManyField(Category)
    count = models.IntegerField(default=0)
    comments = models.TextField(default="http://localhost:8000/")
    # commentsSrc = models.ForeignKey(to=Comment, on_delete=models.CASCADE)
    published = models.DateTimeField(default=localtime,
                                     blank=True,
                                     editable=False)
    # TO-DO: check if "private" is needed
    VISIBILITY_CHOICES = [("PUBLIC", "Public"), ("FRIENDS", "Friends"),
                          ("PRIVATE", "Specific friend")]
    visibility = models.CharField(max_length=7,
                                  choices=VISIBILITY_CHOICES,
                                  default="PUBLIC")
    unlisted = models.BooleanField(default=False)
    likes = models.IntegerField(default=0)
    post_image = models.ImageField(null=True, blank=True, upload_to='images/')
    image_b64 = models.BinaryField(blank=True, null=True)
    inbox = GenericRelation(InboxItem)
    # def save(self, *args, **kwargs):
    #     if self.post_image:
    #         img_file = open(self.post_image.url, "rb")
    #         self.image_b64 = base64.b64encode(img_file.read())
    #         super(Image, self).save(*args, **kwargs)


class Like(models.Model):
    type = models.CharField(default='Like', max_length=200)
    # summary = models.TextField()
    # content = models.TextField()
    author = models.ForeignKey(to=Author, on_delete=models.CASCADE)
    object = models.ForeignKey(to=Post, on_delete=models.CASCADE)
    inbox = GenericRelation(InboxItem)


class Comment(models.Model):
    type = models.CharField(default='comment', max_length=200)
    author = models.ForeignKey(to=Author, on_delete=models.CASCADE)
    comment = models.TextField()
    CONTENT_CHOICES = [("text/plain", "Plaintext"),
                       ("text/markdown", "Markdown")]
    contentType = models.CharField(max_length=30, choices=CONTENT_CHOICES)
    published = models.DateTimeField(default=localtime,
                                     blank=True,
                                     editable=False)
    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=False,
                            unique=True,
                            primary_key=True)
    id = models.CharField(max_length=200)
    post = models.ForeignKey(to=Post, on_delete=models.CASCADE, null=True)
    inbox = GenericRelation(InboxItem)


class Liked(models.Model):
    type = models.CharField(default='liked', max_length=200)
    items = models.ManyToManyField(to=Like)


class ConnectionNode(models.Model):
    """
        Class to contain the connection node information of other
        nodes
        service_url INCLUDES the backslash at the end
    """
    name = models.CharField(max_length=255)
    url = models.URLField()
    auth_username = models.CharField(max_length=255)
    auth_password = models.CharField(max_length=255)

    class Meta:
        verbose_name = "connection node"
        verbose_name_plural = "connection nodes"

    def __str__(self):
        return str(self.name)

    def to_dict(self):
        return {
            'name': self.name,
            'service_url': self.url,
            'auth_username': self.auth_username,
            'auth_password': self.auth_password
        }