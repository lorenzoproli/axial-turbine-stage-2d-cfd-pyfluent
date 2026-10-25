"""Optional source-geometry utility; requires ezdxf in addition to the core environment."""
from pathlib import Path
from collections import defaultdict, Counter
import csv,json,math,zipfile
import numpy as np
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath

ROOT=Path(__file__).resolve().parents[2]
import argparse
parser=argparse.ArgumentParser(description='Extract reference boundary coordinates, DXF and a geometry-only Gmsh file.')
parser.add_argument('--source',type=Path,default=ROOT/'geometry/reference/reference_mesh.su2')
parser.add_argument('--output',type=Path,required=True,help='New output directory; existing directories are preserved')
args=parser.parse_args();SRC=args.source.resolve();OUT=args.output.resolve()
if OUT.exists():raise FileExistsError('Choose a new geometry output directory.')
OUT.mkdir(parents=True)
lines=SRC.read_text().splitlines();zones=[];i=0;zone=None
while i<len(lines):
    line=lines[i].strip()
    if line.startswith('IZONE='):
        zone={'number':int(line.split('=')[1]),'markers':{}};zones.append(zone)
    elif line.startswith('NDIME='):
        assert int(line.split('=')[1])==2
    elif line.startswith('NELEM='):
        i+=int(line.split('=')[1])
    elif line.startswith('NPOIN='):
        count=int(line.split('=')[1].split()[0]);coords={}
        for j in range(count):
            v=lines[i+1+j].split();coords[int(v[2]) if len(v)>2 else j]=(float(v[0]),float(v[1]))
        zone['points']=coords;i+=count
    elif line.startswith('MARKER_TAG='):
        tag=line.split('=',1)[1].strip();n=int(lines[i+1].split('=')[1]);edges=[]
        for j in range(n):
            v=lines[i+2+j].split()
            if int(v[0])==3:edges.append((int(v[1]),int(v[2])))
        if edges:zone['markers'][tag]=edges
        i+=1+n
    i+=1
assert len(zones)==2
# Phase shift only: align straight mixing-plane interfaces for independent meshing.
ROTOR_SHIFT_Y = -0.022759702525
zones[1]['points']={k:(x,y+ROTOR_SHIFT_Y) for k,(x,y) in zones[1]['points'].items()}

def chains(z,edges,closed=False):
    # Merge geometrically identical corner nodes without fitting or smoothing.
    pts={n:tuple(round(v,12) for v in xy) for n,xy in z['points'].items()}
    adj=defaultdict(list)
    for a,b in edges:
        a,b=pts[a],pts[b];assert a!=b;adj[a].append(b);adj[b].append(a)
    assert all(len(v) in (1,2) for v in adj.values()),Counter(len(v) for v in adj.values())
    ends=[k for k,v in adj.items() if len(v)==1]
    if closed:assert not ends
    else:assert len(ends)==2
    first=min(ends if ends else adj);path=[first];prev=None;cur=first
    while True:
        nxt=[v for v in adj[cur] if v!=prev]
        if not nxt:break
        n=nxt[0]
        if n==first:break
        assert n not in path
        path.append(n);prev,cur=cur,n
    assert len(path)==len(adj),(len(path),len(adj))
    return np.array(path)

def signed_area(p):return .5*np.sum(p[:,0]*np.roll(p[:,1],-1)-np.roll(p[:,0],-1)*p[:,1])
def write_csv(name,p,close=False):
    if close:p=np.vstack([p,p[0]])
    with (OUT/name).open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['x_m','y_m','z_m']);w.writerows((f'{x:.12g}',f'{y:.12g}','0') for x,y in p)
def dxf_doc():
    d=ezdxf.new('R2010');d.units=4;d.header['$INSUNITS']=4
    for name,color in [('STATOR',3),('ROTOR',1),('DOMAIN_STATOR',4),('DOMAIN_ROTOR',5)]:d.layers.new(name,dxfattribs={'color':color})
    return d
