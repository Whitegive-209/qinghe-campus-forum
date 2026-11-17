import json
from pathlib import Path
import secrets
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from forum.models import User, Category, Post, Comment, PostLike


class Command(BaseCommand):
    help = '添加示例账号和中文帖子；重复执行不会清空或覆盖已有内容。'

    @transaction.atomic
    def handle(self, *args, **options):
        categories = []
        for order, (name, slug) in enumerate([('学习交流', 'study'), ('校园生活', 'life'), ('活动广场', 'events'), ('闲置交易', 'market'), ('求助问答', 'help')]):
            obj, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'order': order})
            categories.append(obj)
        account_path = Path(settings.BASE_DIR) / '.runtime' / 'demo_accounts.json'
        accounts = json.loads(account_path.read_text(encoding='utf-8')) if account_path.exists() else []
        users = []
        for username, nickname, bio in [('demo_lin', '林间有风', '喜欢图书馆靠窗的位置，也喜欢分享学习笔记。'), ('demo_xia', '夏天的橘子', '记录校园里的小发现。'), ('demo_zhou', '小周同学', '一起学习，一起进步。')]:
            user, created = User.objects.get_or_create(username=username, defaults={'nickname': nickname, 'bio': bio})
            if created:
                password = 'Qh!' + secrets.token_urlsafe(12)
                user.set_password(password)
                user.save()
                accounts.append({'username': username, 'password': password, 'role': '普通演示账号'})
            users.append(user)
        account_path.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), encoding='utf-8')
        samples = [
            (0, 0, '期末复习怎么安排？分享一下我的图书馆学习计划', '最近开始整理期末复习笔记，把每门课分成理解、练习和回顾三个部分。\n\n每天留一点时间复盘，比临时熬夜更容易坚持。大家有什么实用的复习方法？欢迎一起交流。'),
            (1, 1, '傍晚的校园真好看，你最喜欢哪一段散步路线？', '今天下课沿着操场走了一圈，刚好遇见晚霞。\n想收集一些校园散步路线，课后一起发现日常里的小风景。'),
            (2, 2, '周末读书分享：带一本你最近喜欢的书来聊聊', '想约同学一起做个轻松的读书分享，不限定书的类型，也不要求读完。\n感兴趣的话可以在评论里说说你正在读什么，具体时间地点再一起商量。'),
            (1, 3, '出一盏闲置阅读灯，有需要的同学可以看看', '整理书桌找到一盏闲置阅读灯，功能正常。\n这是论坛功能演示内容，不是真实交易信息。实际交易请当面验货，注意保护个人信息。'),
            (2, 4, '第一次准备课程展示，有哪些表达小技巧？', '下周要做一次课程展示，有点紧张。\n大家会怎么安排开场、控制时间，或者应对提问？期待听听有经验的同学的建议。'),
            (0, 0, '学习笔记：用自己的话解释一次，真的更容易记住', '最近尝试每学完一个知识点，就用几句话讲给自己听。卡住的地方往往就是还没理解清楚的部分。\n欢迎分享你的学习小方法。'),
        ]
        for author, category, title, body in samples:
            post, created = Post.objects.get_or_create(author=users[author], title=title, defaults={'category': categories[category], 'body': body})
            if created:
                Comment.objects.create(post=post, author=users[(author + 1) % 3], body='这个话题很有共鸣，谢谢分享！')
                PostLike.objects.create(post=post, user=users[(author + 2) % 3])
        self.stdout.write(self.style.SUCCESS('演示数据已准备，账号密码见.runtime/demo_accounts.json（请勿公开）。'))

