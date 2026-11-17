"""生成标准JMeter 5.6.3 XML计划；默认仅1用户1循环，不自动启动测试。"""
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent


def prop(node, name, value, kind='stringProp'):
    e = E.SubElement(node, kind, name=name)
    e.text = str(value)
    return e


def element(parent, tag, name, gui=None):
    node = E.SubElement(parent, tag, guiclass=gui or tag + 'Gui', testclass=tag, testname=name, enabled='true')
    tree = E.SubElement(parent, 'hashTree')
    return node, tree


def script(parent, tag, name, code):
    node, tree = element(parent, tag, name, 'TestBeanGUI')
    for k, v in {'scriptLanguage': 'groovy', 'parameters': '', 'filename': '', 'cacheKey': 'true', 'script': code}.items():
        prop(node, k, v)
    return tree


def http(parent, name, path, method='GET', data=None, expected=200, contains=None, check=None):
    node, tree = element(parent, 'HTTPSamplerProxy', name, 'HttpTestSampleGui')
    args = E.SubElement(node, 'elementProp', name='HTTPsampler.Arguments', elementType='Arguments', guiclass='HTTPArgumentsPanel', testclass='Arguments', enabled='true')
    values = E.SubElement(args, 'collectionProp', name='Arguments.arguments')
    for key, value in (data or {}).items():
        arg = E.SubElement(values, 'elementProp', name=key, elementType='HTTPArgument')
        prop(arg, 'HTTPArgument.always_encode', 'true', 'boolProp')
        prop(arg, 'Argument.name', key)
        prop(arg, 'Argument.value', value)
        prop(arg, 'Argument.metadata', '=')
        prop(arg, 'HTTPArgument.use_equals', 'true', 'boolProp')
    for k, v in {'domain': '127.0.0.1', 'port': '${__P(port,8001)}', 'protocol': 'http', 'path': path, 'method': method,
                 'contentEncoding': 'UTF-8', 'connect_timeout': '5000', 'response_timeout': '15000'}.items():
        prop(node, 'HTTPSampler.' + k, v)
    for k, v in {'follow_redirects': 'false', 'auto_redirects': 'false', 'use_keepalive': 'true', 'DO_MULTIPART_POST': 'false'}.items():
        prop(node, 'HTTPSampler.' + k, v, 'boolProp')
    code = f"if (prev.getResponseCode() != '{expected}') {{ AssertionResult.setFailure(true); AssertionResult.setFailureMessage('预期HTTP {expected}，实际'+prev.getResponseCode()); }}\n"
    if contains:
        code += f"if (!prev.getResponseDataAsString().contains('{contains}')) {{ AssertionResult.setFailure(true); AssertionResult.setFailureMessage('缺少业务标识'); }}\n"
    if check:
        code += check
    script(tree, 'JSR223Assertion', '校验HTTP和业务内容', code)
    return tree


def login(parent):
    http(parent, '登录-获取表单', '/login/', contains='csrfmiddlewaretoken')
    http(parent, '登录-提交密码', '/login/', 'POST', {'username': '${username}', 'password': '${password}'}, 302,
         check="if (prev.getResponseHeaders().contains('/login/?')) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('登录重定向异常'); }")
    http(parent, '登录-核对独立身份', '/account/me/', check="def j=new groovy.json.JsonSlurper().parseText(prev.getResponseDataAsString()); if(j.username!=vars.get('username') || j.id.toString()!=vars.get('user_id')) {AssertionResult.setFailure(true); AssertionResult.setFailureMessage('身份不匹配');}")


