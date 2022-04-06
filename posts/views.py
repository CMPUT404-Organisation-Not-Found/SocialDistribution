import base64
import json
from pkg_resources import split_sections

import requests
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, JsonResponse, HttpResponse
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
from django.template.loader import render_to_string
from common.views import localHostList

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
        # form content is not None or image is not None
        if form.is_valid() and (form['content'].value() != "" or form['post_image'].value() is not None):
            # creating post from form and adding attributes
            newPost = form.save(commit=False)
            newPost.author = Author.objects.get(username=request.user.username)
            newPost.id = f"{request.build_absolute_uri('/')}authors/{str(newPost.author.uuid)}/posts/{str(newPost.uuid)}"

            # deal with unlisted post
            if newPost.unlisted:
                newPost.url = newPost.author.host + "post/unlisted/" + str(newPost.uuid)
            else:
                newPost.url = newPost.author.host + "post/" + str(newPost.uuid)

            unparsedCat = newPost.unparsedCategories
            catList = unparsedCat.split()
            newPost.save()
            for cat in catList:
                newCat = Category()
                newCat.cat = cat
                newCat.save()
                newPost.categories.add(newCat)
                newPost.save()

            newPost.source = newPost.id
            newPost.origin = newPost.id
            newPost.comments = newPost.id + '/comments'
            newPost.save()

            # if it has an image, then create an unlisted image post
            if newPost.post_image:
                # print("------url", newPost.post_image.path)
                # print(str(newPost.post_image))
                img_file = open(newPost.post_image.path, "rb")
                # newPost.image_b64 = base64.b64encode(img_file.read())
                # create an embedded image post
                newImagePost = Post(
                    author=newPost.author,
                    unlisted=True,
                    source=newPost.source,
                    origin=newPost.origin,
                    visibility="PUBLIC",
                    post_image=newPost.post_image,
                    # image_b64=base64.b64encode(img_file.read())
                )
                # newImagePost.save(commit=False)
                if "jpeg" in newPost.post_image.name:
                    newImagePost.contentType = "image/jpeg;base64"
                elif "png" in newPost.post_image.name:
                    newImagePost.contentType = "image/png;base64"
                else:
                    newImagePost.contentType = "application/base64"
                newImagePost.url = newPost.author.host + "post/unlisted/" + str(newImagePost.uuid)
                newImagePost.id = f"{newPost.author.host}authors/{str(newPost.author.uuid)}/posts/{str(newImagePost.uuid)}"
                newImagePost.image_b64 = base64.b64encode(img_file.read())
                # print(newPost.image_b64[:20])
                newImagePost.save()
                newPost.contentType = "text/markdown"
                newPost.content += "\n[View image here](" + newImagePost.url + ")"
                newPost.post_image = None
                newPost.save()
            else:
                # Set text post to plain/markdown
                newPost.contentType = "text/plain"
                if newPost.textType != None:
                    newPost.contentType = newPost.textType


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
                                    author__username=follower.username).first(),
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
        post = Post.objects.get(id__contains=f'posts/{pk}')
        post_uuid = post.id.split('/')[-1]
        form = CommentForm()
        # if post is a friend post and current user is not the author of the post, then only show comments of current user
        if post.visibility == 'FRIENDS' and post.author.username != request.user.username:
            comments = Comment.objects.filter(id__contains=f'posts/{pk}').order_by('-published')
            for comment in comments:
                if comment.author.username != request.user.username:
                    comments = comments.exclude(
                        author__username=comment.author.username)
            # sort comments by published date
            comments = comments.order_by('-published')
        # else, show all comments
        else:
            comments = Comment.objects.filter(id__contains=f'posts/{pk}').order_by('-published')
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
        post = Post.objects.get(id__contains=f'posts/{pk}')
        form = CommentForm(request.POST)
        author_list = Author.objects.all()
        if form.is_valid():
            newComment = form.save(commit=False)
            newComment.author = Author.objects.get(
                username=request.user.username)
            newComment.comment = form['comment'].value()
            newComment.contentType = form['contentType'].value()
            newComment.id = post.id + "/comments/" + str(
                    newComment.uuid)
            newComment.post = post

            # url
            comment_author = newComment.author.id.split('/')[-1]
            post_author = newComment.post.author.id.split('/')[-1]
            comment_node = ConnectionNode.objects.filter(url__contains=newComment.author.host).first()
            post_node = ConnectionNode.objects.filter(url__contains=newComment.post.author.host).first()

            # For testing purpose, if connectionNode is empty
            if post_node is not None:
                comment_json = json.dumps(serializers.CommentsSerializer(newComment).data)

                if newComment.post.author.host not in localHostList:
                    newComment.save()

                # push to post authors inbox
                post_author_req = requests.Request(
                    'POST',
                    f"{post_node.url}authors/{post_author}/inbox",
                    data=comment_json,
                    auth=HTTPBasicAuth(post_node.auth_username, post_node.auth_password),
                    headers={'Content-Type': 'application/json'},
                )

                post_prep = post_author_req.prepare()
                post_session = requests.Session()
                post_resp = post_session.send(post_prep)

                if post_resp.status_code >= 400:
                    print('Error has occured while sending things')

            form = CommentForm()

        comments = Comment.objects.filter(id__contains=f'posts/{pk}').order_by('-published')
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


