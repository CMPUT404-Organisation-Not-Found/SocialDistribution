import json
from http.client import HTTPResponse
from urllib import request
from itertools import chain

from multiprocessing import context

from django.core import paginator
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.views import View
from rest_framework.decorators import api_view

from .models import Post, Comment, Inbox, Like
from .forms import PostForm, CommentForm, ShareForm
from django.shortcuts import render, get_object_or_404, redirect

from .models import Author, Post, FollowerCount
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, auth
from django.forms.models import model_to_dict
from django.views.generic.edit import UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .forms import PostForm, CommentForm
from .models import Author, Post, FollowerCount, Comment, Inbox, Category

from . import serializers, renderers, pagination
from .pagination import CustomPageNumberPagination
from django.http import HttpResponseRedirect

from ast import Delete

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, ListAPIView, RetrieveUpdateAPIView, RetrieveUpdateDestroyAPIView, \
    RetrieveAPIView, RetrieveDestroyAPIView
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework.renderers import JSONRenderer

import re
import base64


# Create your views here.
@method_decorator(login_required, name='dispatch')
class PostListView(View):
    def get(self, request, *args, **kwargs):
        # posts = Post.objects.all().order_by('-published')
        posts = Inbox.objects.filter(author__username=request.user.username)[0].items
        author_list = Author.objects.all()
        context = {
            'postList': posts,
            'author_list':author_list,
            # 'form': form,
        }
        return render(request,'feed.html', context)

@method_decorator(login_required, name='dispatch')
class NewPostView(View):
    def get(self, request, *args, **kwargs):
        form = PostForm()
        share_form = ShareForm()
        author_list = Author.objects.all()
        context = {
            'form': form,
            'share_form': share_form,
            'author_list':author_list,
        }
        return render(request,'newpost.html', context)

    def post(self, request, *args, **kwargs):
        posts = Post.objects.all()
        share_form = ShareForm()
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            newPost = form.save(commit=False)
            newPost.author = Author.objects.get(username=request.user.username)
            newPost.id = request.get_host()+ "/authors/" + str(newPost.author.uuid) + "/posts/" + str(newPost.uuid)
            newPost.save()
            unparsedCat = newPost.unparsedCategories
            catList = unparsedCat.split()
            for cat in catList:
                newCat = Category()
                newCat.cat = cat
                newCat.save()
                newPost.categories.add(newCat)
                newPost.save()


            if newPost.type == 'post':
                newPost.source = request.get_host()+ "/post/" + str(newPost.uuid)
                newPost.origin = request.get_host()+ "/post/" + str(newPost.uuid)
                newPost.comments = request.get_host()+ "/post/" + str(newPost.uuid)
                newPost.save()
            if newPost.post_image:
                # print("------url", newPost.post_image.path)
                # print(str(newPost.post_image))
                img_file = open(newPost.post_image.path, "rb")
                newPost.image_b64 = base64.b64encode(img_file.read())
                # print(newPost.image_b64[:20])
                newPost.save()

            Inbox.objects.filter(author__username=request.user.username)[0].items.add(newPost)
            followersID = FollowerCount.objects.filter(user=request.user.username)
            for followerID in followersID:
                Inbox.objects.filter(author__username=followerID.follower)[0].items.add(newPost)

        # posts = Post.objects.all()
        # context = {
        #     'postList': posts,
        #     # 'form': form,
        # }
        # return render(request,'myapp/newpost.html', context)
        return redirect('myapp:postList')

