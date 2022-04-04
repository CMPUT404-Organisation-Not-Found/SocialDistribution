import base64
import json
from pkg_resources import split_sections

import requests
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, JsonResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import UpdateView, DeleteView
from requests.auth import HTTPBasicAuth
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, \
    RetrieveAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response

from authors.models import Author, Followers, FollowerCount
from common.models import ConnectionNode
from common.pagination import CustomPageNumberPagination
from inboxes.models import Inbox, InboxItem
from . import serializers, renderers
from .forms import PostForm, CommentForm, ShareForm
from .models import Post, Comment, Category, Like

localHostList = [
    'http://127.0.0.1:7070/', 'http://127.0.0.1:8000/',
    'http://localhost:8000', 'http://localhost:8000/',
    'https://c404-social-distribution.herokuapp.com/'
]

connectionNodes = ConnectionNode.objects.all()


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
            newPost.id = f"{request.build_absolute_uri('/')}authors/{str(newPost.author.uuid)}/posts/{str(newPost.uuid)}"
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
                newPost.source = newPost.id
                newPost.origin = newPost.id
                newPost.comments = newPost.id + '/comments'
                newPost.save()

            # if its an image
            if newPost.post_image:
                # print("------url", newPost.post_image.path)
                # print(str(newPost.post_image))
                img_file = open(newPost.post_image.path, "rb")
                newPost.image_b64 = base64.b64encode(img_file.read())
                # print(newPost.image_b64[:20])
                newPost.save()

            if newPost.visibility == 'PRIVATE':
                # context = {
                #     'newPost': newPost,
                # }
                return redirect('posts:selectPerson')
            else:
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
                        # if follower is local
                        if follower.host in localHostList:
                            # add it to inbox of follower
                            InboxItem.objects.create(
                                inbox=Inbox.objects.filter(
                                    author__username=follower.username).first(
                                    ),
                                inbox_item_type="post",
                                item=newPost,
                            )
                        else:
                            # if author is not local make post request to add to other user inbox
                            serializer = serializers.PostSerializer(newPost)
                            # get follower node object
                            followerNode = connectionNodes.filter(
                                url=f"{follower.host}service/").first()
                            req = requests.Request(
                                'POST',
                                f"{followerNode.url}authors/{follower.username}/inbox",
                                data=json.dumps(serializer.data),
                                auth=HTTPBasicAuth(followerNode.auth_username,
                                                   followerNode.auth_password),
                                headers={'Content-Type': 'application/json'})

                            prepared = req.prepare()
                            s = requests.Session()
                            resp = s.send(prepared)

                            print("status code, ", resp.status_code)

                except AttributeError as e:
                    print(e, 'No followers for this author')

        return redirect('inboxes:postList')