class UnlistedPostDetailView(View):

    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.filter(uuid=pk).first()
        img_file = open(post.post_image.path, "rb")
        # if post.image_b64 != None:
        #     image_b64 = post.image_b64.decode('utf-8')
        # else:
        #     image_b64 = None
        image_b64 = base64.b64encode(img_file.read()).decode('utf-8')
        context = {
            'post': post,
            'image_b64': image_b64,
        }
        rendered = render_to_string('unlistedPostDetail.html', context)
        return HttpResponse(rendered)


@method_decorator(login_required, name='dispatch')
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
            return render(request, 'personNotFound.html', context)

        try:
            post = Post.objects.filter(author__username=request.user.username).order_by('-published').first()
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
                        return render(request, 'personNotFound.html', context)
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
                    else:
                        hisfollowers = []
                except:
                    hisfollowers = []

                if hisfollowers == []:
                    context = {
                        'username': username,
                    }
                    return render(request, 'notFriend.html', context)
                else:
                    found = False
                    for follower in hisfollowers:
                        if user.id in follower.values():
                            # You are TRUE friends
                            found = True
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
                                        author__username=request.user.username).first(),
                                    inbox_item_type="post",
                                    item=post,
                                )
                            except:
                                context = {
                                    'username':username,
                                }
                                return render(request, 'authors/profileNotFound.html', context)
                    if not found:
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


# class UnlistedPostDetailView(View):
#
#     def get(self, request, pk, *args, **kwargs):
#         post = Post.objects.filter(uuid=pk).first()
#         if post.image_b64 != None:
#             image_b64 = post.image_b64.decode('utf-8')
#         else:
#             image_b64 = None
#         context = {
#             'post': post,
#             'image_b64': image_b64,
#         }
#         rendered = render_to_string('unlistedPostDetail.html', context)
#         return HttpResponse(rendered)