@method_decorator(login_required, name='dispatch')
class PostDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.get(uuid=pk)
        form = CommentForm()
        comments = Comment.objects.filter(post=post).order_by('-published')
        likes = Like.objects.filter(object=post)
        author_list = Author.objects.all()
        if post.post_image:
            image_b64 = post.image_b64.decode('utf-8')
        else:
            image_b64 = ''
        context = {
            'post': post,
            'form': form,
            'comments':comments,
            'likes': likes,
            'author_list':author_list,
            'image_b64':image_b64,
        }

        return render(request, 'postDetail.html', context)

    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(uuid=pk)
        form = CommentForm(request.POST)
        author_list = Author.objects.all()
        if form.is_valid():
            newComment = form.save(commit=False)
            newComment.author = Author.objects.get(username=request.user.username)
            newComment.post = post
            newComment.save()
            newComment.id = request.get_host()+ "/authors/" + str(post.author.uuid) + "/posts/" + str(pk) + "/comments/" + str(newComment.uuid)
            newComment.save()
            post.count += 1
            post.save()
            # reset form
            form = CommentForm()

        comments = Comment.objects.filter(post=post).order_by('-published')
        likes = Like.objects.filter(object=post)
        likes_count = len(Like.objects.filter(object=post))
        if post.image_b64 != None:
            image_b64 = post.image_b64.decode('utf-8')
            context = {
                'post': post,
                'form': form,
                'likes': likes,
                'likes_count': likes_count,
                'comments': comments,
                'author_list': author_list,
                'image_b64':image_b64,
            }
        else:
            context = {
                'post': post,
                'form': form,
                'likes': likes,
                'likes_count': likes_count,
                'comments': comments,
                'author_list': author_list,
            }

        return render(request, 'postDetail.html', context)

@method_decorator(login_required, name='dispatch')
class SharedPostView(View):
    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.get(uuid=pk)
        share_form = ShareForm()

        context = {
            'post': post,
            'form': share_form,
            # 'source_post': source_post,
            # 'original_post': original_post,
        }
        return render(request, 'share.html', context)

    def post(self, request, pk, *args, **kwargs):
        source_post = Post.objects.get(pk=pk)
        if source_post.type == 'post':
            source_text = request.get_host()+'/post/'
        else:
            source_text = request.get_host()+'/post/shared/'
        original_post_id = source_post.origin.split('/')[-1]
        original_post = Post.objects.get(uuid=original_post_id)
        form = ShareForm(request.POST)
        
        if form.is_valid():
            new_post = Post(
            type = 'share',
            title = self.request.POST.get('title'),
            source = source_text + str(pk),
            origin = original_post.origin,
            description = Post.objects.get(pk=pk).description,
            content = Post.objects.get(pk=pk).content,
            contentType = 'text',
            author = Author.objects.get(username=request.user.username),
            visibility = original_post.visibility, 
            )
        new_post.save()
        new_post.author = Author.objects.get(username=request.user.username)
        new_post.id = request.get_host()+ "/authors/" + str(new_post.author.uuid) + "/posts/" + str(new_post.uuid)
        new_post.save()
        Inbox.objects.filter(author__username=request.user.username)[0].items.add(new_post)
        followersID = FollowerCount.objects.filter(user=request.user.username)
        for followerID in followersID:
            Inbox.objects.filter(author__username=followerID.follower)[0].items.add(new_post)
        context = {
            'new_post': new_post,
            # 'source_post': source_post,
            # 'original_post': original_post,
            'form': form,
        }
        return redirect('myapp:postList')
        #return render(request, 'share.html', context)

@login_required(login_url='/accounts/login')
def like(request):
    username = request.user.username
    author = Author.objects.get(username=username)
    post_id = request.GET.get('post_id')
    post = Post.objects.get(uuid=post_id)
    summary = username + ' Likes your post'
    like_filter = Like.objects.filter(object=post, author=author).first()
    if like_filter == None:
        print(post, author)
        new_like = Like.objects.create(author=author, object=post)
        new_like.save()
        # like_text = 'Liked'
        post.likes += 1
        post.save()
        # return redirect('myapp:postList')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        like_filter.delete()
        # like_text='Like'
        post.likes -= 1
        post.save()
        # return redirect('myapp:postList')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@method_decorator(login_required, name='dispatch')
class ShareDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.get(uuid=pk)
        
        form = CommentForm()
        comments = Comment.objects.filter(post=post).order_by('-published')
        likes = Like.objects.filter(object=post)

        source_post_id = post.source.split('/')[-1]
        source_post = Post.objects.get(uuid=source_post_id)
        original_post_id = post.origin.split('/')[-1]
        original_post = Post.objects.get(uuid=original_post_id)

        context = {
            'post': post,
            'form': form,
            'comments':comments,
            'likes': likes,
            'source_post': source_post,
            'original_post': original_post,

        }

        return render(request, 'shareDetail.html', context)
    
    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(uuid=pk)
        form = CommentForm(request.POST)

        if form.is_valid():
            newComment = form.save(commit=False)
            newComment.author = Author.objects.get(username=request.user.username)
            newComment.post = post
            newComment.save()
            post.count += 1
            post.save()

        comments = Comment.objects.filter(post=post).order_by('-published')
        likes = Like.objects.filter(object=post)
        likes_count = len(Like.objects.filter(object=post))

        context = {
            'post': post,
            'form': form,
            'comments':comments,
            'likes': likes,
            'likes_count': likes_count,
            # 'source_post': source_post,
            'original_post': original_post,

        }

        return render(request, 'shareDetail.html', context)

