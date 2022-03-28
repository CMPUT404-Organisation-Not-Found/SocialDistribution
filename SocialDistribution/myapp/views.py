import json
from http.client import HTTPResponse
from urllib import request
from itertools import chain
import requests
from multiprocessing import context

from django.core import paginator
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.views import View
from rest_framework.decorators import api_view

from .models import InboxItem, Post, Comment, Inbox, Like, Followers
from .forms import PostForm, CommentForm, ShareForm
from django.shortcuts import render, get_object_or_404, redirect

from .models import Author, Post, FriendFollowRequest
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
from requests.auth import HTTPBasicAuth

import re
import base64

nodeArray = [
    'https://cmput404-w22-project-backend.herokuapp.com/service/',
    'https://cmput4042ndnetwork.herokuapp.com/service/',
    'https://social-dist-wed.herokuapp.com/service/'
]
authDict = {
    'https://cmput404-w22-project-backend.herokuapp.com/service/':
    ['proxy', 'proxy123!'],
    'https://cmput4042ndnetwork.herokuapp.com/service/': ['admin', 'admin'],
    'https://social-dist-wed.herokuapp.com/service/': ['team02admin', 'admin']
}

# nodeArray = ['https://social-dist-wed.herokuapp.com/service/']
# nodeArray = ['http://127.0.0.1:7080/service/']
localHostList = [
    'http://127.0.0.1:7070/', 'http://127.0.0.1:8000/', 'https://localhost:8000',
    'http://localhost:8000', 'https://c404-social-distribution.herokuapp.com/'
]


# Create your views here.
@method_decorator(login_required, name='dispatch')
class PostListView(View):

    def get(self, request, *args, **kwargs):
        # getting all posts object from inbox
        currentUser = request.user
        currentInbox = Inbox.objects.filter(
            author__username=currentUser.username).first()
        posts = currentInbox.inboxitem_set.filter(inbox_item_type="post")
        responsePosts = []
        for post in posts:
            responsePosts.append(post.item)
        # sort responsePosts by published
        responsePosts.sort(key=lambda x: x.published, reverse=True)

        for node in nodeArray:
            # make get request to other notes /service/authors/
            response = requests.get(f"{node}authors/",
                                    params=request.GET,
                                    auth=HTTPBasicAuth(authDict[node][0],
                                                       authDict[node][1]))
            if response.status_code == 200:
                response_contents = response.json()['items']
                for author in response_contents:
                    if Author.objects.filter(id=author['id']).exists():
                        continue
                    remote_author = Author(
                        id=author['id'],
                        username=author['id'].split("/")
                        [-1],  # username = remote_author.uuid
                        displayName=author['displayName'],
                        host=author['host'],
                        github=author['github'],
                        profileImage=author['profileImage'])
                    remote_author.save()
            else:
                print("FAILURE")
            print(response)

        author_list = Author.objects.all()
        context = {
            'postList': responsePosts,
            'author_list': author_list,
            # 'form': form,
        }
        return render(request, 'feed.html', context)