profiledoc=dxf_doc();domaindoc=dxf_doc();metadata=[];allgeo=[]
geo=['// Geometry only: SI metres; no mesh generated.','// Extracted boundary polylines from official SU2 axial_stage_2D.','SetFactory("Built-in");','lc = 0.001;']
point_id=0;line_id=0;loop_id=0
def geo_loop(p):
    global point_id,line_id,loop_id
    ids=[]
    for x,y in p:
        point_id+=1;ids.append(point_id);geo.append(f'Point({point_id}) = {{{x:.12g}, {y:.12g}, 0, lc}};')
    lids=[]
    for k in range(len(ids)):
        line_id+=1;lids.append(line_id);geo.append(f'Line({line_id}) = {{{ids[k]}, {ids[(k+1)%len(ids)]}}};')
    loop_id+=1;geo.append(f'Curve Loop({loop_id}) = {{{", ".join(map(str,lids))}}};');return loop_id
for z,name,wall in zip(zones,['stator','rotor'],['wall1','wall2']):
    blade=chains(z,z['markers'][wall],True)
    if signed_area(blade)>0:blade=blade[::-1]
    outertags=[t for t in z['markers'] if t!=wall]
    outer=chains(z,[e for t in outertags for e in z['markers'][t]],True)
    if signed_area(outer)<0:outer=outer[::-1]
    assert abs(signed_area(outer))>abs(signed_area(blade))>0
    assert MPath(outer,closed=False).contains_points(blade).all()
    write_csv(name+'_profile.csv',blade,True);write_csv(name+'_outline_domain.csv',outer,True)
    for tag in outertags:write_csv(name+'_'+tag+'.csv',chains(z,z['markers'][tag]))
    profiledoc.modelspace().add_lwpolyline(blade*1000,close=True,dxfattribs={'layer':name.upper()})
    domaindoc.modelspace().add_lwpolyline(blade*1000,close=True,dxfattribs={'layer':name.upper()})
    domaindoc.modelspace().add_lwpolyline(outer*1000,close=True,dxfattribs={'layer':'DOMAIN_'+name.upper()})
    lo=geo_loop(outer);lb=geo_loop(blade);geo.append(f'Plane Surface({z["number"]}) = {{{lo}, {lb}}};')
    geo.append(f'Physical Surface("{name}") = {{{z["number"]}}};')
    metadata.append({'row':name,'points':len(blade),'blade_area_m2':abs(signed_area(blade)),'domain_area_m2':abs(signed_area(outer))-abs(signed_area(blade)),'bounding_box_m':[blade.min(axis=0).tolist(),blade.max(axis=0).tolist()],'boundary_markers':outertags})
    allgeo.append((name,blade,outer))
profiledoc.saveas(OUT/'stator_rotor_profiles_2d.dxf')
domaindoc.saveas(OUT/'stator_rotor_domain_2d.dxf')
(OUT/'stator_rotor_domain_2d.geo').write_text('\n'.join(geo)+'\n')
(OUT/'geometry_info.json').write_text(json.dumps({'rotor_translation_y_m':ROTOR_SHIFT_Y,'pitch_m':0.04463756775,'csv_geo_units':'metres','dxf_units':'millimetres','rows':metadata},indent=2))
fig,ax=plt.subplots(figsize=(11,5.3))
for name,blade,outer in allgeo:
    c='#167580' if name=='stator' else '#bb6536'
    ax.plot(*np.vstack([outer,outer[0]]).T,color=c,lw=1,label='Domain '+name)
    ax.fill(blade[:,0],blade[:,1],color=c,alpha=.35)
    ax.text(blade[:,0].mean(),blade[:,1].mean(),name.capitalize(),ha='center',fontsize=10)
ax.set_aspect('equal');ax.set_xlabel('Axial X [m]');ax.set_ylabel('Tangential Y [m]');ax.grid(alpha=.2);ax.legend(loc='upper right');ax.set_title('2D stator-rotor geometry | SU2 axial_stage_2D\nAligned interface; unmeshed geometry');fig.tight_layout();fig.savefig(OUT/'preview_geometry.png',dpi=160);plt.close(fig)
print(json.dumps(metadata,indent=2))
print('OUTPUT',OUT)
