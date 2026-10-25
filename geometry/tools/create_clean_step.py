"""Optional CAD reconstruction utility; requires a separate CadQuery environment."""
from pathlib import Path
import cadquery as cq
import numpy as np,json
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge

ROOT = Path(__file__).resolve().parents[2]
import argparse
parser = argparse.ArgumentParser(description='Construct the planar fluid-surface STEP from the supplied boundary coordinates.')
parser.add_argument('--coordinates', type=Path, default=ROOT/'geometry/coordinates')
parser.add_argument('--output', type=Path, required=True, help='New STEP path; existing files are preserved')
args = parser.parse_args()
S=args.coordinates.resolve();O=args.output.resolve()
if O.exists() or O.with_suffix('.verification.json').exists():
    raise FileExistsError('Choose a new STEP output and verification filename.')
O.parent.mkdir(parents=True,exist_ok=True)
def read(n):return np.loadtxt(S/n,delimiter=',',skiprows=1)[:-1,:2]*1000

def rdp(p,tol):
 if len(p)<3:return p
 d=p[-1]-p[0];dist=np.abs(np.cross(d,p-p[0]))/np.linalg.norm(d)
 k=int(np.argmax(dist))
 if dist[k]<=tol:return p[[0,-1]]
 return np.vstack([rdp(p[:k+1],tol)[:-1],rdp(p[k:],tol)])
def closed_simplify(p):
 k=np.argmax(np.linalg.norm(p-p[0],axis=1));return np.vstack([rdp(p[:k+1],1e-5)[:-1],rdp(np.vstack([p[k:],p[0]]),1e-5)[:-1]])
def vec(p):return [cq.Vector(float(x),float(y),0) for x,y in p]
def poly_dist(q,p):
 a=p[:-1];v=np.diff(p,axis=0);out=[]
 for chunk in np.array_split(q,20):
  delta=chunk[:,None,:]-a[None,:,:];t=np.clip(np.sum(delta*v,axis=2)/np.sum(v*v,axis=1),0,1)
  out.append(np.sqrt(np.sum((delta-t[:,:,None]*v)**2,axis=2)).min(1))
 return np.concatenate(out)
ass=cq.Assembly(name='Axial_Turbine_Stage_2D');info=[]
for name in ['stator','rotor']:
 blade=read(name+'_profile.csv');outer=read(name+'_outline_domain.csv');outer2=closed_simplify(outer)
 # Remove the redundant start vertex when it lies inside a straight edge.
 while True:
  remove=None
  for j in range(len(outer2)):
   a,b,c=outer2[j-1],outer2[j],outer2[(j+1)%len(outer2)];v=c-a
   t=np.dot(b-a,v)/np.dot(v,v)
   if 0<t<1 and np.linalg.norm(b-a-t*v)<1e-5:remove=j;break
  if remove is None:break
  outer2=np.delete(outer2,remove,axis=0)
 k=np.argmin(blade[:,0]);blade=np.roll(blade,-k,axis=0);te=int(np.argmax(blade[:,0]))
 parts=[blade[:te+1],np.vstack([blade[te:],blade[0]])];edges=[];curve_samples=[]
 for pts in parts:
  params=np.concatenate([[0],np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))])
  edge=cq.Edge.makeSpline(vec(pts),parameters=params.tolist(),tol=1e-7);edges.append(edge)
  c=BRepAdaptor_Curve(edge.wrapped)
  values=[c.Value(float(t)) for t in np.linspace(c.FirstParameter(),c.LastParameter(),4000)]
  curve_samples.append(np.array([(v.X(),v.Y()) for v in values]))
 inner=cq.Wire.assembleEdges(edges);outerw=cq.Wire.makePolygon(vec(outer2),close=True)
 face=cq.Face.makeFromWires(outerw,[inner]);assert face.isValid() and inner.IsClosed()
 poly=np.vstack([blade,blade[0]])
 max_delta=float(poly_dist(np.vstack(curve_samples),poly).max())
 assert max_delta<0.05,max_delta
 poly_area=lambda p:abs(.5*np.sum(p[:,0]*np.roll(p[:,1],-1)-np.roll(p[:,0],-1)*p[:,1]))
 oldarea=poly_area(outer)-poly_area(blade)
 deviation=abs(face.Area()-oldarea)/oldarea
 assert deviation<1e-3,deviation
 assert len(face.Edges())==len(outer2)+2
 ass.add(face,name='fluid_'+name)
 info.append({'row':name,'outer_edges':len(outer2),'blade_edges':2,'fluid_area_mm2':face.Area(),'relative_area_difference':deviation,'max_sampled_spline_to_original_polyline_distance_mm':max_delta})
ass.save(str(O),exportType='STEP',mode='default')
# Round-trip the actual STEP bytes through OpenCascade.
check=cq.importers.importStep(str(O)).val()
assert check.isValid() and len(check.Faces())==2 and len(check.Solids())==0
assert all(abs(v.Center().z)<1e-9 for v in check.Vertices())
assert sorted(len(f.Edges()) for f in check.Faces())==[i['outer_edges']+2 for i in info]
(O.with_suffix('.verification.json')).write_text(json.dumps(info,indent=2))
print(json.dumps(info,indent=2));print('STEP_VALID',O,'faces',len(check.Faces()),'edges',len(check.Edges()),'solids',len(check.Solids()))
