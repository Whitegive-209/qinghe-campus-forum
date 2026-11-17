"""准备供JMeter图形界面打开的场景计划；不启动请求，参数在界面核对设置。"""
import copy
import json
from pathlib import Path
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
info=json.loads((ROOT/'.runtime/gui-latest.json').read_text(encoding='utf-8'))
directory=Path(info['directory'])
scene=info['scene']
plan=E.parse(ROOT/'performance/plans'/f'{scene}.jmx')
root=plan.getroot()
group=root.find('.//ThreadGroup')
group.set('testname',scene+'-虚拟用户')
tree=root.find('./hashTree/hashTree/hashTree')
for name,value in {'ThreadGroup.num_threads':'1','ThreadGroup.ramp_time':'1','ThreadGroup.scheduler':'false','ThreadGroup.duration':'60'}.items():
    group.find(f"*[@name='{name}']").text=value
group.find(".//*[@name='LoopController.loops']").text='1'
for s in root.findall(".//JSR223PreProcessor/stringProp[@name='script']"):
    s.text=s.text.replace("props.getProperty('run_id')",repr(directory.name))
template=E.parse(ROOT/'performance/plans/home_gui_demo.jmx')
agg=copy.deepcopy(next(n for n in template.findall('.//ResultCollector') if n.get('guiclass')=='StatVisualizer'))
agg.set('enabled','true')
agg.find("stringProp[@name='filename']").text=info['jtl']
tree.append(agg);E.SubElement(tree,'hashTree')
path=directory/'gui-plan.jmx'
if path.exists():raise RuntimeError('已存在计划，不覆盖。')
E.indent(root)
plan.write(path,encoding='utf-8',xml_declaration=True)
print(json.dumps({'plan':str(path),'scene':scene,'run_id':directory.name,'说明':'请在JMeter界面设置线程数、Ramp-up、循环和持续时间后开始。'},ensure_ascii=False))