def build(scene):
    root = E.Element('jmeterTestPlan', version='1.2', properties='5.0', jmeter='5.6.3')
    top = E.SubElement(root, 'hashTree')
    plan, pt = element(top, 'TestPlan', '青禾校园-' + scene)
    prop(plan, 'TestPlan.functional_mode', 'false', 'boolProp')
    prop(plan, 'TestPlan.serialize_threadgroups', 'true', 'boolProp')
    args = E.SubElement(plan, 'elementProp', name='TestPlan.user_defined_variables', elementType='Arguments', guiclass='ArgumentsPanel', testclass='Arguments', enabled='true')
    E.SubElement(args, 'collectionProp', name='Arguments.arguments')
    group, gt = element(pt, 'ThreadGroup', '虚拟用户（默认1，仅本地）', 'ThreadGroupGui')
    prop(group, 'ThreadGroup.on_sample_error', 'stopthread')
    loop = E.SubElement(group, 'elementProp', name='ThreadGroup.main_controller', elementType='LoopController', guiclass='LoopControlPanel', testclass='LoopController', enabled='true')
    prop(loop, 'LoopController.continue_forever', 'false', 'boolProp')
    prop(loop, 'LoopController.loops', '${__P(loops,1)}')
    for k, v in {'num_threads': '${__P(users,1)}', 'ramp_time': '${__P(ramp,1)}', 'scheduler': '${__P(scheduled,false)}', 'duration': '${__P(duration,60)}', 'delay': '0'}.items():
        prop(group, 'ThreadGroup.' + k, v)
    cookie, _ = element(gt, 'CookieManager', '每线程独立会话', 'CookiePanel')
    E.SubElement(cookie, 'collectionProp', name='CookieManager.cookies')
    prop(cookie, 'CookieManager.clearEachIteration', 'false', 'boolProp')
    prop(cookie, 'CookieManager.controlledByThreadGroup', 'false', 'boolProp')
    header, _ = element(gt, 'HeaderManager', '请求头与动态CSRF', 'HeaderPanel')
    coll = E.SubElement(header, 'collectionProp', name='HeaderManager.headers')
    for key, value in [('X-CSRFToken', '${COOKIE_csrftoken}'), ('Accept', 'application/json'), ('User-Agent', 'Campus-JMeter-LocalTest')]:
        h = E.SubElement(coll, 'elementProp', name='', elementType='Header')
        prop(h, 'Header.name', key)
        prop(h, 'Header.value', value)
    timer, _ = element(gt, 'UniformRandomTimer', '阅读停顿1至2秒')
    prop(timer, 'ConstantTimer.delay', '${__P(think,1000)}')
    prop(timer, 'RandomTimer.range', '${__P(jitter,1000)}')
    script(gt, 'JSR223PreProcessor', '固定账号及本轮数据标识', """
if(vars.get('username')==null) {
  synchronized(props) {
    if(props.get('forumAccounts')==null) props.put('forumAccounts', new File(props.getProperty('accounts')).readLines('UTF-8').drop(1).collect{it.split(',')});
  }
  def row=props.get('forumAccounts')[ctx.getThreadNum()];
  ['username','password','user_id','target_post'].eachWithIndex{k,i->vars.put(k,row[i])};
}
vars.put('marker','JM-'+props.getProperty('run_id')+'-'+ctx.getThreadNum()+'-'+vars.getIteration());
""")
    if scene in ('write', 'like'):
        _, once = element(gt, 'OnceOnlyController', '每用户先登录一次')
        login(once)
    if scene == 'home':
        http(gt, '首页访问', '/', contains='校园动态')
    elif scene == 'browse':
        http(gt, '帖子列表', '/?category=study', contains='学习交流')
        http(gt, '帖子详情', '/posts/${target_post}/', contains='性能基础帖子')
    elif scene == 'login':
        login(gt)
        http(gt, '登录-退出', '/logout/', 'POST', expected=302)
    elif scene == 'write':
        http(gt, '发帖-获取表单', '/posts/new/', contains='发布帖子')
        tree = http(gt, '发帖-提交', '/posts/new/', 'POST', {'category': '1', 'title': '${marker}', 'body': '${marker} 正文'}, 302,
                    check="def m=(prev.getResponseHeaders() =~ /(?im)^Location: \\/posts\\/(\\d+)\\//); if(m.find()) vars.put('new_post',m.group(1)); else {AssertionResult.setFailure(true);AssertionResult.setFailureMessage('未提取新帖ID');}")
        http(gt, '发帖-详情核对', '/posts/${new_post}/', check="if(!prev.getResponseDataAsString().contains(vars.get('marker'))) {AssertionResult.setFailure(true);AssertionResult.setFailureMessage('新帖内容未保存');}")
        http(gt, '评论-提交', '/posts/${new_post}/comments/', 'POST', {'body': '${marker} 评论'}, 302)
        http(gt, '评论-详情核对', '/posts/${new_post}/', check="if(!prev.getResponseDataAsString().contains(vars.get('marker')+' 评论')) {AssertionResult.setFailure(true);AssertionResult.setFailureMessage('评论内容未保存');}")
    elif scene == 'like':
        http(gt, '点赞-获取当前CSRF', '/posts/new/', contains='csrfmiddlewaretoken')
        for label, action, state in [('点赞', 'like', 'true'), ('重复点赞', 'like', 'true'), ('取消点赞', 'unlike', 'false')]:
            http(gt, label, '/posts/${target_post}/like/', 'POST', {'action': action}, check=f"def j=new groovy.json.JsonSlurper().parseText(prev.getResponseDataAsString()); if(j.liked!={state} || j.post_id.toString()!=vars.get('target_post')) {{AssertionResult.setFailure(true);AssertionResult.setFailureMessage('点赞返回状态不正确');}}")
    E.indent(root)
    (ROOT / 'plans').mkdir(exist_ok=True)
    E.ElementTree(root).write(ROOT / 'plans' / f'{scene}.jmx', encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    for scene in ['home', 'browse', 'login', 'write', 'like']:
        build(scene)
    print('5份JMeter计划已生成，默认1用户1循环。')