@method_decorator(login_required, name='dispatch')
class NewPostView(View):

    def get(self, request, *args, **kwargs):
        form = PostForm()
        share_form = ShareForm()
        author_list = Author.objects.all()
        context = {
            'form': form,
            'share_form': share_form,
            'author_list': author_list,
        }
        return render(request, 'newpost.html', context)

    def post(self, request, *args, **kwargs):
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            # creating post from form and adding attributes
            newPost = form.save(commit=False)
            newPost.author = Author.objects.get(username=request.user.username)
            newPost.id = request.get_host() + "/authors/" + str(
                newPost.author.uuid) + "/posts/" + str(newPost.uuid)

            # adding categories to post
            unparsedCat = newPost.unparsedCategories
            catList = unparsedCat.split()
            newPost.save()
            for cat in catList:
                newCat = Category()
                newCat.cat = cat
                newCat.save()
                newPost.categories.add(newCat)
                newPost.save()

            # not sure what its for but it works
            if newPost.type == 'post':
                newPost.source = request.get_host() + "/post/" + str(
                    newPost.uuid)
                newPost.origin = request.get_host() + "/post/" + str(
                    newPost.uuid)
                newPost.comments = request.get_host() + "/post/" + str(
                    newPost.uuid) + '/comments'
                newPost.save()

            # if its an image
            if newPost.post_image:
                # print("------url", newPost.post_image.path)
                # print(str(newPost.post_image))
                img_file = open(newPost.post_image.path, "rb")
                newPost.image_b64 = base64.b64encode(img_file.read())
                # print(newPost.image_b64[:20])
                newPost.save()

            # adding post to inbox of current author
            # add post to InboxItem which links to Inbox
            InboxItem.objects.create(
                inbox=Inbox.objects.filter(
                    author__username=request.user.username).first(),
                inbox_item_type="post",
                item=newPost,
            )

            user = Author.objects.get(username=request.user.username)
            try:
                followersID = Followers.objects.filter(
                    user__username=user.username).first().items.all()
                for follower in followersID:
                    # follower is <author> object
                    # breakpoint()
                    if follower.host in localHostList:
                        # add it to inbox of follower
                        InboxItem.objects.create(
                            inbox=Inbox.objects.filter(
                                author__username=follower.username).first(),
                            inbox_item_type="post",
                            item=newPost,
                        )
                    else:
                        # if author is not local make post request to add to other user inbox
                        serializer = serializers.PostSerializer(newPost)

                        ### from stack overflow https://stackoverflow.com/questions/20658572/python-requests-print-entire-http-request-raw
                        authDictKey = follower.host + "/service/"
                        req = requests.Request(
                            'POST',
                            f"{follower.host}/service/authors/{follower.username}/inbox",
                            data=json.dumps(serializer.data),
                            auth=HTTPBasicAuth(authDict[authDictKey][0],
                                               authDict[authDictKey][1]),
                            headers={'Content-Type': 'application/json'})
                        prepared = req.prepare()

                        s = requests.Session()
                        resp = s.send(prepared)

                        print("status code, ", resp.status_code)

            except AttributeError as e:
                print(e, 'No followers for this author')

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
            'comments': comments,
            'likes': likes,
            'author_list': author_list,
            'image_b64': image_b64,
        }

        return render(request, 'postDetail.html', context)

    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(uuid=pk)
        form = CommentForm(request.POST)
        author_list = Author.objects.all()
        if form.is_valid():
            newComment = form.save(commit=False)
            newComment.author = Author.objects.get(
                username=request.user.username)
            newComment.post = post
            newComment.save()
            newComment.id = request.get_host() + "/authors/" + str(
                post.author.uuid) + "/posts/" + str(pk) + "/comments/" + str(
                    newComment.uuid)
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
                'image_b64': image_b64,
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
    """
        View for sharing posted posts (or something like that)
    """

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
        # source_post is the currently selected post to be shared
        source_post = Post.objects.get(pk=pk)
        # TODO: SU: please confirm that this is accepted behaviour.
        if source_post.type == 'post':
            source_text = request.get_host() + '/post/'
        else:
            source_text = request.get_host() + '/post/shared/'
        original_post_id = source_post.origin.split('/')[-1]
        original_post = Post.objects.get(uuid=original_post_id)
        form = ShareForm(request.POST)

        if form.is_valid():
            new_post = Post(
                #TODO: Su: please confirm that type is allowed to be updated
                # eg if author.user is not the same as the user who is sharing the post
                type='share',
                title=self.request.POST.get('title'),
                source=source_text + str(pk),
                origin=original_post.origin,
                description=Post.objects.get(pk=pk).description,
                content=Post.objects.get(pk=pk).content,
                contentType='text',
                author=Author.objects.get(username=request.user.username),
                visibility=original_post.visibility,
            )
            new_post.save()
            new_post.id = request.get_host() + "/authors/" + str(
                new_post.author.uuid) + "/posts/" + str(new_post.uuid)
            new_post.save()

        # adding post to request.user's inbox
        InboxItem.objects.create(
            inbox=Inbox.objects.filter(
                author__username=request.user.username).first(),
            inbox_item_type='post',
            item=new_post,
        )

        try:
            followers = Followers.objects.get(
                user__username=request.user.username).items.all()
            # followersID = FollowerCount.objects.filter(user=request.user.username)
            for follower in followers:
                # follower is <author> object
                InboxItem.objects.create(
                    inbox=Inbox.objects.filter(
                        author__username=follower.username).first(),
                    inbox_item_type='post',
                    item=new_post,
                )
                # TODO: darren make this work for remote authors too (just call API or something lol)
        except Exception as e:
            print(e, 'No followers for this author')

        context = {
            'new_post': new_post,
            # 'source_post': source_post,
            # 'original_post': original_post,
            'form': form,
        }
        return redirect('myapp:postList')


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
        # push like object into inbox
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
            'comments': comments,
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
            newComment.author = Author.objects.get(
                username=request.user.username)
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
            'comments': comments,
            'likes': likes,
            'likes_count': likes_count,
            # 'source_post': source_post,
            # 'original_post': original_post,
        }

        return render(request, 'shareDetail.html', context)