@login_required(login_url='/accounts/login')
def liked(request, post_id):
    post = Post.objects.get(uuid=post_id)
    username = request.user.username
    likes_list = Like.objects.filter(object=post)
    context = {
        'likes_list': likes_list
    }
    return render(request, 'liked.html', context)
    # if 
    # like_text = 'Like'

@login_required(login_url='/accounts/login')
def profile(request, user_id):
    # get basic info
    current_author_info = get_object_or_404(Author, pk=user_id)
    follower = request.user.username
    user = user_id
    # get github info
    github_username = current_author_info.github.split("/")[-1]
    # get posts
    try:
        posts = Post.objects.filter(author__username=user_id).order_by('-published')
    except:
        posts = []
    # get follow
    if FollowerCount.objects.filter(follower=follower, user=user).first():
        button_text = 'Unfollow'
    else:
        button_text = 'Follow'
    count_followers = len(FollowerCount.objects.filter(user=user_id))
    count_following = len(FollowerCount.objects.filter(follower=user_id))
    author_list = Author.objects.all()
    context = {
        'current_author_info': current_author_info,
        'button_text': button_text,
        'count_followers': count_followers,
        'count_following': count_following,
        'github_username': github_username,
        'posts': posts,
        'author_list': author_list,
        }

    return render(request, 'profile.html', context)

@login_required(login_url='/accounts/login')
def follow(request):
    # print("follow is working")
    if request.method == 'POST':
        follower = request.POST['follower']
        user = request.POST['user']
        if FollowerCount.objects.filter(follower=follower, user=user).first():
            delete_follower = FollowerCount.objects.get(follower=follower, user=user)
            delete_follower.delete()
            return redirect('myapp:profile', user_id=user)
        else:
            new_follower = FollowerCount.objects.create(follower=follower, user=user)
            new_follower.save()
            return redirect('myapp:profile', user_id=user)
    else:
        return redirect('/')

@login_required(login_url='/accounts/login')
def search(request):
    author_list = Author.objects.all()
    return render(request, 'feed.html', {'author_list':author_list})

@login_required(login_url='/accounts/login')
def getuser(request):
    username = request.GET['username']
    try:
        current_author_info = Author.objects.get(displayName = username)
    except:
        current_author_info = None
    if current_author_info == None:
        author_list = Author.objects.all()
        context = {
            'username':username,
            'author_list':author_list,
        }
        return render(request, 'profileNotFound.html', context)
    # current_author_info = get_object_or_404(Author, displayName = username)
    else:
        user_id = current_author_info.username
        return redirect('myapp:profile', user_id=user_id)

@method_decorator(login_required, name='dispatch')
class PostEditView(UpdateView):
    model = Post
    fields = ['title','content','contentType','visibility']
    template_name = 'postEdit.html'

    def get_success_url(self):
        pk = self.kwargs['pk']
        return reverse_lazy('myapp:postDetail', kwargs={'pk':pk})

@method_decorator(login_required, name='dispatch')
class PostDeleteView(DeleteView):
    model = Post
    template_name = 'postDelete.html'
    success_url = reverse_lazy('myapp:postList')

#
# API
#

class AuthorAPIView(RetrieveUpdateAPIView):
    """ GET or PUT an Author object """
    # note that PUT is updating an author object

    serializer_class = serializers.AuthorSerializer
    lookup_field = "uuid"
    http_method_names = ['get', 'put']

    def get_queryset(self):
        uuid = self.kwargs['uuid']
        return Author.objects.filter(uuid=uuid)


class AuthorsAPIView(ListAPIView):
    """ GET Authors (with pagination support)"""
    # TODO pagination failed
    # resource https://www.youtube.com/watch?v=eaWzTMtrcrE&list=PLx-q4INfd95FWHy9M3Gt6NkUGR2R2yqT8&index=9
    serializer_class = serializers.AuthorSerializer
    pagination_class = CustomPageNumberPagination
    # renderer_classes = (renderers.AuthorsRenderer, )
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        serializer = serializers.AuthorSerializer(Author.objects.all(), many=True)
        return Response({"type": "authors", "items": serializer.data})


