from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    nickname = models.CharField('昵称', max_length=30, blank=True)
    bio = models.CharField('个人简介', max_length=200, blank=True)

    @property
    def display_name(self):
        return self.nickname or self.username


class Category(models.Model):
    name = models.CharField('分类名称', max_length=30, unique=True)
    slug = models.SlugField('分类标识', unique=True)
    order = models.PositiveIntegerField('排序', default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = '分类'
        verbose_name_plural = '分类'

    def __str__(self):
        return self.name


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='posts', verbose_name='作者')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='posts', verbose_name='分类')
    title = models.CharField('标题', max_length=100)
    body = models.TextField('正文', max_length=10000)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    updated_at = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['-created_at', '-id']), models.Index(fields=['category', '-created_at'])]
        verbose_name = '帖子'
        verbose_name_plural = '帖子'

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='帖子')
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='comments', verbose_name='作者')
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='replies', verbose_name='回复对象')
    body = models.TextField('评论内容', max_length=1000)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    is_deleted = models.BooleanField('已删除', default=False)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['post', 'created_at'])]
        verbose_name = '评论'
        verbose_name_plural = '评论'

    def clean(self):
        if self.parent_id and (self.parent_id == self.pk or self.parent.post_id != self.post_id):
            raise ValidationError('回复对象必须是本帖中的其他评论。')


class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'post'], name='unique_user_post_like')]
        verbose_name = '点赞'
        verbose_name_plural = '点赞'