@login_required(login_url='/accounts/login')
def liked(request, post_id):
    post = Post.objects.get(uuid=post_id)
    username = request.user.username
    likes_list = Like.objects.filter(object=post)
    context = {'likes_list': likes_list}
    return render(request, 'liked.html', context)
    # if
    # like_text = 'Like'


@login_required(login_url='/accounts/login')
def profile(request, user_id):
    # get basic info
    current_author_info = get_object_or_404(Author, pk=user_id)
    actor = Author.objects.filter(username=request.user.username).first()
    object = Author.objects.filter(username=user_id).first()
    # get github info
    github_username = current_author_info.github.split("/")[-1]

    localURL = f"http://{request.get_host()}/service/"
    posts = []

    response_contents = None
    # original UUID from Original server for current_author_info
    current_author_original_uuid = current_author_info.id.split('/')[-1]

    # use API calls to get posts
    modifiedNodeArray = nodeArray.copy()  # adding our local to node array
    # modifiedNodeArray.append(localURL)
    for node in modifiedNodeArray:
        response = requests.get(
            f"{node}authors/{current_author_original_uuid}/posts/",
            params=request.GET,
            auth=HTTPBasicAuth(authDict[node][0], authDict[node][1]))
        if response.status_code == 200:
            response_contents = response.json()['items']
            posts = response_contents
        else:
            pass

    # add UUID to posts object
    for post in posts:
        post['uuid'] = post['id'].split('/')[-1]
    # get follow
    if FriendFollowRequest.objects.filter(
            actor__username=actor.username,
            object__username=object.username).first():
        button_text = 'Friend Request Sent'
    else:
        button_text = 'Send Friend Request'
    user = Author.objects.get(username=user_id)
    try:
        count_followers = len(
            Followers.objects.filter(user=user)[0].items.all())
    except:
        count_followers = 0
    author_list = Author.objects.all()
    context = {
        'current_author_info': current_author_info,
        'button_text': button_text,
        'count_followers': count_followers,
        'github_username': github_username,
        'posts': posts,
        'author_list': author_list,
    }
    # breakpoint()
    return render(request, 'profile.html', context)


