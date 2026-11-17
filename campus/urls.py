from django.contrib import admin
from django.urls import include, path

urlpatterns = [path('admin/', admin.site.urls), path('', include('forum.urls'))]
admin.site.site_header = '青禾校园 · 管理后台'
admin.site.site_title = '校园论坛管理'

