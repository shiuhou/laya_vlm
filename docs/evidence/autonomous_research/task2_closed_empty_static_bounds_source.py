from pathlib import Path
from itertools import product
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path('/home/junhongli/projects/laya-embodied-runtime')
XML = ROOT/'runs/autonomous-research/task2-pre22-counterfactual-run-01/current-model.xml'
JOURNAL = ROOT/'runs/autonomous-research/task2-additional-stationary-grasp-run-01/neck-close/episodes.jsonl'
MODEL_JOURNAL = XML.parent/'episodes.jsonl'
BDDL = ROOT/'embodied_runtime/experiments/tasks/KITCHEN_SCENE4_put_the_wine_bottle_in_the_bottom_drawer_and_close_it.bddl'
RESET_SOURCE = Path('/home/junhongli/projects/LIBERO/libero/libero/envs/bddl_base_domain.py')
tree = ET.parse(XML).getroot()
assert not tree.findall('default')
for element in tree.iter():
    if element.tag in ('geom','body','joint'):
        assert not set(element.attrib).intersection(('euler','axisangle','xyaxes','zaxis','fromto','ref'))
boundary = next(json.loads(line) for line in JOURNAL.open() if '"native_before"' in line and
    (lambda r:r['data']['step']==29 and r['data']['control']==0 and r['data']['index']==0)(json.loads(line)))
qpos = boundary['data']['qpos']
joint_values = {}; cursor = 0
for joint in tree.find('worldbody').iter('joint'):
    count = 7 if joint.get('type')=='free' else 1
    assert joint.get('type','hinge') in ('free','hinge','slide')
    joint_values[joint.get('name')] = np.asarray(qpos[cursor:cursor+count])
    cursor += count
assert cursor == len(qpos) == 26
model_record = next(json.loads(line) for line in MODEL_JOURNAL.open()
                    if '"current_model_identity"' in line)
model_identity = model_record['data']['current_model_identity']
assert hashlib.sha256(XML.read_bytes()).hexdigest() == model_identity['xml_sha256']
types=[];addresses=[];named_mapping=[];cursor=0
for joint in tree.find('worldbody').iter('joint'):
    kind=joint.get('type','hinge'); types.append({'free':0,'hinge':3,'slide':2}[kind]);addresses.append(cursor)
    named_mapping.append({'joint':joint.get('name'),'type':kind,'qpos_address':cursor})
    cursor += 7 if kind=='free' else 1
address_checks={}
for key,values in [('jnt_type',types),('jnt_qposadr',addresses)]:
    digest=hashlib.sha256(np.asarray(values,dtype=np.int32).tobytes()).hexdigest()
    assert digest==model_identity['model_array_sha256'][key]
    address_checks[key]=digest

def array(value, default):
    return np.asarray([float(x) for x in (value or default).split()])

