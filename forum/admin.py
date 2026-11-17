from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Post, Comment, PostLike

@admin.register(User)
class CampusUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('校园资料', {'fields': ('nickname', 'bio')}),)

admin.site.register(Category)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(PostLike)