class FollowersAPIView(RetrieveAPIView):
    """ GET an Author's all followers """

    # serializer_class = serializers.FollowersSerializer
    # renderer_classes = (renderers.FollowersRenderer,)
    http_method_names = ['get']

    def retrieve(self, request, *args, **kwargs):
        queryset = []
        uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=uuid).first()
        followers = FollowerCount.objects.filter(user=author.username)
        for follower in followers:
            author = model_to_dict(Author.objects.filter(username=follower.follower).first())
            serializer = serializers.AuthorSerializer(author)
            queryset.append(serializer.data)
        response = {"type": "followers", "items": queryset}
        return Response(response)

class FollowerAPIView(RetrieveUpdateDestroyAPIView):
    """ GET if is a follower PUT a new follower DELETE an existing follower"""

    serializer_class = serializers.FollowersSerializer
    renderer_classes = [JSONRenderer]
    # TODO foreign author (currently our author)

    def usernames(self, *args, **kwargs):
        follower_uuid = self.kwargs['another_author']
        follower = Author.objects.filter(uuid=follower_uuid).first()
        user_uuid = self.kwargs['author']
        user = Author.objects.filter(uuid=user_uuid).first()
        return follower.username, user.username

    def relation_check(self, *args, **kwargs):
        usernames = self.usernames()
        followers = FollowerCount.objects.filter(user=usernames[1]).values_list('follower', flat=True)
        if usernames[0] in followers:
            return True
        return False

    def retrieve(self, request, *args, **kwargs):

        if self.relation_check():
            return Response({'following_relation_exist': 'True'})
        else:
            return Response({'following_relation_exist': 'False'})

    def put(self, request, *args, **kwargs):
        if self.relation_check():
            return Response({'following_relation_exist': 'True',
                             'following_relation_put': 'False'})
        else:
            try:
                usernames = self.usernames()
                FollowerCount.objects.create(follower=usernames[0], user=usernames[1])
                return Response({'following_relation_exist': 'False',
                                 'following_relation_put': 'True'})
            except:
                return Response({'following_relation_exist': 'False',
                                 'following_relation_put': 'False'})

    def delete(self, request, *args, **kwargs):
        if self.relation_check():
            usernames = self.usernames()
            relation = FollowerCount.objects.filter(follower=usernames[0]).filter(user=usernames[1])
            try:
                relation.delete()
                return Response({'following_relation_exist': 'True',
                                 'following_relation_delete': 'True'})
            except:
                return Response({'following_relation_exist': 'True',
                                 'following_relation_delete': 'False'})
        else:
            return Response({'following_relation_exist': 'False',
                                 'following_relation_delete': 'False'})

# TODO FollowRequest is not complete (after Project 2)


