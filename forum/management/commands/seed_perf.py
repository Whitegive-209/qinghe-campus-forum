import csv
import json
from pathlib import Path
import secrets
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from forum.models import Category, User, Post, Comment, PostLike


class Command(BaseCommand):
    help = '只在独立性能库创建200账号、1000帖子、5000评论；不清理已有数据。'

    def handle(self, *args, **options):
        if settings.DATABASES['default']['NAME'] != 'qinghe_forum_perf':
            raise CommandError('仅允许在qinghe_forum_perf运行，演示库禁止执行。')
        directory = Path(settings.BASE_DIR) / 'performance' / 'data'
        directory.mkdir(parents=True, exist_ok=True)
        manifest = directory / 'manifest.json'
        if manifest.exists():
            value = json.loads(manifest.read_text(encoding='utf-8'))
            if not User.objects.filter(username=value['first_username']).exists():
                raise CommandError('数据与清单不一致，请检查，不自动重建。')
            self.stdout.write('性能数据已存在，保留已有数据和CSV。')
            return
        if User.objects.exists() or Post.objects.exists():
            raise CommandError('目标库已有数据但无本项目性能清单，停止，避免覆盖。')
        rows = []
        with transaction.atomic():
            cats = [Category.objects.create(name=n, slug=s, order=i) for i, (n, s) in enumerate([
                ('学习交流', 'study'), ('校园生活', 'life'), ('活动广场', 'events'), ('闲置交易', 'market'), ('求助问答', 'help')])]
            users = []
            for i in range(200):
                password = 'Jm!' + secrets.token_urlsafe(16)
                u = User.objects.create_user(f'perf_{i+1:03}', password=password, nickname=f'测试同学{i+1:03}')
                users.append(u)
                rows.append([u.username, password, str(u.pk), ''])
            posts = [Post(author=users[i % 200], category=cats[i % 5], title=f'性能基础帖子{i+1:04}：校园交流', body='用于本机JMeter性能测试的独立数据。学习交流，校园生活。' * 8) for i in range(1000)]
            Post.objects.bulk_create(posts)
            posts = list(Post.objects.order_by('id'))
            Comment.objects.bulk_create([Comment(post=posts[i % 1000], author=users[i % 200], body=f'基础评论{i+1:05}') for i in range(5000)])
            PostLike.objects.bulk_create([PostLike(post=post, user=users[(i+1) % 200]) for i, post in enumerate(posts[1:])])
            target = posts[0]
            for row in rows:
                row[-1] = str(target.pk)
        with (directory / 'accounts.csv').open('x', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['username', 'password', 'user_id', 'target_post'])
            w.writerows(rows)
        value = {'database': 'qinghe_forum_perf', 'users': 200, 'posts': 1000, 'comments': 5000,
                 'initial_likes': 999, 'target_post': target.pk, 'first_username': rows[0][0],
                 '说明': 'CSV仅含合成测试账号，禁止用于真实用户；反复执行不会清库。'}
        manifest.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write('性能数据已创建：200账号、1000帖子、5000评论、999基础点赞。')
