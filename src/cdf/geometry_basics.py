"""In Between / Frame Morph. One master slider drives the complete model.
frame_open: -1 contracted, 0 reference, +1 fully expanded.
Only the outer two posts move. Horizontal rails and the middle post stay fixed.
Rhino 8 / Grasshopper Python 3, dimensions in millimetres.
"""
import math,json
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
from System.Drawing import Color
TOL=0.001
PALETTE=[Color.FromArgb(19,19,21),Color.FromArgb(226,31,24),Color.FromArgb(24,75,132),Color.FromArgb(247,191,6)]

def checked(b,label):
    if b is None or not b.IsValid or not b.IsSolid:raise ValueError(label+': invalid or open solid')
    if b.SolidOrientation==rg.BrepSolidOrientation.Inward:b.Flip()
    return b

def solid_volume(b):
    mass=rg.VolumeMassProperties.Compute(b)
    if mass is None:raise ValueError('Cannot compute solid volume')
    return abs(mass.Volume)

def breps(items):
    return [checked(b if isinstance(b,rg.Brep) else rs.coercebrep(b),'input') for b in list(items or [])]

def extrude_profile(profile,y_depth,label):
    surface=rg.Surface.CreateExtrusion(profile,rg.Vector3d(0,y_depth,0))
    if surface is None:raise RuntimeError(label+': extrusion failed')
    return checked(surface.ToBrep().CapPlanarHoles(TOL),label)

def polygon(points,y,depth,label):
    pts=[rg.Point3d(x,y,z) for x,z in points];pts.append(pts[0])
    return extrude_profile(rg.PolylineCurve(pts),depth,label)

def block(x0,x1,z0,z1,y,depth,label):
    return polygon([(x0,z0),(x1,z0),(x1,z1),(x0,z1)],y,depth,label)

def boolean_difference(body,tool,label):
    pieces=rg.Brep.CreateBooleanDifference(body,tool,TOL)
    if pieces is None or len(pieces)==0:raise RuntimeError(label+': difference failed or removed the entire body')
    return [checked(b,label) for b in pieces]

def master_state(frame_open=0.0):
    t=max(-1.,min(1.,float(frame_open)))
    # Post OUTER faces never cross the fixed 0..100 mm horizontal rails.
    if t>=0:
        left=25.4+(0.75-25.4)*t;right=76.4+(99.25-76.4)*t
    else:
        left=25.4-16.6*t;right=76.4+16.6*t
    return {'open':t,'left':left,'right':right,'middle':57.8,
            'lower':22.6,'upper':81.8,'height':106.,'rail_length':100.,'rod':1.5,
            'left_shift':left-25.4,'morph':max(0.,t)}

def build_frame(m):
    l,r,mid,t=m['left'],m['right'],m['middle'],m['rod']
    rails=[block(0,100,m['upper']-t/2,m['upper']+t/2,-2,2,'upper rail'),
           block(0,100,m['lower']-t/2,m['lower']+t/2,-2,2,'lower rail'),
           block(l-t/2,l+t/2,m['lower']*m['morph'],m['upper'],-2,2,'moving left post'),
           block(mid-t/2,mid+t/2,31.5,m['upper'],-2,2,'fixed middle post'),
           block(r-t/2,r+t/2,m['lower'],m['height']+(m['upper']-m['height'])*m['morph'],-2,2,'moving right post')]
    return rails

def annular_ellipsoid(centre,radius,half_depth,hole):
    """Exact ellipsoid-minus-coaxial-cylinder shell, built by revolution.
    Used when Rhino's Boolean solver cannot resolve a thin oblate sphere.
    """
    outer_y=math.sqrt(max(0.,radius*radius-hole*hole))
    a=rg.Point3d(centre.X+hole,centre.Y-outer_y,centre.Z)
    b=rg.Point3d(centre.X+radius,centre.Y,centre.Z)
    c=rg.Point3d(centre.X+hole,centre.Y+outer_y,centre.Z)
    arc=rg.Arc(a,b,c).ToNurbsCurve()
    arc.Transform(rg.Transform.Scale(rg.Plane(centre,rg.Vector3d.XAxis,rg.Vector3d.YAxis),1.,half_depth/radius,1.))
    axis=rg.Line(centre,centre+rg.Vector3d.YAxis)
    outer=rg.RevSurface.Create(arc,axis,0,2*math.pi)
    if outer is None:raise RuntimeError('Red annular revolution failed')
    y0=centre.Y-outer_y*half_depth/radius
    wall=rg.Cylinder(rg.Circle(rg.Plane(rg.Point3d(centre.X,y0,centre.Z),rg.Vector3d.YAxis),hole),2*outer_y*half_depth/radius).ToBrep(False,False)
    joined=rg.Brep.JoinBreps([outer.ToBrep(),wall],TOL)
    if joined is None or len(joined)!=1:raise RuntimeError('Red annular shell did not join')
    return checked(joined[0],'red annular ellipsoid')

