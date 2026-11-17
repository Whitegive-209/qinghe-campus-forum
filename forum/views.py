from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .forms import RegisterForm, ProfileForm, PostForm, CommentForm
from .models import User, Category, Post, Comment, PostLike


def listed_posts():
    return Post.objects.select_related('author', 'category').annotate(
        comment_count=Count('comments', filter=Q(comments__is_deleted=False), distinct=True),
        like_count=Count('likes', distinct=True))


@require_GET
def home(request):
    posts = listed_posts()
    query = request.GET.get('q', '').strip()[:100]
    category = request.GET.get('category', '')
    sort = 'hot' if request.GET.get('sort') == 'hot' else 'new'
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(body__icontains=query))
    if category:
        get_object_or_404(Category, slug=category)
        posts = posts.filter(category__slug=category)
    posts = posts.order_by('-like_count', '-comment_count', '-created_at', '-id') if sort == 'hot' else posts.order_by('-created_at', '-id')
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'forum/home.html', {
        'page_obj': Paginator(posts, 20).get_page(request.GET.get('page')),
        'categories': Category.objects.all(), 'q': query, 'selected_category': category,
        'sort': sort, 'query_string': params.urlencode(),
    })


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, '注册成功，欢迎来到青禾校园！')
        return redirect('home')
    return render(request, 'forum/form.html', {'form': form, 'title': '加入青禾校园', 'subtitle': '从一次友善的交流开始。', 'button': '创建账号'})


@require_GET
def profile(request, pk):
    user = get_object_or_404(User, pk=pk, is_active=True)
    return render(request, 'forum/profile.html', {'profile_user': user, 'page_obj': Paginator(listed_posts().filter(author=user), 20).get_page(request.GET.get('page'))})


@login_required
@require_http_methods(['GET', 'POST'])
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '个人资料已保存。')
        return redirect('profile', pk=request.user.pk)
    return render(request, 'forum/form.html', {'form': form, 'title': '编辑个人资料', 'button': '保存资料'})


@login_required
@require_GET
def me(request):
    return JsonResponse({'id': request.user.pk, 'username': request.user.username})


@login_required
@require_http_methods(['GET', 'POST'])
def post_create(request):
    form = PostForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, '帖子已发布。')
        return redirect('post_detail', pk=post.pk)
    return render(request, 'forum/form.html', {'form': form, 'title': '分享校园新鲜事', 'subtitle': '选一个分类，写下值得分享的事。', 'button': '发布帖子'})


@require_GET
def post_detail(request, pk):
    post = get_object_or_404(listed_posts(), pk=pk)
    comments = list(post.comments.select_related('author', 'parent__author'))
    roots = []
    by_id = {item.pk: item for item in comments}
    for item in comments:
        item.thread_replies = []
    for item in comments:
        if item.parent_id:
            root = by_id[item.parent_id]
            while root.parent_id:
                root = by_id[root.parent_id]
            root.thread_replies.append(item)
        else:
            roots.append(item)
    liked = request.user.is_authenticated and PostLike.objects.filter(post=post, user=request.user).exists()
    return render(request, 'forum/detail.html', {'post': post, 'comments': roots, 'form': CommentForm(), 'liked': liked})


def owned_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.pk:
        raise PermissionDenied
    return post


@login_required
@require_http_methods(['GET', 'POST'])
def post_edit(request, pk):
    post = owned_post(request, pk)
    form = PostForm(request.POST or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '帖子修改已保存。')
        return redirect('post_detail', pk=pk)
    return render(request, 'forum/form.html', {'form': form, 'title': '编辑帖子', 'button': '保存修改'})


@login_required
@require_http_methods(['GET', 'POST'])
def post_delete(request, pk):
    post = owned_post(request, pk)
    if request.method == 'POST':
        with transaction.atomic():
            get_object_or_404(Post.objects.select_for_update(), pk=pk)
            # 先解除评论内部引用，再由帖子的外键级联统一删除。
            post.comments.update(parent=None)
            post.delete()
        messages.success(request, '帖子及其评论、点赞已删除。')
        return redirect('home')
    return render(request, 'forum/delete.html', {'post': post})


@login_required
@require_POST
def comment_create(request, pk):
    with transaction.atomic():
        # 与删除帖子串行，防止写入过程中帖子被删除。
        post = get_object_or_404(Post.objects.select_for_update(), pk=pk)
        form = CommentForm(request.POST)
        parent_id = request.POST.get('parent', '')
        parent = None
        if parent_id:
            if not parent_id.isdecimal():
                return JsonResponse({'error': '回复对象无效。'}, status=400)
            parent = get_object_or_404(Comment, pk=parent_id, post=post)
        if not form.is_valid():
            messages.error(request, '评论未发布：请输入1～1000字的有效内容。')
        else:
            comment = form.save(commit=False)
            comment.post, comment.author, comment.parent = post, request.user, parent
            comment.full_clean()
            comment.save()
            messages.success(request, '回复已发布。' if parent else '评论已发布。')
    return redirect('post_detail', pk=pk)


@login_required
@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author_id != request.user.pk:
        raise PermissionDenied
    Comment.objects.filter(pk=pk).update(body='', is_deleted=True)
    messages.success(request, '评论已删除，已有回复仍然保留。')
    return redirect('post_detail', pk=comment.post_id)


@login_required
@require_POST
def like(request, pk):
    action = request.POST.get('action')
    if action not in ('like', 'unlike'):
        return JsonResponse({'error': '请选择点赞或取消点赞。'}, status=400)
    with transaction.atomic():
        post = get_object_or_404(Post.objects.select_for_update(), pk=pk)
        if action == 'like':
            PostLike.objects.get_or_create(post=post, user=request.user)
        else:
            PostLike.objects.filter(post=post, user=request.user).delete()
        count = post.likes.count()
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'liked': action == 'like', 'count': count, 'post_id': pk})
    messages.success(request, '已点赞。' if action == 'like' else '已取消点赞。')
    return redirect('post_detail', pk=pk)


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})

