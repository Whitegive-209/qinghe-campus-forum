"""通过真实Chrome验证中文页面，不执行负载测试，不清空任何数据库。"""
from datetime import datetime
import json
from pathlib import Path
import re
import secrets
import time
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
STAMP = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S')
BASE = 'http://127.0.0.1:8000'
records = []


def step(name, expected, operation):
    start = time.perf_counter()
    try:
        detail = operation()
    except Exception as exc:
        records.append({'项目': name, '预期': expected, '实际': str(exc), '通过': False})
        raise
    records.append({'项目': name, '预期': expected, '实际': detail or '页面断言全部通过。',
                    '通过': True, '耗时秒': round(time.perf_counter() - start, 3)})
    print(f'通过：{name}', flush=True)


def register(page, username, nickname, password):
    page.goto(BASE + '/register/')
    page.locator('#id_username').fill(username)
    page.locator('#id_nickname').fill(nickname)
    page.locator('#id_password1').fill(password)
    page.locator('#id_password2').fill(password)
    page.get_by_role('button', name='创建账号', exact=True).click()
    expect(page.get_by_text('注册成功，欢迎来到青禾校园！', exact=True)).to_be_visible()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        a = browser.new_context(viewport={'width': 1440, 'height': 1050})
        b = browser.new_context(viewport={'width': 1440, 'height': 1050})
        page, other = a.new_page(), b.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        user_a, user_b = 'ui_a_' + STAMP, 'ui_b_' + STAMP
        nick_a, nick_b = '浏览器甲', '浏览器乙'
        password = 'Ui!' + secrets.token_urlsafe(16)
        try:
            def home():
                r = page.goto(BASE)
                page.wait_for_load_state('networkidle')
                assert r.status == 200
                expect(page.get_by_role('heading', name='校园动态')).to_be_visible()
                assert page.locator('.post-card').count() >= 6
                page.screenshot(path=str(OUT / 'homepage-desktop.png'), full_page=True)
                return 'HTTP 200，显示至少6篇中文演示帖子，已保存桌面截图。'
            step('首页和演示帖子', '首页正常，中文导航和帖子完整显示。', home)

            def mobile():
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=str(OUT / 'homepage-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1050})
                return '390px宽度未发生横向溢出，截图已保存。'
            step('窄屏布局', '390px页面无横向溢出。', mobile)

            def guest():
                page.goto(BASE + '/posts/new/')
                expect(page).to_have_url(re.compile(r'/login/\?next='))
                page.screenshot(path=str(OUT / 'login.png'), full_page=True)
            step('游客保护', '未登录发帖跳转登录页。', guest)

            step('注册甲账号', '注册成功并自动登录。', lambda: register(page, user_a, nick_a, password))
            step('注册乙账号', '独立浏览器上下文注册成功。', lambda: register(other, user_b, nick_b, password))

            def identity():
                aa, bb = a.request.get(BASE + '/account/me/').json(), b.request.get(BASE + '/account/me/').json()
                assert aa['username'] == user_a and bb['username'] == user_b and aa['id'] != bb['id']
                return '两个独立会话分别返回甲、乙用户名及不同ID，无串号。'
            step('真实会话隔离', '两个浏览器上下文身份相互独立。', identity)

            title = '浏览器验证：期末分享 ' + STAMP
            body = '浏览器正文关键词' + STAMP
            def publish():
                page.goto(BASE + '/posts/new/')
                page.locator('#id_category').select_option(label='学习交流')
                page.locator('#id_title').fill(title)
                page.locator('#id_body').fill(body)
                page.get_by_role('button', name='发布帖子', exact=True).click()
                expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
                expect(page.locator('.post-body')).to_have_text(body)
                return '发布成功，详情显示正确标题和正文。'
            step('发布及查看帖子', '甲账号发帖后进入正确详情。', publish)
            post_url = page.url
            post_id = re.search(r'/posts/(\d+)/', post_url).group(1)

            def permissions():
                response = b.request.get(BASE + f'/posts/{post_id}/edit/')
                assert response.status == 403
                token = next(c['value'] for c in b.cookies() if c['name'] == 'csrftoken')
                response = b.request.post(BASE + f'/posts/{post_id}/delete/', form={'csrfmiddlewaretoken': token})
                assert response.status == 403
                assert a.request.get(post_url).status == 200
                return '乙直接请求甲的编辑页和删除接口均403；甲帖子仍存在。'
            step('浏览器跨账号权限', '乙无法编辑、删除甲的帖子。', permissions)

            def edit():
                page.get_by_role('link', name='编辑', exact=True).click()
                page.locator('#id_title').fill(title + '（已修改）')
                page.get_by_role('button', name='保存修改', exact=True).click()
                expect(page.get_by_role('heading', name=title + '（已修改）', exact=True)).to_be_visible()
            step('编辑本人帖子', '修改后详情显示新标题。', edit)

            def comments():
                page.locator('#id_body').fill('甲的浏览器评论')
                page.get_by_role('button', name='发布评论', exact=True).click()
                expect(page.locator('.comment-list')).to_contain_text('甲的浏览器评论')
                other.goto(post_url)
                other.locator('.comment').filter(has_text='甲的浏览器评论').get_by_role('button', name='回复', exact=True).click()
                expect(other.locator('#reply-indicator')).to_be_visible()
                other.locator('#id_body').fill('乙的浏览器回复')
                other.get_by_role('button', name='发布评论', exact=True).click()
                expect(other.locator('.replies')).to_contain_text('乙的浏览器回复')
            step('评论与回复', '甲发表评论，乙通过回复按钮正确回复。', comments)

            def like():
                other.get_by_role('button', name='点赞 · 0', exact=True).click()
                expect(other.get_by_role('button', name='取消点赞 · 1', exact=True)).to_be_visible()
                other.get_by_role('button', name='取消点赞 · 1', exact=True).click()
                expect(other.get_by_role('button', name='点赞 · 0', exact=True)).to_be_visible()
            step('点赞与取消', '点击后数量0→1→0，按钮状态同步。', like)

            def search():
                for q in [STAMP, body]:
                    page.goto(BASE)
                    page.locator('#search-q').fill(q)
                    page.get_by_role('button', name='搜索', exact=True).click()
                    expect(page.locator('.post-card')).to_have_count(1)
                page.locator('#search-q').fill('无此结果' + STAMP)
                page.get_by_role('button', name='搜索', exact=True).click()
                expect(page.get_by_role('heading', name='暂时没有找到相关帖子')).to_be_visible()
            step('标题正文搜索及空结果', '标题、正文均可检索，无结果有提示。', search)

            def profile():
                page.goto(BASE + '/settings/profile/')
                page.locator('#id_nickname').fill('浏览器甲已更新')
                page.locator('#id_bio').fill('这是浏览器实际验证的简介。')
                page.get_by_role('button', name='保存资料', exact=True).click()
                expect(page.get_by_role('heading', name='浏览器甲已更新')).to_be_visible()
                expect(page.get_by_text('这是浏览器实际验证的简介。', exact=True)).to_be_visible()
                page.screenshot(path=str(OUT / 'profile.png'), full_page=True)
            step('个人资料', '保存后主页显示更新后的昵称和简介。', profile)

            def remove_comment():
                page.goto(post_url)
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('.comment').filter(has_text='甲的浏览器评论').get_by_role('button', name='删除评论').click()
                expect(page.locator('.comment-list')).to_contain_text('评论已删除')
                expect(page.locator('.replies')).to_contain_text('乙的浏览器回复')
                page.screenshot(path=str(OUT / 'post-detail.png'), full_page=True)
            step('删除本人评论', '删除原文，保留回复与占位。', remove_comment)

            def remove_post():
                page.get_by_role('link', name='删除', exact=True).click()
                expect(page.get_by_role('heading', name='确定删除这篇帖子？')).to_be_visible()
                page.get_by_role('button', name='确认删除帖子', exact=True).click()
                expect(page.get_by_text('帖子及其评论、点赞已删除。', exact=True)).to_be_visible()
                assert a.request.get(post_url).status == 404
            step('二次确认删除帖子', '本人确认后删除，详情变为404。', remove_post)

            def logout_login():
                page.get_by_role('button', name='退出', exact=True).click()
                page.goto(BASE + '/posts/new/')
                expect(page).to_have_url(re.compile(r'/login/\?next='))
                page.locator('#id_username').fill(user_a)
                page.locator('#id_password').fill('wrong-password')
                page.get_by_role('button', name='登录', exact=True).click()
                expect(page.get_by_text('用户名或密码不正确，请重新输入。', exact=True)).to_be_visible()
                page.locator('#id_password').fill(password)
                page.get_by_role('button', name='登录', exact=True).click()
                expect(page.get_by_role('heading', name='分享校园新鲜事')).to_be_visible()
            step('退出、错误密码和重新登录', '退出后失去权限，错误密码失败，正确密码登录并回到原页。', logout_login)
            step('JavaScript运行', '无未捕获的页面脚本错误。', lambda: (_ for _ in ()).throw(AssertionError(errors)) if errors else '未捕获脚本错误0条。')
        except Exception:
            page.screenshot(path=str(OUT / f'browser-failure-{STAMP}.png'), full_page=True)
            raise
        finally:
            report = {'执行时间': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), '地址': BASE,
                      '浏览器': browser.version, '执行数': len(records), '成功': bool(records) and all(r['通过'] for r in records),
                      '说明': '真实Chrome无头浏览器。新增2个带时间标识的普通测试账号；本次测试帖子已通过被测删除流程处理。', '用例': records}
            (OUT / 'browser-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            browser.close()


if __name__ == '__main__':
    main()