class PostAPIView(CreateModelMixin, RetrieveUpdateDestroyAPIView):
    """ GET POST PUT DELETE a post"""
    # note that POST is creating a new post
    # note that PUT is updating an existing post
    # TODO rewrite the PUT method

    serializer_class = serializers.PostSerializer
    # renderer_classes = (renderers.PostRenderer, )
    lookup_fields = ('pk', 'author')

    def get_queryset(self):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        post_id = self.kwargs['pk']
        return Post.objects.filter(uuid=post_id, author=author.username)

    def post(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        post_id = self.kwargs['pk']
        author = Author.objects.filter(uuid=author_uuid).first()
        if author is None:
            return HttpResponseNotFound("author not exist")
        data = request.data
        try:
            new_post = Post.objects.create(title=data["title"], uuid=post_id, description=data["description"],
                                           content=data["content"],
                                           contentType=data["contentType"], author=author,
                                           unparsedCategories=data["categories"],
                                           visibility=data["visibility"],
                                           image_b64=data["post_image"])
            unparsed_cat = new_post.unparsedCategories
            cat_list = unparsed_cat.split()
            for cat in cat_list:
                new_cat = Category()
                new_cat.cat = cat
                new_cat.save()
                new_post.categories.add(new_cat)
                new_post.save()

            new_post.id = request.get_host()+ "/authors/" + str(new_post.author.uuid) + "/posts/" + str(new_post.uuid)
            new_post.source = request.get_host()+ "/post/" + str(new_post.uuid)
            new_post.origin = request.get_host()+ "/post/" + str(new_post.uuid)
            new_post.comments = request.get_host()+ "/post/" + str(new_post.uuid)
            new_post.save()
        except Exception as e:
            return HttpResponseNotFound(e)

        Inbox.objects.filter(author__username=author.username)[0].items.add(new_post)
        followersID = FollowerCount.objects.filter(user=author.username)

        for followerID in followersID:
            Inbox.objects.filter(author__username=followerID.follower)[0].items.add(new_post)
        serializer = serializers.PostSerializer(new_post)
        return Response(serializer.data)


class PostsAPIView(CreateModelMixin, ListAPIView):
    """ GET all posts or POST a new post (with pagination support) """

    serializer_class = serializers.PostSerializer
    pagination_class = CustomPageNumberPagination
    # renderer_classes = (renderers.PostsRenderer, )
    lookup_field = 'author'

    def post(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        if author is None:
            return HttpResponseNotFound("author not exist")
        data = request.data
        try:
            new_post = Post.objects.create(title=data["title"], description=data["description"], content=data["content"],
                                          contentType=data["contentType"], author=author,
                                          unparsedCategories=data["categories"],
                                          visibility=data["visibility"],
                                          post_image=data["post_image"])
            unparsed_cat = new_post.unparsedCategories
            cat_list = unparsed_cat.split()
            for cat in cat_list:
                new_cat = Category()
                new_cat.cat = cat
                new_cat.save()
                new_post.categories.add(new_cat)
                new_post.save()

            new_post.save()
        except Exception as e:
            return HttpResponseNotFound(e)
        new_post.id = request.get_host() + "/authors/" + str(new_post.author.uuid) + "/posts/" + str(new_post.uuid)
        new_post.source = request.get_host()+ "/post/" + str(new_post.uuid)
        new_post.origin = request.get_host()+ "/post/" + str(new_post.uuid)
        new_post.comments = request.get_host()+ "/post/" + str(new_post.uuid)
        new_post.save()

        Inbox.objects.filter(author__username=author.username)[0].items.add(new_post)
        followersID = FollowerCount.objects.filter(user=author.username)

        for followerID in followersID:
            Inbox.objects.filter(author__username=followerID.follower)[0].items.add(new_post)
        serializer = serializers.PostSerializer(new_post)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        posts = Post.objects.filter(author=author.username, visibility="PUBLIC")
        serializer = serializers.PostSerializer(posts, many=True)
        return Response({"type": "posts", "items": serializer.data})


class ImagePostAPIView(RetrieveAPIView):
    """ GET an image post"""

    serializer_class = serializers.PostSerializer
    renderer_classes = (renderers.ImagePostRenderer, )
    lookup_fields = ('uuid', 'author')

    def get_queryset(self):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        post_id = self.kwargs['pk']
        return Post.objects.filter(uuid=post_id, author=author.username)


class CommentsAPIView(CreateModelMixin, ListAPIView):
    """ GET all comments or POST a new comment (with pagination support) """
    # TODO pagination failed
    serializer_class = serializers.CommentsSerializer
    pagination_class = CustomPageNumberPagination
    # renderer_classes = (renderers.CommentsRenderer, )
    lookup_fields = ('post', )

    def list(self, request, *args, **kwargs):
        post_id = self.kwargs['post']
        serializer = serializers.CommentsSerializer(Comment.objects.filter(post=post_id), many=True)
        return Response({"type": "comments", "items": serializer.data})

    def post(self, request, *args, **kwargs):
        current_user_uuid = self.kwargs['author']
        current_user = Author.objects.filter(uuid=current_user_uuid).first()
        post_id = self.kwargs['post']
        post = Post.objects.filter(uuid=post_id).first()
        if current_user is None or post is None:
            return HttpResponseNotFound("author or post not exist")

        data = request.data
        new_comment = Comment.objects.create(author=current_user, comment=data["comment"],
                                             contentType=data["contentType"], post=post)
        new_comment.save()
        new_comment.id = request.get_host() + "/authors/" + str(post.author.uuid) + "/posts/" + str(
            post.uuid) + "/comments/" + str(new_comment.uuid)
        new_comment.save()
        post.count += 1
        post.save()
        serializer = serializers.CommentsSerializer(new_comment)
        return Response(serializer.data)

# TODO Like API - 1: send a like object


class LikesAPIView(ListAPIView):
    serializer_class = serializers.LikesSerializer
    pagination_class = CustomPageNumberPagination
    # renderer_classes = (renderers.LikesRenderer,)
    lookup_fields = ('object', )

    def get_queryset(self):
        post_id = self.kwargs['post']
        return Like.objects.filter(object=post_id)

# TODO Like API - 3: comment likes


class LikedAPIView(ListAPIView):
    serializer_class = serializers.LikesSerializer
    pagination_class = CustomPageNumberPagination
    # renderer_classes = (renderers.LikedRenderer,)
    lookup_fields = ('author',)

    def list(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        like = Like.objects.filter(object__visibility="PUBLIC", author=author.username)
        serializer = serializers.LikesSerializer(like, many=True)
        return Response({"type": "liked", "items": serializer.data})

class InboxAPIView(CreateModelMixin, RetrieveDestroyAPIView):
    """ GET inbox POST post/follow/like DELETE inbox_obj"""
    serializer_class = serializers.InboxSerializer
    pagination_class = CustomPageNumberPagination
    lookup_fields = ('author',)

    def get_object(self):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        return Inbox.objects.filter(author=author.username).first()

    def post(self, request, *args, **kwargs):
        # check if user in url exists
        current_username = self.kwargs['author']
        current_user = Author.objects.filter(username=current_username).first()
        if current_user is None:
            return HttpResponseNotFound("author (in url) not exist")
        data = request.data

        try:
            # 1. publish a post
            # don't care if these two have a friend relation, just push the post into its follower's inbox
            if data["type"] == "post":
                # check if user in the body (who post the post) exists
                author = Author.objects.filter(username=data["author"]).first()
                if author is None:
                    return HttpResponseNotFound("author (in body) not exist")

                new_post = Post.objects.create(title=data["title"], description=data["description"],
                                               content=data["content"],
                                               contentType=data["contentType"], author=author,
                                               unparsedCategories=data["unparsedCategories"],
                                               visibility=data["visibility"],
                                               post_image=data["post_image"])
                unparsed_cat = new_post.unparsedCategories
                cat_list = unparsed_cat.split()
                for cat in cat_list:
                    new_cat = Category()
                    new_cat.cat = cat
                    new_cat.save()
                    new_post.categories.add(new_cat)
                    new_post.save()

                try:
                    new_post.save()
                except Exception as e:
                    return HttpResponseNotFound(e)
                new_post.id = request.get_host() + "/authors/" + str(new_post.author.uuid) + "/posts/" + str(
                    new_post.uuid)
                new_post.source = request.get_host() + "/post/" + str(new_post.uuid)
                new_post.origin = request.get_host() + "/post/" + str(new_post.uuid)
                new_post.comments = request.get_host() + "/post/" + str(new_post.uuid)
                new_post.save()

                Inbox.objects.filter(author__username=author.username)[0].items.add(new_post)
                followersID = FollowerCount.objects.filter(user=author.username)

                for followerID in followersID:
                    Inbox.objects.filter(author__username=followerID.follower)[0].items.add(new_post)

                serializer = serializers.PostSerializer(new_post)
                return Response(serializer.data)
            # TODO 2. friend request
            elif data["type"] == "friend_request":
                pass

            elif data["type"] == "like":
                # check if post in the body (the post that user gives a like) exists
                post = Post.objects.filter(uuid=data["object"]).first()
                if post is None:
                    return HttpResponseNotFound("post not exist")
                like_before = Like.objects.filter(author=current_user, object=post).first()
                if like_before is not None:
                    return HttpResponseNotFound("user has given a like before")
                new_like = Like.objects.create(author=current_user, object=post)
                new_like.save()
                post.likes += 1
                post.save()
                # TODO like could be comments/posts
                serializer = serializers.LikeSerializer(new_like)
                # TODO push into inbox
                return Response(serializer.data)

        except Exception as e:
            return HttpResponseNotFound(e)

    def delete(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        inbox = Inbox.objects.filter(author=author.username).first()
        inbox.delete()
        new_inbox = Inbox.objects.create(author=author)
        new_inbox.save()

        serializer = serializers.InboxSerializer(new_inbox)
        return Response(serializer.data)