@login_required(login_url='/accounts/login')
def follow(request):
    # print("follow is working")
    # payload = {}
    if request.method == 'POST':
        actorName = request.POST['follower']
        objectName = request.POST['user']
        # actor = Author.objects.filter(username=actorName).first()
        # actorName = request.user.username
        actor = Author.objects.filter(username=actorName).first()
        # object_id = request.POST.get("receiver_user_id")
        object = Author.objects.filter(username=objectName).first()
        # objectName = object.displayName

        if FriendFollowRequest.objects.filter(actor=actor, object=object):
            pass
            # delete_follower = FriendFollowRequest.objects.get(actor=actor, object=object)
            # delete_follower.delete()
            # raise Exception('Friend request canceled')
        else:
            # localHostList = ['http://127.0.0.1:8000/', 'http://localhost:8000', 'https://cmput4042ndnetwork.herokuapp.com/']
            if object.host in localHostList:
                print("following local users...", object.username)
                friendRequest = FriendFollowRequest.objects.create(
                    actor=actor,
                    object=object,
                    summary=f'{actorName} wants to follow {objectName}')
                friendRequest.save()
            else:
                friendRequest = FriendFollowRequest.objects.create(
                    actor=actor,
                    object=object,
                    summary=f'{actorName} wants to follow {objectName}')
                friendRequest.save()
                print(f'following remote author {object.username}')
                # if author is not local make post request to add to other user inbox
                serializer = serializers.FriendFollowRequestSerializer(
                    friendRequest)
                print(f"{object.host}/service/authors/{object.username}/inbox")
                print(json.dumps(serializer.data))

                ### from stack overflow https://stackoverflow.com/questions/20658572/python-requests-print-entire-http-request-raw
                # req = requests.Request('POST',f"{object.host}service/authors/{object.username}/inbox", data=json.dumps(serializer.data), auth=HTTPBasicAuth('proxy','proxy123!'), headers={'Content-Type': 'application/json'})
                if 'cmput4042ndnetwork' in object.host or object.host in localHostList:
                    authDictKey = object.host + "/service/"
                else:
                    authDictKey = object.host + "service/"
                req = requests.Request(
                    'POST',
                    f"{object.host}/service/authors/{object.username}/inbox",
                    data=json.dumps(serializer.data),
                    auth=HTTPBasicAuth(authDict[authDictKey][0],
                                       authDict[authDictKey][1]),
                    headers={'Content-Type': 'application/json'})
                prepared = req.prepare()

                s = requests.Session()
                resp = s.send(prepared)

                print("status code, ", resp.status_code)
        return redirect('myapp:profile', user_id=objectName)
    else:
        return redirect('/')
        #     payload['response'] = 'Friend request sent'
        # if payload['response'] == None:
        #     payload['response'] = 'Something went wrong'
    # return HttpResponse(json.dumps(payload), content_type='application/json')
    #     else:
    #
    #         return redirect('myapp:profile', user_id=object)


@login_required(login_url='/accounts/login')
def friendRequests(request):
    context = {}
    actorName = request.user.username
    actor = Author.objects.get(username=actorName)
    friendRequests = FriendFollowRequest.objects.filter(object=actor)
    context['friendRequests'] = friendRequests
    return render(request, 'friendRequests.html', context)


@login_required(login_url='/accounts/login')
def acceptFriendRequest(request, actor_id):
    objectName = request.user.username
    object = Author.objects.get(username=objectName)
    actor = Author.objects.get(username=actor_id)
    if request.method == 'GET':
        friendRequest_accept = FriendFollowRequest.objects.get(actor=actor,
                                                               object=object)
        if friendRequest_accept:
            if Followers.objects.filter(user=object):
                Followers.objects.get(user=object).items.add(actor)
            else:
                Followers.objects.create(user=object)
                Followers.objects.get(user=object).items.add(actor)
            return render(request, 'feed.html')


# @login_required(login_url='/accounts/login')
# def search(request):
#     # TODO: Move this up
#     import requests
#     author_list = Author.objects.all()
#     # get all authors from other nodes, append it
#     raise ValueError('u kdf')
#     for node in nodeArray:
#         # make get request to other notes /service/authors/
#         response = requests.get(f"{node}authors/", params=request.GET)
#         if response.status_code == 200:
#             print("SUCCESS")
#         else:
#             print("FAILURE")
#         print(response)
#         # create them into author objects
#         # append them in to list, return them
#     return render(request, 'feed.html', {'author_list':author_list})


@login_required(login_url='/accounts/login')
def getuser(request):
    username = request.GET['username']
    try:
        current_author_info = Author.objects.get(displayName=username)
    except:
        current_author_info = None
    if current_author_info == None:
        author_list = Author.objects.all()
        context = {
            'username': username,
            'author_list': author_list,
        }
        return render(request, 'profileNotFound.html', context)
    # current_author_info = get_object_or_404(Author, displayName = username)
    else:
        user_id = current_author_info.username
        return redirect('myapp:profile', user_id=user_id)