def build_red(m):
    """Hole radius decreases with measured rail span; thickness inflates to a sphere.
    The exact fully-open endpoint skips the zero-radius cutter entirely.
    """
    t=m['open'];q=m['morph']
    radius=17.2+(7.8*t if t>=0 else 4.2*t)
    hole=8*(1-t) if t>=0 else 8-2.5*t
    half_depth=2.5+(radius-2.5)*(q*q*(3-2*q))
    # Both frame members occupy Y=-2..0; their centreline intersection is Y=-1.
    centre=rg.Point3d(m['right'],-1.,m['upper'])
    raw=rg.Sphere(centre,radius).ToBrep()
    if q<1:
        plane=rg.Plane(centre,rg.Vector3d.XAxis,rg.Vector3d.YAxis)
        raw.Transform(rg.Transform.Scale(plane,1.,half_depth/radius,1.))
    raw=checked(raw,'red oblate sphere')
    if hole>TOL:
        cutter=rg.Cylinder(rg.Circle(rg.Plane(rg.Point3d(centre.X,centre.Y-half_depth-2,centre.Z),rg.Vector3d.YAxis),hole),2*half_depth+4).ToBrep(True,True)
        parts=rg.Brep.CreateBooleanDifference(raw,checked(cutter,'red cutter'),TOL)
        red=[checked(p,'red through-hole') for p in parts] if parts is not None and len(parts)>0 else [annular_ellipsoid(centre,radius,half_depth,hole)]
    else:red=[raw]
    meta={'radius':radius,'hole_radius':max(0.,hole),'half_depth':half_depth,
          'sphere':q>=1,'centre':[centre.X,centre.Y,centre.Z],
          'raw_volume':solid_volume(raw),'final_volume':sum(solid_volume(b) for b in red)}
    return red,meta

def half_disc(x,z,radius,y,depth,label):
    top=rg.Point3d(x,y,z+radius);left=rg.Point3d(x-radius,y,z);bottom=rg.Point3d(x,y,z-radius)
    curve=rg.PolyCurve();curve.Append(rg.Arc(top,left,bottom).ToNurbsCurve());curve.Append(rg.LineCurve(bottom,top))
    return extrude_profile(curve,depth,label)

def blue_profile(m,y):
    """Three cubic circular-arc segments morph into three straight rectangle edges.
    The fourth, right-hand edge always follows the fixed middle post.
    Exact arc and exact four-sided polygon are used at the two endpoints.
    """
    q=m['morph'];x,z=m['middle'],51.6+4.8*q;rx=x-(m['left']+11.8*(1-q));rz=20.6+4.8*q
    if rx<=TOL:raise ValueError('Blue width vanished')
    if q>=1:
        pts=[rg.Point3d(x,y,z+rz),rg.Point3d(x-rx,y,z+rz),rg.Point3d(x-rx,y,z-rz),rg.Point3d(x,y,z-rz)]
        return rg.PolylineCurve(pts+[pts[0]])
    if q<=0:
        a=rg.Point3d(x,y,z+rz);b=rg.Point3d(x-rz,y,z);c=rg.Point3d(x,y,z-rz)
        arc=rg.Arc(a,b,c).ToNurbsCurve()
        arc.Transform(rg.Transform.Scale(rg.Plane(rg.Point3d(x,y,z),rg.Vector3d.XAxis,rg.Vector3d.YAxis),rx/rz,1,1))
        profile=rg.PolyCurve();profile.Append(arc);profile.Append(rg.LineCurve(c,a));return profile
    corners=[(x,z+rz),(x-rx,z+rz),(x-rx,z-rz),(x,z-rz)]
    curve=rg.PolyCurve()
    def point(v):return rg.Point3d(v[0],y,v[1])
    for i in range(3):
        a=math.pi/2+i*math.pi/3;b=a+math.pi/3;k=4/3*math.tan((b-a)/4)
        p0=(x+rx*math.cos(a),z+rz*math.sin(a));p3=(x+rx*math.cos(b),z+rz*math.sin(b))
        p1=(p0[0]-k*rx*math.sin(a),p0[1]+k*rz*math.cos(a))
        p2=(p3[0]+k*rx*math.sin(b),p3[1]-k*rz*math.cos(b))
        ca,cb=corners[i],corners[i+1]
        linear=[ca,((2*ca[0]+cb[0])/3,(2*ca[1]+cb[1])/3),((ca[0]+2*cb[0])/3,(ca[1]+2*cb[1])/3),cb]
        points=[point(((1-q)*p[0]+q*l[0],(1-q)*p[1]+q*l[1])) for p,l in zip([p0,p1,p2,p3],linear)]
        curve.Append(rg.NurbsCurve.Create(False,3,points))
    curve.Append(rg.LineCurve(curve.PointAtEnd,curve.PointAtStart))
    if not curve.IsClosed or not curve.IsValid:raise RuntimeError('Blue morph profile failed')
    return curve