@method_decorator(login_required, name='dispatch')
class PostDetailView(View):

    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.get(uuid=pk)
        post_uuid = post.id.split('/')[-1]
        form = CommentForm()
        # if post is a friend post and current user is not the author of the post, then only show comments of current user
        if post.visibility == 'FRIENDS' and post.author.username != request.user.username:
            comments = Comment.objects.filter(post=post).order_by('-published')
            for comment in comments:
                if comment.author.username != request.user.username:
                    comments = comments.exclude(
                        author__username=comment.author.username)
            # sort comments by published date
            comments = comments.order_by('-published')
        # else, show all comments
        else:
            # get all related local comments, and convert them to json
            comments = Comment.objects.filter(
                id__contains=post_uuid).order_by('-published')
            import ast
            comments_json = [
                ast.literal_eval(
                    json.dumps(serializers.CommentsSerializer(comment).data))
                for comment in comments
            ]
            # for comment in comments:
            #     comments_json.append(
            #         json.dumps(serializers.CommentsSerializer(comment).data))
            comments = comments_json
            # get all related remote comments
            remote_comment_pagination = 0
            while True:
                split_comment_url = post.comments.split('/')
                split_comment_url.insert(split_comment_url.index('authors'),
                                         'service')
                comment_url = '/'.join(split_comment_url)

                post_host = post.id.split('/')[2]
                post_node = connectionNodes.filter(
                    url__contains=post_host).first()

                try:
                    response = requests.get(
                        f'{comment_url}?page={remote_comment_pagination}',
                        params=request.GET,
                        auth=HTTPBasicAuth(post_node.auth_username,
                                           post_node.auth_password))
                    # check dictionary key since its kinda fked
                    if 'comments' in response.json():
                        key = 'comments'
                    elif 'items' in response.json():
                        key = 'items'
                    else:
                        raise Exception('Invalid Keys in Response')
                        break
                    if response.ok and len(response.json()[key]) > 0:
                        print(len(response.json()[key]))
                        remote_comment_pagination += 1
                        remote_comments = response.json()[key]

                        # check if already added in remote_comments list, if so that means
                        # the server does not support pagination, hence the same results
                        comment_duplication = False
                        for comment in remote_comments:
                            if comment in comments:
                                comment_duplication = True
                            else:
                                comments.append(comment)

                        if comment_duplication:
                            break
                    else:
                        # either post request is bad or no more comments
                        if response.ok:
                            print(
                                f'No more remote comments for post "{post.__str__()}"'
                            )
                        else:
                            print(f'Bad request for post "{post.__str__()}"')
                        break
                except Exception as e:
                    print(
                        f'Error while getting comments for post "{post.__str__()}": {e}'
                    )
                    break

            # order list of dict by published date
            comments = sorted(comments, key=lambda k: k['published'])

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
            print(newComment.uuid)
            newComment.author = Author.objects.get(
                username=request.user.username)
            newComment.comment = form['comment'].value()
            newComment.contentType = form['contentType'].value()
            newComment.id = request.get_host() + "/authors/" + str(
                post.author.uuid) + "/posts/" + str(pk) + "/comments/" + str(
                    newComment.uuid)
            newComment.post = post

            # url
            comment_author = newComment.author.id.split('/')[-1]
            post_author = newComment.post.author.id.split('/')[-1]
            comment_node = ConnectionNode.objects.filter(
                url__contains=newComment.author.host).first()
            post_node = ConnectionNode.objects.filter(
                url__contains=newComment.post.author.host).first()

            #comment json for commenter
            comment_json = json.dumps(
                serializers.CommentsSerializer(newComment).data)

            # # push to commenters inbox
            # comment_author_req = requests.Request(
            #     'POST',
            #     f"{comment_node.url}authors/{comment_author}/inbox",
            #     auth=HTTPBasicAuth(comment_node.auth_username, comment_node.auth_password),
            #     headers={'Content-Type': 'application/json'},
            #     data=comment_json,
            # )
            # comment_prepare = comment_author_req.prepare()
            # comment_s = requests.Session()
            # comment_resp= comment_s.send(comment_prepare)

            # if comment_resp.status_code >= 400:
            #         print('Error has occured while sending things')

            # push to post authors inbox
            post_author_req = requests.Request(
                'POST',
                f"{post_node.url}authors/{post_author}/inbox",
                data=comment_json,
                auth=HTTPBasicAuth(post_node.auth_username,
                                   post_node.auth_password),
                headers={'Content-Type': 'application/json'},
            )

            post_prep = post_author_req.prepare()
            post_session = requests.Session()
            post_resp = post_session.send(post_prep)

            if post_resp.status_code >= 400:
                print('Error has occured while sending things')

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
# def selectPerson(request):
#     author_list = Author.objects.all()
#     context = {
#             'author_list':author_list,
#         }
#     return render(request, 'selectPerson.html', context)
class selectPersonView(View):

    def get(self, request, *args, **kwargs):
        form = PostForm()
        share_form = ShareForm()
        author_list = Author.objects.all()
        context = {
            'form': form,
            'author_list': author_list,
            # 'source_post': source_post,
            # 'original_post': original_post,
        }
        return render(request, 'selectPerson.html', context)

    def post(self, request, *args, **kwargs):
        # form = PostForm(request.POST, request.FILES)
        # author_list = Author.objects.all()
        username = request.POST.get('specificUserName', '')
        # print(username)
        try:
            selected_author = Author.objects.get(displayName=username)
        except:
            context = {
                'username': username,
            }
            return render(request, 'authors/profileNotFound.html', context)

        try:
            post = Post.objects.filter(author__username=request.user.username
                                       ).order_by('-published').first()
            # print(Post.objects.filter(author__username=request.user.username))
            # print(post)
        except:
            post = []

        # check if they are true friend.
        user = Author.objects.get(username=request.user.username)
        try:
            myfollowers = Followers.objects.filter(
                user__username=user.username).first().items.all()
        except:
            myfollowers = []
        if selected_author in myfollowers:
            # if the host is local
            if selected_author.host in localHostList:
                try:
                    hisfollowers = Followers.objects.filter(
                        user__username=selected_author.username).first(
                        ).items.all()
                except:
                    hisfollowers = []
                if user in hisfollowers:
                    # in this case you are true friends
                    try:
                        # Inbox.objects.filter(author__username=selected_author_info.username).first().items.add(post)
                        # add the new post to my own inbox
                        InboxItem.objects.create(
                            inbox=Inbox.objects.filter(
                                author__username=selected_author.username).
                            first(),
                            inbox_item_type="post",
                            item=post,
                        )
                        try:
                            InboxItem.objects.create(
                                inbox=Inbox.objects.filter(
                                    author__username=request.user.username).
                                first(),
                                inbox_item_type="post",
                                item=post,
                            )
                        except AttributeError as e:
                            print(
                                e,
                                'Cannot add to my 1to1. Something went wrong!')
                    except:
                        context = {
                            'username': username,
                        }
                        return render(request, 'authors/profileNotFound.html',
                                      context)
                else:
                    context = {
                        'username': username,
                    }
                    return render(request, 'notFriend.html', context)
            else:
                # if author is not local
                # get follower node object
                try:
                    followerNode = connectionNodes.filter(
                        url=f"{selected_author.host}service/").first()
                    response = requests.get(
                        f"{followerNode.url}authors/{selected_author.username}/followers",
                        params=request.GET,
                        auth=HTTPBasicAuth(followerNode.auth_username,
                                           followerNode.auth_password))
                    if response.status_code == 200:
                        hisfollowers = response.json()['items']
                        print(hisfollowers)
                    else:
                        hisfollowers = []
                except:
                    hisfollowers = []
                for follower in hisfollowers:
                    if user.id in follower.values():
                        # You are TRUE friends
                        try:
                            serializer = serializers.PostSerializer(post)
                            # get follower node object
                            followerNode = connectionNodes.filter(
                                url=f"{selected_author.host}service/").first()
                            req = requests.Request(
                                'POST',
                                f"{followerNode.url}authors/{selected_author.username}/inbox",
                                data=json.dumps(serializer.data),
                                auth=HTTPBasicAuth(followerNode.auth_username,
                                                   followerNode.auth_password),
                                headers={'Content-Type': 'application/json'})

                            prepared = req.prepare()

                            s = requests.Session()
                            resp = s.send(prepared)

                            print("status code, ", resp.status_code)
                            # ADD to my own 1 to 1
                            InboxItem.objects.create(
                                inbox=Inbox.objects.filter(
                                    author__username=request.user.username).
                                first(),
                                inbox_item_type="post",
                                item=post,
                            )
                        except:
                            context = {
                                'username': username,
                            }
                            return render(request,
                                          'authors/profileNotFound.html',
                                          context)
                    else:
                        context = {
                            'username': username,
                        }
                        return render(request, 'notFriend.html', context)
        else:
            context = {
                'username': username,
            }
            return render(request, 'notFriend.html', context)

        # add the new post to my own inbox
        # Inbox.objects.filter(author__username=request.user.username).first().items.add(post)
        # posts = Post.objects.all()
        # context = {
        #     'postList': posts,
        #     # 'form': form,
        # }
        # return render(request,'myapp/newpost.html', context)
        return redirect('inboxes:postList')


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
        source_post_id = source_post.id.split('/')[-1]
        original_post_id = source_post.origin.split('/')[-1]
        original_post = Post.objects.get(uuid=original_post_id)
        form = ShareForm(request.POST)

        if form.is_valid():
            new_post = Post(
                #TODO: Su: please confirm that type is allowed to be updated
                # eg if author.user is not the same as the user who is sharing the post
                type='post',
                title=self.request.POST.get('title'),
                origin=original_post.origin,
                description=Post.objects.get(pk=pk).description,
                content=Post.objects.get(pk=pk).content,
                contentType=original_post.contentType,
                author=Author.objects.get(username=request.user.username),
                visibility=original_post.visibility,
            )
            new_post.source = f"{request.build_absolute_uri('/')}authors/{str(new_post.author.uuid)}/posts/{str(source_post_id)}"
            new_post.save()
            new_post.id = f"{request.build_absolute_uri('/')}authors/{str(new_post.author.uuid)}/posts/{str(new_post.uuid)}"
            new_post.save()
            new_post.comments = new_post.id + '/comments'
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
        except Exception as e:
            print(e, 'No followers for this author')

        # followersID = F ollowerCount.objects.filter(user=request.user.username)
        for follower in followers:
            try:
                # TODO: darren make this work for remote authors too (just call API or something lol)
                # follower is <author> object
                serializer = serializers.PostSerializer(new_post)
                # get follower node object
                followerNode = connectionNodes.filter(
                    url=f"{follower.host}service/").first()

                # since API uses UUID, it is different for local
                if follower.host in localHostList:
                    post_destination_url = f"{followerNode.url}authors/{follower.uuid}/inbox"
                else:
                    post_destination_url = f"{followerNode.url}authors/{follower.username}/inbox"

                req = requests.Request(
                    'POST',
                    post_destination_url,
                    data=json.dumps(serializer.data),
                    auth=HTTPBasicAuth(followerNode.auth_username,
                                       followerNode.auth_password),
                    headers={'Content-Type': 'application/json'})

                prepared = req.prepare()
                s = requests.Session()
                resp = s.send(prepared)
                print("status code, ", resp.status_code)

                if resp.ok:
                    print(
                        f"Successfully send shared post to {followerNode.url}authors/{follower.username}/inbox"
                    )
                else:
                    print(
                        f"Failed to send shared post to {followerNode.url}authors/{follower.username}/inbox"
                    )
            except Exception as e:
                print(e, 'Failed to send shared post to follower')

        context = {
            'new_post': new_post,
            # 'source_post': source_post,
            # 'original_post': original_post,
            'form': form,
        }
        return redirect('inboxes:postList')


