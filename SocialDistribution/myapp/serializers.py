from django.forms import model_to_dict
from rest_framework import serializers, pagination
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer
from . import models
from .models import Author, Post, Comment, Like, Inbox, InboxItem, FriendFollowRequest


class AuthorSerializer(ModelSerializer):

    class Meta:
        model = models.Author
        fields = ('type', 'id', 'username', "host", "displayName", "github",
                  "profileImage")


# class SingleAuthorSerializer(ModelSerializer):
#
#     class Meta:
#         model = models.Author
#         fields = '__all__'


class FollowersSerializer(ModelSerializer):

    class Meta:
        model = models.FollowerCount
        fields = '__all__'


class FriendFollowRequestSerializer(ModelSerializer):

    class Meta:
        model = models.FriendFollowRequest
        # fields = '__all__'
        fields = ("type", "summary", "actor", "object")
        depth = 1


class PostSerializer(ModelSerializer):
    author = AuthorSerializer()
    categories = serializers.SerializerMethodField('get_categories')

    def get_categories(self, obj):
        post = model_to_dict(obj)
        categories = post.get("categories")
        lst = []
        for i in categories:
            category = model_to_dict(i)
            lst.append(category.get("cat"))
        return lst

    class Meta:
        model = models.Post
        fields = ("type", "title", "id", "source", "origin", "description",
                  "content", "contentType", "author", "categories", "count",
                  "comments", "published", "visibility", "unlisted", "likes",
                  "image_b64")
        depth = 1


class CommentsSerializer(ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = models.Comment
        fields = ("type", "author", "comment", "contentType", "published",
                  "id")


class LikesSerializer(ModelSerializer):
    author = AuthorSerializer()
    object = serializers.SerializerMethodField('get_object')

    class Meta:
        model = models.Like
        fields = ("type", "author", "object")

    def get_object(self, obj):
        like = model_to_dict(obj)
        post_uuid = like.get("object")
        post = Post.objects.filter(uuid=post_uuid).first()
        return model_to_dict(post).get("id")


# class LikeSerializer(ModelSerializer):
#
#     class Meta:
#         model = models.Like
#         fields = '__all__'
#         depth = 1


class InboxSerializer(ModelSerializer):
    author = serializers.SerializerMethodField('get_author')
    items = serializers.SerializerMethodField('get_items')

    class Meta:
        model = models.Inbox
        fields = ('type', "author", "items")
        depth = 1

    def get_author(self, obj):
        inbox = model_to_dict(obj)
        author_username = inbox.get("author")
        author = Author.objects.filter(username=author_username).first()
        return model_to_dict(author).get("id")

    def get_items(self, obj):
        inbox = obj  # obj is inbox object
        # get items from the inbox
        # for each item call its serializer method
        # return the serialized items
        items = inbox.inboxitem_set.all()
        itemArray = []
        for item in items:
            if item.inbox_item_type == "post":
                postObject = Post.objects\
                    .filter(uuid=item.item_id).first()
                itemArray.append(PostSerializer(postObject).data)

            elif item.inbox_item_type == "comment":
                commentObject = Comment.objects\
                    .filter(uuid=item.item_id).first()
                itemArray.append(CommentsSerializer(commentObject).data)

            elif item.inbox_item_type == "like":
                likeObject = Like.objects\
                    .filter(id=item.item_id).first()
                itemArray.append(LikesSerializer(likeObject).data)

            elif item.inbox_item_type == "friend_follow_request":
                friendFollowRequestObject = FriendFollowRequest.objects\
                    .filter(id=item.item_id).first()
                itemArray.append(
                    FriendFollowRequestSerializer(friendFollowRequestObject)\
                        .data)
        return itemArray