def build_blue(m,red_meta):
    # Inverse linkage is derived from the actual upper red hole measurement.
    hole=red_meta['hole_radius']
    desired=7.9+9.5*(1-hole/8) if m['open']>=0 else 7.9+4*m['open']
    span=m['middle']-(m['left']+11.8*(1-m['morph']))
    inner_radius=min(desired,span-.15,20.6-.5)
    inner_radius=max(.5,inner_radius)
    raw=extrude_profile(blue_profile(m,.6),6,'blue half-disc to quadrilateral')
    # A real partial-depth Boolean seat couples the red inlay to the blue body.
    tool=checked(rg.Cylinder(rg.Circle(rg.Plane(rg.Point3d(m['middle'],.4,51.6),rg.Vector3d.YAxis),inner_radius*1.025),2.6).ToBrep(True,True),'inner red socket tool')
    blue=boolean_difference(raw,tool,'blue recess follows inner red')
    socket_removed=solid_volume(raw)-sum(solid_volume(b) for b in blue)
    squares=[]  # Central blue remains continuous; no square perforations.
    inner=half_disc(m['middle'],51.6,inner_radius,.1,2.5,'growing inner red half-disc')
    meta={'inner_radius':inner_radius,'blue_width':span,'morph':m['morph'],
          'profile_edges':4 if m['morph']>=1 else None,
          'socket_removed':socket_removed,'squares':squares}
    return blue,[inner],meta

def yellow_cone(m):
    """The initial triangular wedge revolves about the moving right post.
    Its angular opening grows continuously to one complete revolution.
    """
    q=m['morph'];t=m['open']
    radius=29.4-9.4*q;height=52-m['lower']
    centre=rg.Point3d(m['right'],-1.,m['lower'])
    apex=centre+rg.Vector3d(0,0,height)
    if q>=1:
        return checked(rg.Cone(rg.Plane(apex,-rg.Vector3d.ZAxis),height,radius).ToBrep(True),'exact yellow cone')
    angle0=2*math.atan(1.5/radius)
    angle=angle0+(2*math.pi-angle0)*q
    plane=rg.Plane(centre,-rg.Vector3d.XAxis,-rg.Vector3d.YAxis)
    arc=rg.Arc(plane,radius,angle).ToNurbsCurve()
    a,b=arc.PointAtStart,arc.PointAtEnd
    lateral=rg.RevSurface.Create(rg.LineCurve(apex,a),rg.Line(centre,apex),0,angle).ToBrep()
    outline=rg.PolyCurve();outline.Append(rg.LineCurve(centre,a));outline.Append(arc);outline.Append(rg.LineCurve(b,centre))
    bottom=rg.Brep.CreatePlanarBreps(outline,TOL)
    sides=[rg.Brep.CreateFromCornerPoints(apex,centre,a,TOL),rg.Brep.CreateFromCornerPoints(apex,b,centre,TOL)]
    joined=rg.Brep.JoinBreps([lateral]+list(bottom)+sides,TOL)
    if joined is None or len(joined)!=1:raise RuntimeError('Yellow cone sector failed to join')
    return checked(joined[0],'yellow triangle to cone sector')