@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class LikeHandlerView(View):

    def post(self, request):
        commenter = Author.objects.filter(
            username=request.user.username).first()
        author_id = request.POST['author_id']
        author_uuid = author_id.split('/')[-1]
        author = Author.objects.get(id=author_id)
        object_id = request.POST['object_id']
        object_uuid = object_id.split('/')[-1]
        host = request.POST['author_host']
        node = ConnectionNode.objects.filter(url__contains=host).first()

        if "comments" in object_id:
            summary = commenter.displayName + ' likes your comment'
            post_uuid = object_id.split('/')[-3]
            req = requests.Request(
                'GET',
                f"{node.url}authors/{author_uuid}/posts/{post_uuid}/comments/{object_uuid}/likes",
                auth=HTTPBasicAuth(node.auth_username, node.auth_password),
            )
        else:
            summary = commenter.displayName + ' likes your post'
            req = requests.Request(
                'GET',
                f"{node.url}authors/{author_uuid}/posts/{object_uuid}/likes",
                auth=HTTPBasicAuth(node.auth_username, node.auth_password),
            )

        prepared = req.prepare()
        s = requests.Session()
        resp = s.send(prepared)
        if resp.status_code >= 400:
            return JsonResponse({"liked": "fail"})
        content = resp.json()
        author_lst = []
        for i in content['items']:
            author_lst.append(i['author']['id'])

        if commenter.id in author_lst:
            return JsonResponse({"liked": "before"})
        else:
            # send the like object into the inbox, local or foreign, whatever, I am using API!

            new_like = Like(author=commenter,
                            object=object_id,
                            summary=summary)
            if host not in localHostList:
                new_like.save()
            serializer = serializers.LikesSerializer(new_like)
            req = requests.Request(
                'POST',
                f"{node.url}authors/{author_uuid}/inbox",
                data=json.dumps(serializer.data),
                auth=HTTPBasicAuth(node.auth_username, node.auth_password),
                headers={'Content-Type': 'application/json'})
            prepared = req.prepare()
            s = requests.Session()
            resp = s.send(prepared)

            if resp.status_code == 200 or resp.status_code == 201:
                return JsonResponse({"liked": "success"})
            else:
                return JsonResponse({"liked": "fail"})


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

    # getting local likes
    likes_list = list(Like.objects.filter(object=post))

    # getting remote likes
    node = ConnectionNode.objects.filter(
        url__contains=request.get_host()).first()
    url = f"{node.url}authors/{username}/posts/{post_id}/likes"
    response = requests.get(url,
                            params=request.GET,
                            auth=HTTPBasicAuth(node.auth_username,
                                               node.auth_password))

    if response.ok:
        response_json = response.json()
        #check what kind of format the likes are in
        if 'items' in response_json:
            key = 'items'
        elif 'likes' in response_json:
            key = 'likes'
        else:
            raise Exception(
                'Invalid response key. Required "items" or "likes"')
        # append likes to likes_list
        # likes_list.append(response_json[key])
        for like in response_json[key]:
            likes_list.append(like)
    else:
        print(f"error while getting remote likes at {url}")

    # breakpoint()
    print(likes_list)
    context = {'likes_list': likes_list}
    return render(request, 'liked.html', context)


