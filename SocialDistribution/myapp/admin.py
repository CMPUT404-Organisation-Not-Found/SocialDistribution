from django.contrib import admin
from .models import *
#from .models import Profile


# Register your models here.
admin.site.register(Author)
admin.site.register(Category)
admin.site.register(Followers)
admin.site.register(FollowerCount)
admin.site.register(FriendFollowRequest)
admin.site.register(Post)
admin.site.register(Like)
admin.site.register(Comment)
admin.site.register(Liked)
admin.site.register(Inbox)
admin.site.register(ConnectionNode)