def build_lower(m):
    """The yellow/black pair is rigidly attached to the left post.
    The yellow slope is extended as a Boolean cutter through the black block.
    """
    dx=m['left_shift'];lo=m['lower']
    triangle=[(47+dx,lo),(76.4+dx,lo),(76.4+dx,52)]
    yellow=yellow_cone(m)
    right_edge=100+dx*(1-m['morph'])
    raw=block(25.4+dx,right_edge,0,lo,0,6,'black base before diagonal')
    # The cutting line is measured from the actual yellow polygon.
    a,b=triangle[0],triangle[2];slope=(b[1]-a[1])/(b[0]-a[0])
    z0,z1=-2,lo+2
    cutter=polygon([(-120,z0),(a[0]+(z0-a[1])/slope,z0),(a[0]+(z1-a[1])/slope,z1),(-120,z1)],-4,15,'yellow diagonal tool')
    base=boolean_difference(raw,cutter,'black trapezoid follows yellow')
    q=m['morph'];side=8.
    fx0=q*(m['left']-side/2);fx1=(1-q)*m['left']+q*(m['left']+side/2)
    fz0=q*(lo-side/2);fz1=(1-q)*lo+q*(lo+side/2)
    fy0=(1-q)*.6+q*(-1-25.);fy1=(1-q)*4.6+q*(-1+25.)
    foot=block(fx0,fx1,fz0,fz1,fy0,fy1-fy0,'blue foot to intersection-centred oblong')
    # The black curved corner stretches only between left and fixed middle post.
    left,mid,upper,z=m['left'],m['middle'],m['upper'],49.4
    r=upper-z;start=rg.Point3d(mid,1,upper);end=rg.Point3d(mid-r,1,z)
    arc=rg.Arc(start,rg.Point3d(mid-r/math.sqrt(2),1,z+r/math.sqrt(2)),end).ToNurbsCurve()
    arc.Transform(rg.Transform.Scale(rg.Plane(rg.Point3d(mid,1,z),rg.Vector3d.XAxis,rg.Vector3d.YAxis),(mid-left)/r,1,1))
    curve=rg.PolyCurve();curve.Append(rg.LineCurve(rg.Point3d(left,1,upper),start));curve.Append(arc);curve.Append(rg.LineCurve(rg.Point3d(left,1,z),rg.Point3d(left,1,upper)))
    corner=extrude_profile(curve,3,'corner follows left post')
    corner_raw_volume=solid_volume(corner)
    # The actual blue outline consumes the corner; an empty result means full contact.
    regions=rg.Curve.CreateBooleanDifference(curve,blue_profile(m,1),TOL)
    if regions is None:raise RuntimeError('Blue/corner planar Boolean failed')
    corners=[extrude_profile(c,3,'corner consumed by blue contact') for c in regions]
    return [yellow],base,[foot],corners,{'yellow_axis':[m['right'],-1.,lo],'yellow_cone':q>=1,'yellow_radius':29.4-9.4*q,'yellow_height':52-lo,'foot_bounds':[fx0,fx1,fy0,fy1,fz0,fz1],'base_right':right_edge,'corner_raw_volume':corner_raw_volume,'corner_volume':sum(solid_volume(c) for c in corners),'yellow_dx':dx,'base_dx':dx,'foot_width':m['left'],
            'base_removed':solid_volume(raw)-sum(solid_volume(b) for b in base)}

def assemble_model(m,frame,red,blue,inner,yellow,base,foot,corner,red_meta,blue_meta,lower_meta):
    geometry,colours,names=[],[],[]
    for items,colour,name in [(frame,0,'frame'),(red,1,'red orb'),(blue,2,'blue morph'),(inner,1,'inner red'),(yellow,3,'yellow'),(base,0,'black trapezoid'),(foot,2,'blue foot'),(corner,0,'black corner')]:
        for body in breps(items):geometry.append(body);colours.append(PALETTE[colour]);names.append(name)
    diagnostics={'master':m,'red':red_meta,'blue':blue_meta,'lower':lower_meta,'solid_count':len(geometry),'names':names}
    report='FRAME OPEN {:+.3f} | left {:.2f}, right {:.2f} mm\nRed radius {:.2f}, hole {:.3f}, half-depth {:.2f} mm{}\nInner red {:.2f} mm | blue morph {:.0%}\nBlack base translation {:+.2f} mm | foot driver {:.2f} mm\n{} valid closed solids'.format(m['open'],m['left'],m['right'],red_meta['radius'],red_meta['hole_radius'],red_meta['half_depth'],' / EXACT SPHERE' if red_meta['sphere'] else '',blue_meta['inner_radius'],blue_meta['morph'],lower_meta['yellow_dx'],lower_meta['foot_width'],len(geometry))
    return geometry,colours,report,diagnostics

def create_frame_morph(frame_open=0):
    m=master_state(frame_open);frame=build_frame(m);red,rm=build_red(m)
    blue,inner,bm=build_blue(m,rm);yellow,base,foot,corner,lm=build_lower(m)
    return assemble_model(m,frame,red,blue,inner,yellow,base,foot,corner,rm,bm,lm)