@method_decorator(login_required, name='dispatch')
class SharedPostView(View):
    """
        View for sharing posted posts (or something like that)
    """

    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.get(id__contains=f'posts/{pk}')
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
        source_post = Post.objects.get(id__contains=f'posts/{pk}')
        source_post_id = source_post.id.split('/')[-1]
        original_post_id = source_post.origin.split('/')[-1]
        original_post = Post.objects.get(id__contains=f'posts/{original_post_id}')
        form = ShareForm(request.POST)

        if form.is_valid():
            new_post = Post(
                type='post',
                title=self.request.POST.get('title'),
                origin=original_post.origin,
                description=original_post.description,
                content=original_post.content,
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
        commenter = Author.objects.filter(username=request.user.username).first()
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

            new_like = Like(author=commenter, object=object_id, summary=summary)
            if host not in localHostList:
                if "comments" not in object_id:
                    post = Post.objects.filter(id__contains=f'/posts/{object_uuid}').first()
                    post.likes += 1
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
        post = Post.objects.get(id__contains=f'posts/{pk}')

        form = CommentForm()
        comments = Comment.objects.filter(id__contains=f'posts/{pk}').order_by('-published')
        likes = Like.objects.filter(object=post)

        source_post_id = post.source.split('/')[-1]
        source_post = Post.objects.filter(id__contains=f'posts/{source_post_id}').first()
        original_post_id = post.origin.split('/')[-1]
        original_post = Post.objects.filter(id__contains=f'posts/{original_post_id}').first()
        if source_post == None:
            source_deleted = True
        else:
            source_deleted = False
        if original_post == None:
            original_deleted = True
        else:
            original_deleted = False

        context = {
            'post': post,
            'form': form,
            'comments': comments,
            'likes': likes,
            'source_post': source_post,
            'original_post': original_post,
            'source_deleted': source_deleted,
            'original_deleted': original_deleted,
        }

        return render(request, 'shareDetail.html', context)

    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(id__contains=f'posts/{pk}')
        form = CommentForm(request.POST)

        if form.is_valid():
            newComment = form.save(commit=False)
            newComment.author = Author.objects.get(
                username=request.user.username)
            newComment.post = post
            newComment.save()
            post.count += 1
            post.save()

        comments = Comment.objects.filter(id__contains=f'posts/{pk}').order_by('-published')
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
    post = Post.objects.get(id__contains=f'posts/{post_id}')
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
    fields = ['title','content','contentType']
    template_name = 'postEdit.html'

    def get_success_url(self):
        pk = self.kwargs['pk']
        return reverse_lazy('posts:postDetail', kwargs={'pk': pk})


@method_decorator(login_required, name='dispatch')
class PostDeleteView(DeleteView):
    model = Post
    template_name = 'postDelete.html'
    success_url = reverse_lazy('inboxes:postList')

    def delete(self, request, *args, **kwargs):
        listed_post_id = self.kwargs['pk']
        listed_post = Post.objects.get(uuid=listed_post_id)
        # if this post contains an image
        if "[View image here]" in listed_post.content and str(listed_post.uuid) in listed_post.origin:
            unlisted_url = listed_post.content.split('[View image here]')[1].strip("()")
            unlisted_post_id = unlisted_url.split('/')[-1]
            unlisted_post = Post.objects.get(uuid=unlisted_post_id)
            unlisted_post.delete()
        # listed_post.delete()
        return super(PostDeleteView, self).delete(request, *args, **kwargs)



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
        author = Author.objects.filter(id__contains=author_uuid).first()
        post_id = self.kwargs['pk']
        return Post.objects.filter(id__contains=f'posts/{post_id}', author=author.username)

    def post(self, request, *args, **kwargs):
        author_uuid = self.kwargs['author']
        post_id = self.kwargs['pk']
        author = Author.objects.filter(id__contains=author_uuid).first()
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
        author = Author.objects.filter(id__contains=author_uuid).first()
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
        author = Author.objects.filter(id__contains=author_uuid).first()
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
        author = Author.objects.filter(id__contains=author_uuid).first()
        post_id = self.kwargs['pk']
        return Post.objects.filter(id__contains=f'posts/{post_id}', author=author.username)


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
        current_user = Author.objects.filter(id__contains=current_user_uuid).first()
        pk = self.kwargs['post']
        post = Post.objects.filter(id__contains=f'posts/{pk}').first()
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
        author = Author.objects.filter(id_contains=author_uuid).first()
        like = Like.objects.filter(object__visibility="PUBLIC",
                                   author=author.username)
        serializer = serializers.LikesSerializer(like, many=True)
        return Response({"type": "liked", "items": serializer.data})