@method_decorator(login_required, name='dispatch')
class PostEditView(UpdateView):
    model = Post
    fields = ['title', 'description', 'contentType', 'categories']
    template_name = 'postEdit.html'

    def get_success_url(self):
        pk = self.kwargs['pk']
        return reverse_lazy('posts:postDetail', kwargs={'pk': pk})


@method_decorator(login_required, name='dispatch')
class PostDeleteView(DeleteView):
    model = Post
    template_name = 'postDelete.html'
    success_url = reverse_lazy('inboxes:postList')


#
# API
#


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
            Comment.objects.filter(id__contains=post_id), many=True)
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


class PostLikesAPIView(ListAPIView):
    serializer_class = serializers.LikesSerializer
    pagination_class = CustomPageNumberPagination
    # renderer_classes = (renderers.LikesRenderer,)
    lookup_fields = ('object', )

    def get_queryset(self):
        object_id = self.kwargs['post']
        # this is a post
        likes = Like.objects.filter(object__contains=object_id)
        likes = likes.exclude(object__contains="comments")
        return likes


class CommentLikesAPIView(ListAPIView):
    serializer_class = serializers.LikesSerializer
    pagination_class = CustomPageNumberPagination
    # renderer_classes = (renderers.LikesRenderer,)
    lookup_fields = ('object', )

    def get_queryset(self):
        post_id = self.kwargs['post']
        comment_id = self.kwargs['comment']
        # this is a post
        likes = Like.objects.filter(object__contains=post_id)
        likes = likes.filter(object__contains="comments")
        likes = likes.filter(object__contains=comment_id)
        return likes


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
