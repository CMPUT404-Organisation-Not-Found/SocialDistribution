# API Documentation



The remote API won't be available for FriendRequest, send a like object (POST), and get likes of a comment (POST).

You can now access the entire API (local or remote) with an HTTP Basic Auth credential, this will fix later.  





## Authors 



```
URL:://service/authors
```



### GET (remote)

retrieve all authors on the node, it supports pagination

*Example:* `GET ://service/authors/` will retrieve 5 authors on page 10.

*Example:* `GET ://service/authors?page=10&size=5` will retrieve 5 authors on page 10.



## Author



```
URL:://service/authors/{author_id}
```



### GET (remote)

retrieve one author's profile.

*Example:* `GET ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4` will retreieve johnny's profile.



### PUT

update one author's profile.

*Example:* `POST ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4` will update johnny's profile.

```json
(body) 
{
    "type": "author",
    "id": "127.0.0.1:8000/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4",		
    "username": "johnny",														
    "host": "127.0.0.1:8000",
    "displayName": "someone",
    "github": "https://github.com/someone",
    "profileImage": "https://an_image.url"
}
```



## Followers



```
URL:://service/authors/{author_id}/followers
```



### GET (remote)

retreive a list of authors that are `author_id`'s followers.

*Example:* `GET ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4/followers` will retreieve johnny's followers.





```
URL:://service/authors/{author_id}/followers/{another_author_id}
```



### GET (remote)

check if `another_author_id` is `author_id`'s follower. 

Returns:

​	Will return `{'following_relation_exist': 'True'}` if  `another_author_id` is `author_id`'s follower;

​	Will return `{'following_relation_exist': 'False'}` if  `another_author_id` is not `author_id`'s follower. 

*Example:* `GET ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4/followers/44603e25-39c7-4343-b779-baf9e137c155/` will check if wong is one of jonny's followers.



### PUT

add `another_author_id` as `author_id`'s follower.

Returns:

​	Will return `{'following_relation_exist': 'True', 'following_relation_put': 'False'}` if `another_author_id` is already `author_id`'s follower;

​	Will return `{'following_relation_exist': 'False', 'following_relation_put': 'True'}` if `another_author_id` is not `author_id`'s follower, and the addition process succeed;

​	Will return `{'following_relation_exist': 'False', 'following_relation_put': 'True'}` if `another_author_id` is not `author_id`'s follower, and the addition process is not success.

*Example*:  `PUT ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4/followers/44603e25-39c7-4343-b779-baf9e137c155/` will try to add wong as johnny's follower.



### DELETE

remove `another_author_id` from `author_id`'s follower.

Returns:

​	Will return `{'following_relation_exist': 'True', 'following_relation_delete': 'True'}` if `another_author_id` is `author_id`'s follower and now the removing process succeed;

​	Will return `{'following_relation_exist': 'True', 'following_relation_delete': 'False'}` if `another_author_id` is `author_id`'s follower, and the removing process is not success;

​	Will return `{'following_relation_exist': 'False', 'following_relation_delete': 'False'}` if `another_author_id` is not `author_id`'s follower.

*Example*:  `DELETE ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4/followers/44603e25-39c7-4343-b779-baf9e137c155/` will try to remove wong from johnny's follower.



## Friend/Follow Request (N/A)



Not available in this submission



## Posts



```
URL::/service/authors/{author_id}/posts
```



### GET (remote)

retrieve all the posts published by `author_id`.

*Example:*  `GET ://service/authors/johnny/posts` will retrieve all johnny's post.



### POST

publish a new post by using `author_id`

*Example:* `POST ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4/posts` will publish a post using `author_id` as johnny, the field below are all mandatory

```json
(body)
{
    "title": "new post",
    "description": "this is a new post",
    "content": "whatever you wanna write",
    "contentType": "text/markdown", // choose from {text/markdown, text/plain, application/base64, 		
    								// image/png;base64, image/jpeg;base64}
    "categories": "post web_dev", 	// separate categories with space
    "visibility": "PUBLIC", 		// choose from {PUBLIC, FRIENDS, PRIVATE}
    "post_image": null, 			// or an base64 enocoded image
}
```



## Post



```
URL::/service/authors/{author_id}/posts/{post_id}/
```



### GET (remote)

retrieve public post published by `author_id` and that is `post_id`. 

*Example:* `GET ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4/posts/338ef917-789e-4db7-99e6-b00169fb9326/` will retrieve johnny's post with id as `338ef917-789e-4db7-99e6-b00169fb9326`.



### POST

publish a new post with `post_id` by using account `author_id`

*Example:* `POST ://service/authors/25e8f446-efc3-4f44-af8c-3af5c42993d4/posts/338ef917-789e-4db7-99e6-b00169fb9326/` will publish a new post, id as `338ef917-789e-4db7-99e6-b00169fb9326`, by using johnny's account.  The field below are all mandatory