@method_decorator(login_required, name='dispatch')
class PostEditView(UpdateView):
    model = Post
    fields = ['title', 'content', 'contentType', 'visibility']
    template_name = 'postEdit.html'

    def get_success_url(self):
        pk = self.kwargs['pk']
        return reverse_lazy('myapp:postDetail', kwargs={'pk': pk})


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
        serializer = serializers.AuthorSerializer(
            Author.objects.filter(host="https://" + request.get_host()),
            many=True)
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
            author = model_to_dict(
                Author.objects.filter(username=follower.follower).first())
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
        followers = FollowerCount.objects.filter(
            user=usernames[1]).values_list('follower', flat=True)
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
            return Response({
                'following_relation_exist': 'True',
                'following_relation_put': 'False'
            })
        else:
            try:
                usernames = self.usernames()
                FollowerCount.objects.create(follower=usernames[0],
                                             user=usernames[1])
                return Response({
                    'following_relation_exist': 'False',
                    'following_relation_put': 'True'
                })
            except:
                return Response({
                    'following_relation_exist': 'False',
                    'following_relation_put': 'False'
                })

    def delete(self, request, *args, **kwargs):
        if self.relation_check():
            usernames = self.usernames()
            relation = FollowerCount.objects.filter(
                follower=usernames[0]).filter(user=usernames[1])
            try:
                relation.delete()
                return Response({
                    'following_relation_exist': 'True',
                    'following_relation_delete': 'True'
                })
            except:
                return Response({
                    'following_relation_exist': 'True',
                    'following_relation_delete': 'False'
                })
        else:
            return Response({
                'following_relation_exist': 'False',
                'following_relation_delete': 'False'
            })


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
            new_post = Post.objects.create(
                title=data["title"],
                uuid=post_id,
                description=data["description"],
                content=data["content"],
                contentType=data["contentType"],
                author=author,
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

            new_post.id = request.get_host() + "/authors/" + str(
                new_post.author.uuid) + "/posts/" + str(new_post.uuid)
            new_post.source = request.get_host() + "/post/" + str(
                new_post.uuid)
            new_post.origin = request.get_host() + "/post/" + str(
                new_post.uuid)
            new_post.comments = request.get_host() + "/post/" + str(
                new_post.uuid) + '/comments'
            new_post.save()
        except Exception as e:
            return HttpResponseNotFound(e)

        # TODO: lucas charles: verify this part doesnt need image post stuff like on
        # line 163 of this file.\

        # adding post to inbox of current author
        # add post to InboxItem which links to Inbox
        InboxItem.objects.create(
            inbox=Inbox.objects.filter(
                author__username=author.username).first(),
            inbox_item_type='post',
            item=new_post,
        )

        # adding post to inbox of all followers of current author
        followers = Followers.objects.filter(user=author.username)
        for follower in followers:
            InboxItem.objects.create(
                inbox=Inbox.objects.filter(
                    author__username=follower.username).first(),
                inbox_item_type='post',
                item=new_post,
            )
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
            new_post = Post.objects.create(
                title=data["title"],
                description=data["description"],
                content=data["content"],
                contentType=data["contentType"],
                author=author,
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
        new_post.id = request.get_host() + "/authors/" + str(
            new_post.author.uuid) + "/posts/" + str(new_post.uuid)
        new_post.source = request.get_host() + "/post/" + str(new_post.uuid)
        new_post.origin = request.get_host() + "/post/" + str(new_post.uuid)
        new_post.comments = request.get_host() + "/post/" + str(new_post.uuid)
        new_post.save()

        # to modify
        # Inbox.objects.filter(
        #     author__username=author.username)[0].items.add(new_post)
        # followersID = FollowerCount.objects.filter(user=author.username)
        # for followerID in followersID:
        #     Inbox.objects.filter(
        #         author__username=followerID.follower)[0].items.add(new_post)

        # adding post to inbox of current author
        # add post to InboxItem which links to Inbox
        InboxItem.objects.create(
            inbox=Inbox.objects.filter(
                author__username=author.username).first(),
            inbox_item_type='post',
            item=new_post,
        )

        # adding post to inbox of all followers of current author
        followers = Followers.objects.filter(user=author.username)
        for follower in followers:
            InboxItem.objects.create(
                inbox=Inbox.objects.filter(
                    author__username=follower.username).first(),
                inbox_item_type='post',
                item=new_post,
            )

        serializer = serializers.PostSerializer(new_post)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        posts = Post.objects.filter(author__username=author.username,
                                    visibility="PUBLIC")
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
        serializer = serializers.CommentsSerializer(
            Comment.objects.filter(post=post_id), many=True)
        return Response({"type": "comments", "items": serializer.data})

    def post(self, request, *args, **kwargs):
        current_user_uuid = self.kwargs['author']
        current_user = Author.objects.filter(uuid=current_user_uuid).first()
        post_id = self.kwargs['post']
        post = Post.objects.filter(uuid=post_id).first()
        if current_user is None or post is None:
            return HttpResponseNotFound("author or post not exist")

        data = request.data
        new_comment = Comment.objects.create(author=current_user,
                                             comment=data["comment"],
                                             contentType=data["contentType"],
                                             post=post)
        new_comment.save()
        new_comment.id = request.get_host() + "/authors/" + str(
            post.author.uuid) + "/posts/" + str(
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
    lookup_fields = ('author', )

    def list(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        like = Like.objects.filter(object__visibility="PUBLIC",
                                   author=author.username)
        serializer = serializers.LikesSerializer(like, many=True)
        return Response({"type": "liked", "items": serializer.data})


class InboxAPIView(CreateModelMixin, RetrieveDestroyAPIView):
    """ GET inbox POST post/follow/like DELETE inbox_obj"""
    serializer_class = serializers.InboxSerializer
    pagination_class = CustomPageNumberPagination
    lookup_fields = ('author', )

    def get_object(self):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        return Inbox.objects.filter(author__username=author.username).first()

    def post(self, request, *args, **kwargs):
        # check if user in url exists
        uuid = self.kwargs['author']
        current_user = Author.objects.filter(uuid=uuid).first()
        if current_user is None:
            return HttpResponseNotFound("author (in url) not exist")
        data = request.data

        # try:
        # 1. publish a post
        # don't care if these two have a friend relation, just push the post into its follower's inbox
        if data["type"] == "post":
            # check if user in the body (who post the post) exists
            author = Author.objects.filter(id=data["author"]["id"]).first()
            if author is None:
                return HttpResponseNotFound("author (in body) not exist")

            new_post = Post.objects.create(
                title=data["title"],
                description=data["description"],
                content=data["content"],
                contentType=data["contentType"],
                author=author,
                unparsedCategories=data["categories"],
                visibility=data["visibility"],
                image_b64=data["image_b64"])
            unparsed_cat = new_post.unparsedCategories
            for cat in unparsed_cat:
                new_cat = Category()
                new_cat.cat = cat
                new_cat.save()
                new_post.categories.add(new_cat)
                new_post.save()

            try:
                new_post.save()
            except Exception as e:
                return HttpResponseNotFound(e)
            new_post.id = request.get_host() + "/authors/" + str(
                new_post.author.uuid) + "/posts/" + str(new_post.uuid)
            new_post.source = request.get_host() + "/post/" + str(
                new_post.uuid)
            new_post.origin = request.get_host() + "/post/" + str(
                new_post.uuid)
            new_post.comments = request.get_host() + "/post/" + str(
                new_post.uuid)
            new_post.save()
            Inbox.objects.filter(
                author__username=current_user.username)[0].items.add(new_post)

            serializer = serializers.PostSerializer(new_post)
            return Response(serializer.data)

        elif data["type"].lower() == "follow":
            remote_author = Author.objects.filter(
                id=data['actor']['id']).first()
            our_author = Author.objects.filter(
                username=data['object']['displayName']).first()
            friend_request = FriendFollowRequest.objects.create(
                summary=data["summary"],
                actor=remote_author,
                object=our_author)
            friend_request.save()

            serializer = serializers.FriendFollowRequestSerializer(
                friend_request)
            return Response(serializer.data)

        elif data["type"] == "like":
            # check if post in the body (the post that user gives a like) exists
            post = Post.objects.filter(uuid=data["object"]).first()
            if post is None:
                return HttpResponseNotFound("post not exist")
            like_before = Like.objects.filter(author=current_user,
                                              object=post).first()
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

        # except Exception as e:
        #     return HttpResponseNotFound(e)

    def delete(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        author = Author.objects.filter(uuid=author_uuid).first()
        inbox = Inbox.objects.filter(author=author.username).first()
        inbox.delete()
        new_inbox = Inbox.objects.create(author=author)
        new_inbox.save()

        serializer = serializers.InboxSerializer(new_inbox)
        return Response(serializer.data)