def rotation(quat):
    w,x,y,z = quat/np.linalg.norm(quat)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
      [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
      [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

assets = {m.get('name'):m for m in tree.find('asset').findall('mesh')}
mesh_hashes = {}

def vertices(geom):
    kind = geom.get('type','sphere')
    if kind == 'mesh':
        mesh = assets[geom.get('mesh')]; path = Path(mesh.get('file')); data = path.read_bytes()
        count = struct.unpack('<I',data[80:84])[0]
        assert len(data)==84+50*count, path
        dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
        mesh_hashes[str(path)] = hashlib.sha256(data).hexdigest()
        return np.frombuffer(data,dtype=dtype,offset=84)['vertices'].reshape(-1,3).astype(float)*array(mesh.get('scale'),'1 1 1')
    size = array(geom.get('size'),'0 0 0')
    assert kind in ('box','cylinder'), kind
    extent = size if kind=='box' else np.array([size[0],size[0],size[1]])
    return np.asarray(list(product((-1,1),repeat=3)))*extent

groups = {}
def walk(body, translation, orientation, group, fixture=False):
    p = translation + orientation@array(body.get('pos'),'0 0 0')
    r = orientation@rotation(array(body.get('quat'),'1 0 0 0'))
    for joint in body.findall('joint'):
        kind=joint.get('type','hinge'); value=joint_values[joint.get('name')]
        axis=array(joint.get('axis'),'0 0 1'); axis/=np.linalg.norm(axis)
        if kind=='free':
            p=value[:3].copy();r=rotation(value[3:])
        elif kind=='slide':
            p+=r@axis*value[0]
        else:
            anchor=array(joint.get('pos'),'0 0 0')
            turn=rotation(np.r_[np.cos(value[0]/2),np.sin(value[0]/2)*axis])
            p+=r@anchor-r@turn@anchor;r=r@turn
    for geom in body.findall('geom'):
        if geom.get('contype')=='0' and geom.get('conaffinity')=='0':continue
        gp=p+r@array(geom.get('pos'),'0 0 0');gr=r@rotation(array(geom.get('quat'),'1 0 0 0'))
        points=vertices(geom)@gr.T+gp
        groups.setdefault(group,[]).append({'name':geom.get('name'),'low':points.min(axis=0),'high':points.max(axis=0)})
    for child in body.findall('body'):walk(child,p,r,group,fixture)

for body in tree.find('worldbody').findall('body'):
    name=body.get('name')
    # Fixture origins are handled as BDDL interval bounds below, not guessed from this XML.
    orient=np.diag([-1.,-1.,1.]) if name=='wine_rack_1_main' else np.eye(3)
    walk(body,np.zeros(3),orient,name)

out={};maximum_x={}
for name,geoms in groups.items():
    low=np.min([g['low'] for g in geoms],axis=0); high=np.max([g['high'] for g in geoms],axis=0)
    if name=='white_cabinet_1_main':low[0]-=.01;high[0]+=.01
    if name=='wine_rack_1_main':low[0]-=.11;high[0]-=.09
    maximum_x[name]=high[0]
    out[name]={'collision_geoms':len(geoms),'world_X_interval_m':[float(low[0]),float(high[0])],
               'max_x_geom':max(geoms,key=lambda g:g['high'][0])['name']}
    if name not in ('white_cabinet_1_main','wine_rack_1_main'):
        out[name].update(minimum=low.tolist(),maximum=high.tolist())
    else:
        out[name]['Y_Z_world_bounds']='not reconstructed or used'
bottle=out['wine_bottle_1_main']; relocated_low=np.array(bottle['minimum'])+np.array([.35,0,0]);relocated_high=np.array(bottle['maximum'])+np.array([.35,0,0])
separations={name:float(relocated_low[0]-value) for name,value in maximum_x.items() if name not in ('table','wine_bottle_1_main')}
result={'purpose':'Privileged static setup geometry only; no sensor feature or model input. No simulator import, model construction, forward, render, reset, or dynamics.',
    'xml':str(XML),'xml_sha256':hashlib.sha256(XML.read_bytes()).hexdigest(),
    'journal':str(JOURNAL),'journal_sha256':hashlib.sha256(JOURNAL.read_bytes()).hexdigest(),
    'static_model_journal':str(MODEL_JOURNAL),'static_model_journal_sha256':hashlib.sha256(MODEL_JOURNAL.read_bytes()).hexdigest(),
    'static_model_identity_record_seq':model_record['seq'],'static_model_identity_record_id':model_record['record_id'],
    'XML_joint_mapping_hashes_equal_compiled_arrays':address_checks,'named_joint_mapping':named_mapping,
    'BDDL':str(BDDL),'BDDL_sha256':hashlib.sha256(BDDL.read_bytes()).hexdigest(),
    'reset_source':str(RESET_SOURCE),'reset_source_sha256':hashlib.sha256(RESET_SOURCE.read_bytes()).hexdigest(),
    'fixture_contract_assumptions':{'white_cabinet_1':{'world_X_origin_range_m':[-.01,.01],'yaw_rad':0.0},'wine_rack_1':{'world_X_origin_range_m':[-.11,-.09],'yaw_rad':float(np.pi)},'table_workspace_origin_XY_m':[0.0,0.0]},
    'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'boundary_seq':boundary['seq'],'boundary_record_id':boundary['record_id'],'boundary_time_s':boundary['data']['time_s'],
    'method':'Pure XML joint transforms and exact raw STL vertices; boxes by corners; cylinders enclosed by a box. Fixed fixture X spans conservatively expanded across BDDL placement intervals; rack yaw pi, cabinet yaw zero. Fixture Y/Z are not reconstructed and are not used for clearance.',
    'qpos':qpos,'mesh_sha256':mesh_hashes,'bounds':out,'delta_world_m':[.35,0,0],
    'relocated_bottle_minimum_m':relocated_low.tolist(),'relocated_bottle_maximum_m':relocated_high.tolist(),
    'X_separation_lower_bounds_m':separations,
    'table_XY_contains_relocated_collision_geometry':bool(np.all(relocated_low[:2]>[-.5,-.6]) and np.all(relocated_high[:2]<[.5,.6])),
    'all_non_table_X_bounds_disjoint':all(x>0 for x in separations.values()),
    'limits':['Same-qpos geometric bounds, not old contact cache reconstruction.','Fixture BDDL origin ranges/yaws are explicit setup-contract assumptions checked by source inspection, not measured runtime fixture poses.','Geometry and BDDL placement-contract consistency require independent review and future live identity checks.','No dynamic stability, post-event robot trajectory, or camera-visibility guarantee.','Fixture Y/Z world bounds are deliberately omitted.']}
print(json.dumps(result,indent=2))
