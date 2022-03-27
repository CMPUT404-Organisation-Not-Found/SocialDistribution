from django.contrib import admin
from .models import *
#from .models import Profile


# Register your models here.
admin.site.register(Post)
admin.site.register(Author)
admin.site.register(FriendFollowRequest)
admin.site.register(Like)
admin.site.register(Liked)
admin.site.register(Followers)
admin.site.register(InboxItem)
admin.site.register(Comment)