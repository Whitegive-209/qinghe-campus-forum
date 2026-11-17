from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from .models import Category, Post, Comment, PostLike


class ForumTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = get_user_model().objects.create_user('test_alice', password='Safe-A7!mango', nickname='同学甲')
        cls.b = get_user_model().objects.create_user('test_bob', password='Safe-B9!orange', nickname='同学乙')
        cls.cat = Category.objects.create(name='学习交流', slug='study')
        cls.cat2 = Category.objects.create(name='校园生活', slug='life')
        cls.post = Post.objects.create(author=cls.a, category=cls.cat, title='中文复习计划', body='图书馆的线性代数笔记')

    def auth(self, user=None):
        self.client.force_login(user or self.a)

    def test_register_and_password_hash(self):
        """注册合法新账号并核查数据库；应自动登录且密码非明文、可正确验证。"""
        r = self.client.post(reverse('register'), {'username': 'new_student', 'nickname': '新同学', 'password1': 'Campus-Q7!coffee', 'password2': 'Campus-Q7!coffee'})
        self.assertRedirects(r, reverse('home'))
        u = get_user_model().objects.get(username='new_student')
        self.assertNotEqual(u.password, 'Campus-Q7!coffee')
        self.assertTrue(u.check_password('Campus-Q7!coffee'))
        self.assertEqual(self.client.get(reverse('me')).json()['id'], u.pk)

    def test_duplicate_username(self):
        """使用已有用户名注册；应拒绝且不增加用户。"""
        r = self.client.post(reverse('register'), {'username': self.a.username, 'password1': 'Campus-Q7!coffee', 'password2': 'Campus-Q7!coffee'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_weak_password(self):
        """使用短弱密码注册；应提示校验错误且不创建账号。"""
        r = self.client.post(reverse('register'), {'username': 'weak', 'password1': '123', 'password2': '123'})
        self.assertTrue(r.context['form'].errors)
        self.assertFalse(get_user_model().objects.filter(username='weak').exists())

    def test_password_mismatch(self):
        """两次密码不同；应拒绝注册。"""
        r = self.client.post(reverse('register'), {'username': 'mismatch', 'password1': 'Safe-Q7!coffee', 'password2': 'Safe-Q8!coffee'})
        self.assertIn('password2', r.context['form'].errors)

    def test_login_logout(self):
        """输入正确密码登录后POST退出；应身份正确且退出后无法读取登录身份。"""
        self.assertRedirects(self.client.post(reverse('login'), {'username': self.a.username, 'password': 'Safe-A7!mango'}), reverse('home'))
        self.assertEqual(self.client.get(reverse('me')).json()['id'], self.a.pk)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('home'))
        self.assertEqual(self.client.get(reverse('me')).status_code, 302)

    def test_bad_password(self):
        """错误密码登录；应失败并显示中文提示。"""
        r = self.client.post(reverse('login'), {'username': self.a.username, 'password': 'wrong'})
        self.assertContains(r, '用户名或密码不正确')
        self.assertEqual(self.client.get(reverse('me')).status_code, 302)

    def test_sessions_are_independent(self):
        """两个独立客户端分别登录甲乙；应返回各自身份。"""
        other = Client()
        self.client.login(username=self.a.username, password='Safe-A7!mango')
        other.login(username=self.b.username, password='Safe-B9!orange')
        self.assertEqual(self.client.get(reverse('me')).json()['id'], self.a.pk)
        self.assertEqual(other.get(reverse('me')).json()['id'], self.b.pk)

    def test_safe_login_redirect(self):
        """登录时提交外站next地址；应留在本地首页。"""
        r = self.client.post(reverse('login'), {'username': self.a.username, 'password': 'Safe-A7!mango', 'next': 'https://example.com/'})
        self.assertRedirects(r, reverse('home'))

    def test_post_create_detail(self):
        """登录发布中文帖子并查看详情；应保存正确作者分类和正文。"""
        self.auth()
        r = self.client.post(reverse('post_create'), {'title': '新帖子', 'body': '内容测试', 'category': self.cat.pk})
        post = Post.objects.get(title='新帖子')
        self.assertEqual(post.author, self.a)
        self.assertEqual(post.category, self.cat)
        self.assertRedirects(r, reverse('post_detail', args=[post.pk]))
        self.assertContains(self.client.get(r.url), '内容测试')

    def test_post_input_validation(self):
        """提交空白标题、超长标题正文和无效分类；应拒绝并保留原数据。"""
        self.auth()
        for data in [{'title': '  ', 'body': '内容', 'category': self.cat.pk}, {'title': '字' * 101, 'body': '内容', 'category': self.cat.pk}, {'title': '正常', 'body': '字' * 10001, 'category': self.cat.pk}, {'title': '正常', 'body': '内容', 'category': 99999}]:
            r = self.client.post(reverse('post_create'), data)
            self.assertTrue(r.context['form'].errors)
        self.assertEqual(Post.objects.count(), 1)

    def test_owner_edit(self):
        """作者编辑帖子；应保存新标题和正文。"""
        self.auth()
        r = self.client.post(reverse('post_edit', args=[self.post.pk]), {'title': '修改后', 'body': '新的正文', 'category': self.cat2.pk})
        self.assertEqual(r.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, '修改后')
        self.assertEqual(self.post.category, self.cat2)

    def test_other_user_cannot_edit_delete(self):
        """乙直接GET/POST甲的编辑和删除地址；应均403且帖子保持原样。"""
        self.auth(self.b)
        for route in ['post_edit', 'post_delete']:
            for method in [self.client.get, self.client.post]:
                self.assertEqual(method(reverse(route, args=[self.post.pk]), {'title': '篡改', 'body': '篡改', 'category': self.cat.pk}).status_code, 403)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, '中文复习计划')

    def test_delete_requires_confirmation_post(self):
        """作者GET删除确认页；应显示提示且不删除数据。"""
        self.auth()
        self.assertContains(self.client.get(reverse('post_delete', args=[self.post.pk])), '确认删除帖子')
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_delete_post_with_nested_comments(self):
        """作者删除含多层回复和点赞的帖子；应删除所有关联记录且不误删其他帖子。"""
        self.auth()
        parent = Comment.objects.create(post=self.post, author=self.a, body='一级')
        reply = Comment.objects.create(post=self.post, author=self.b, parent=parent, body='二级')
        Comment.objects.create(post=self.post, author=self.a, parent=reply, body='三级')
        PostLike.objects.create(post=self.post, user=self.b)
        other = Post.objects.create(author=self.b, category=self.cat, title='保留', body='保留')
        self.assertRedirects(self.client.post(reverse('post_delete', args=[self.post.pk])), reverse('home'))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(PostLike.objects.count(), 0)
        self.assertTrue(Post.objects.filter(pk=other.pk).exists())

    def test_comment_reply(self):
        """甲评论、乙回复该评论；应作者和父评论关系正确，详情显示内容。"""
        self.auth()
        self.client.post(reverse('comment_create', args=[self.post.pk]), {'body': '甲的评论'})
        parent = Comment.objects.get()
        self.auth(self.b)
        self.client.post(reverse('comment_create', args=[self.post.pk]), {'body': '乙的回复', 'parent': parent.pk})
        reply = Comment.objects.get(parent=parent)
        self.assertEqual(reply.author, self.b)
        self.assertContains(self.client.get(reverse('post_detail', args=[self.post.pk])), '乙的回复')

    def test_invalid_comment(self):
        """提交空白或超长评论；应拒绝且无记录。"""
        self.auth()
        for body in ['   ', '字' * 1001]:
            self.client.post(reverse('comment_create', args=[self.post.pk]), {'body': body})
        self.assertEqual(Comment.objects.count(), 0)

    def test_cross_post_reply_rejected(self):
        """伪造其他帖子的父评论ID；应404且不产生跨帖回复。"""
        other = Post.objects.create(author=self.b, category=self.cat, title='其他', body='其他')
        parent = Comment.objects.create(post=other, author=self.b, body='其他评论')
        self.auth()
        r = self.client.post(reverse('comment_create', args=[self.post.pk]), {'body': '伪造', 'parent': parent.pk})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Comment.objects.count(), 1)

    def test_invalid_parent_id(self):
        """提交非数字父评论ID；应400且无新增记录。"""
        self.auth()
        self.assertEqual(self.client.post(reverse('comment_create', args=[self.post.pk]), {'body': '内容', 'parent': 'bad'}).status_code, 400)
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_delete_retains_reply(self):
        """甲删除自己的父评论；应清空正文，保留回复和删除占位。"""
        parent = Comment.objects.create(post=self.post, author=self.a, body='需要删除')
        reply = Comment.objects.create(post=self.post, author=self.b, parent=parent, body='保留回复')
        self.auth()
        self.client.post(reverse('comment_delete', args=[parent.pk]))
        parent.refresh_from_db()
        self.assertTrue(parent.is_deleted)
        self.assertEqual(parent.body, '')
        self.assertTrue(Comment.objects.filter(pk=reply.pk).exists())
        r = self.client.get(reverse('post_detail', args=[self.post.pk]))
        self.assertContains(r, '评论已删除')
        self.assertContains(r, '保留回复')

    def test_other_cannot_delete_comment(self):
        """乙删除甲的评论；应403且正文保留。"""
        comment = Comment.objects.create(post=self.post, author=self.a, body='保留')
        self.auth(self.b)
        self.assertEqual(self.client.post(reverse('comment_delete', args=[comment.pk])).status_code, 403)
        comment.refresh_from_db()
        self.assertFalse(comment.is_deleted)

    def test_like_unlike_idempotent(self):
        """同一用户两次点赞、两次取消；数量应依次为1、1、0、0。"""
        self.auth()
        for action, count in [('like', 1), ('like', 1), ('unlike', 0), ('unlike', 0)]:
            r = self.client.post(reverse('like', args=[self.post.pk]), {'action': action}, HTTP_ACCEPT='application/json')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['count'], count)
            self.assertEqual(PostLike.objects.count(), count)

    def test_like_database_unique(self):
        """直接向数据库插入同用户同帖子第二条点赞；应由唯一约束拒绝。"""
        PostLike.objects.create(user=self.a, post=self.post)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PostLike.objects.create(user=self.a, post=self.post)
        self.assertEqual(PostLike.objects.count(), 1)

    def test_multiple_user_likes(self):
        """甲乙分别点赞，甲取消；应剩乙一条且统计为1。"""
        self.auth()
        self.client.post(reverse('like', args=[self.post.pk]), {'action': 'like'})
        self.auth(self.b)
        r = self.client.post(reverse('like', args=[self.post.pk]), {'action': 'like'}, HTTP_ACCEPT='application/json')
        self.assertEqual(r.json()['count'], 2)
        self.auth()
        r = self.client.post(reverse('like', args=[self.post.pk]), {'action': 'unlike'}, HTTP_ACCEPT='application/json')
        self.assertEqual(r.json()['count'], 1)
        self.assertEqual(PostLike.objects.get().user, self.b)

    def test_search_title_body_empty(self):
        """分别搜索中文标题、正文及不存在关键词；应匹配正确或显示无结果。"""
        for q in ['复习计划', '线性代数']:
            r = self.client.get(reverse('home'), {'q': q})
            self.assertEqual(r.context['page_obj'].paginator.count, 1)
        self.assertContains(self.client.get(reverse('home'), {'q': '不存在的词'}), '暂时没有找到相关帖子')

    def test_categories_and_sort(self):
        """创建更新但不热门的帖子；最新与热门顺序应不同，分类筛选正确。"""
        newer = Post.objects.create(author=self.b, category=self.cat2, title='更新', body='更新')
        PostLike.objects.create(user=self.b, post=self.post)
        self.assertEqual(self.client.get(reverse('home')).context['page_obj'][0], newer)
        self.assertEqual(self.client.get(reverse('home'), {'sort': 'hot'}).context['page_obj'][0], self.post)
        r = self.client.get(reverse('home'), {'category': 'life'})
        self.assertEqual(list(r.context['page_obj']), [newer])

    def test_pagination(self):
        """准备22篇帖子并翻页；应每页20条，第二页2条。"""
        Post.objects.bulk_create([Post(author=self.a, category=self.cat, title=f'分页{i}', body='内容') for i in range(21)])
        self.assertEqual(len(self.client.get(reverse('home')).context['page_obj']), 20)
        self.assertEqual(len(self.client.get(reverse('home'), {'page': 2}).context['page_obj']), 2)

    def test_anonymous_write_protected(self):
        """游客直接访问全部写入地址；应跳转登录且数据不变。"""
        comment = Comment.objects.create(post=self.post, author=self.a, body='内容')
        urls = [reverse('post_create'), reverse('post_edit', args=[self.post.pk]), reverse('post_delete', args=[self.post.pk]), reverse('comment_create', args=[self.post.pk]), reverse('comment_delete', args=[comment.pk]), reverse('like', args=[self.post.pk]), reverse('profile_edit')]
        for url in urls:
            r = self.client.post(url, {'title': '伪造', 'body': '伪造', 'action': 'like'})
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r.url.startswith(reverse('login')))
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(PostLike.objects.count(), 0)

    def test_csrf_is_enforced(self):
        """使用启用CSRF的客户端登录后不带令牌发帖；应403且无写入。"""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.a)
        self.assertEqual(client.post(reverse('post_create'), {'title': '测试', 'body': '内容', 'category': self.cat.pk}).status_code, 403)
        self.assertEqual(Post.objects.count(), 1)

    def test_xss_escaped(self):
        """帖子与评论包含script标签；页面应显示转义文本，不包含可执行标签。"""
        self.post.body = '<script>alert(1)</script>'
        self.post.save()
        Comment.objects.create(post=self.post, author=self.a, body='<script>alert(2)</script>')
        r = self.client.get(reverse('post_detail', args=[self.post.pk]))
        self.assertContains(r, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(r, '<script>alert(1)</script>')
        self.assertNotContains(r, '<script>alert(2)</script>')

    def test_profile_edit_is_self_only(self):
        """甲编辑个人资料并伪造用户ID；应仅修改甲，乙保持不变。"""
        self.auth()
        self.client.post(reverse('profile_edit'), {'nickname': '甲的新昵称', 'bio': '简介', 'id': self.b.pk})
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.nickname, '甲的新昵称')
        self.assertEqual(self.b.nickname, '同学乙')

    def test_read_only_methods(self):
        """GET退出、点赞和评论写入地址；应405且无状态改变。"""
        self.auth()
        for url in [reverse('logout'), reverse('like', args=[self.post.pk]), reverse('comment_create', args=[self.post.pk])]:
            self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.get(reverse('me')).status_code, 200)

    def test_health_and_not_found(self):
        """访问健康检查与不存在页面；应分别200和中文404。"""
        self.assertEqual(self.client.get(reverse('health')).json(), {'status': 'ok'})
        self.assertContains(self.client.get('/posts/999999/'), '没有找到这个页面', status_code=404)