```json
(body)
{
    "title": "new post",
    "description": "this is a new post",
    "content": "whatever you wanna write",
    "contentType": "text/markdown", // choose from {text/markdown, text/plain, application/base64, 		
    								// image/png;base64, image/jpeg;base64}
    "categories": "post web_dev", 	// separate categories with space
    "visibility": "PUBLIC", 		// choose from {PUBLIC, FRIENDS, PRIVATE}
    "post_image": null, 			// or an base64 enocoded image
}
```

<span style="color:grey">

### PUT (N/A)

update an existing post that id is `post_id` and published by `author_id`

*Example:* `PUT ://service/authors/johnny/posts/338ef917-789e-4db7-99e6-b00169fb9326/` will update an existing post, id as 338ef917-789e-4db7-99e6-b00169fb9326, by using johnny's account

```
(body)
{
    "id": "338ef917-789e-4db7-99e6-b00169fb9326",
    "type": "post",
    "title": "new post",
    "description": "a post",
    "contentType": "md",
    "categories": "post",
    "count": 0,
    "published": "2022-03-04T18:05:48.566281Z",
    "visibility": "PUBLIC",
    "post_image": null,
    "author": "johnny"
}
```

</span>

### DELETE

remove an existing post that id is `post_id` and published by `author_id`

*Example:* `DELETE ://service/authors/johnny/posts/338ef917-789e-4db7-99e6-b00169fb9326/` will delete an existing post, id as 338ef917-789e-4db7-99e6-b00169fb9326, by using johnny's account



## Image Posts



```
URL::/service/authors/{author_id}/posts/{post_id}/image
```



### GET (remote)

retrieve an image post if it is an image post, otherwise return `404 not found`

*Example*: `GET :://service/authors/johnny/posts/338ef917-789e-4db7-99e6-b00169fb9326/image` will return the post if it is one, or `404` if it is not an image



## Comments



```
URL::/service/authors/{author_id}/posts/{post_id}/comments
```



### GET (remote) 

retrieve a list of comments of a post whose id is POST_ID, pagination enabled 

*Example*: `GET :://service/authors/johnny/posts/338ef917-789e-4db7-99e6-b00169fb9326/comments` will all comments on that post



### POST

publish a new comment on that post, using the author's name

*Example:* `POST ://service/authors/johnny/posts/338ef917-789e-4db7-99e6-b00169fb9326/comments` will publish a new comment on post 338ef917-789e-4db7-99e6-b00169fb9326, by using johnny's account.  The field below are all mandatory

```
(body)
{
    "contentType": "text/markdown", // choose from {text/markdown, text/plain}
    "comment": "this is a comment"
}
```





## Likes (N/A: send a like object, get likes of a comment)



`URL::/service/authors/{author_id}/posts/{post_id}/like`



### GET (remote)

retrieve a list of authors who liked on a POST_ID

*Example*: `GET :://service/authors/johnny/posts/338ef917-789e-4db7-99e6-b00169fb9326/likes` will show all authors who likes on a post 



## Liked (N/A: like on a comment)



`URL::/service/authors/{author_id}/liked`



### GET (remote)

retrieve a list of public posts that an author liked

*Example*: `GET :://service/authors/johnny/liked` will show a list of public posts that johnny liked 



## Inbox



`URL::/service/authors/{author_id}/inbox`



### GET (remote)

retrieve author_id's inbox 

*Example*: `GET :://service/authors/johnny/inbox` will show all stuff in johnny's inbox



<span style="color:grey">

### POST (remote) 



#### POST a post

publish a post, if the person who send the post is the author_id's follower, author_id's inbox will have that post 

*Example:* `POST ://service/authors/wong/inbox` will publish a post using `author_id` as johnny, the field below are all mandatory. If `wong` is following `johnny`, `wong`'s inbox will have such a post

```
(body)
{
    "type": "post",					// have to declare it is a post
    "title": "new post",
    "description": "this is a new post",
    "contentType": "text/markdown", // choose from {text/markdown, text/plain, application/base64, 		
    								// image/png;base64, image/jpeg;base64}
    "categories": "post web_dev", 	// separate categories with space
    "visibility": "PUBLIC", 		// choose from {PUBLIC, FRIENDS, PRIVATE}
    "post_image": null, 			// or an base64 enocoded image
    "author": "johnny"				// "author" have to specify, it could be the same person as author_id
}
```



#### POST a friend/follow request (N/A)



#### POST a like on an object (N/A: like a comment, push to inbox)

publish a like on an object, is not able to send the like object into inbox right now. (we haven't implement "like into inbox" in this project, yet)

*Example:* `POST ://service/authors/wong/inbox` will publish a like on post `338ef917-789e-4db7-99e6-b00169fb9326` using `author_id` as johnny, the field below are all mandatory. If `wong` is following `johnny`, `wong`'s inbox will have such a like

```
(body)
{
    "type": "like",					// have to declare it is a like
	"object": "338ef917-789e-4db7-99e6-b00169fb9326"
    "author": "johnny"				// "author" have to specify, it could be the same person as author_id
}
```

</span>



### DELETE

will empty the entire inbox of author_id

*Example:* `DELETE ://service/authors/wong/inbox` will empty `wong`'s inbox, so there won't be anything in `wong`'s  inbox after this DELETE is executed 
