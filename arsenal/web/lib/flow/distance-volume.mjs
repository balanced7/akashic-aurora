// Renderer-independent, transferable signed-distance volume. Scene units throughout.
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export function trilinear(a,nx,ny,nz,x,y,z){
 x=clamp(x,0,nx-1.00001);y=clamp(y,0,ny-1.00001);z=clamp(z,0,nz-1.00001);
 const i=Math.floor(x),j=Math.floor(y),k=Math.floor(z),s=nx*ny,p=i+nx*j+s*k;
 x-=i;y-=j;z-=k;
 return (1-z)*((1-y)*(a[p]*(1-x)+a[p+1]*x)+y*(a[p+nx]*(1-x)+a[p+nx+1]*x))+
 z*((1-y)*(a[p+s]*(1-x)+a[p+s+1]*x)+y*(a[p+s+nx]*(1-x)+a[p+s+nx+1]*x));
}

// Exact separable squared Euclidean distance transform of binary voxel centres.
function squaredDistance(mask,nx,ny,nz,target){
 const a=Float32Array.from(mask,v=>v===target?0:1e12),length=Math.max(nx,ny,nz);
 const f=new Float64Array(length),d=new Float64Array(length),v=new Int32Array(length),b=new Float64Array(length+1);
 function line(base,stride,n){
  for(let q=0;q<n;q++)f[q]=a[base+stride*q];
  let k=0;v[0]=0;b[0]=-Infinity;b[1]=Infinity;
  for(let q=1;q<n;q++){
   let s=((f[q]+q*q)-(f[v[k]]+v[k]*v[k]))/(2*(q-v[k]));
   while(s<=b[k]){k--;s=((f[q]+q*q)-(f[v[k]]+v[k]*v[k]))/(2*(q-v[k]));}
   k++;v[k]=q;b[k]=s;b[k+1]=Infinity;
  }
  k=0;for(let q=0;q<n;q++){while(b[k+1]<q)k++;d[q]=(q-v[k])**2+f[v[k]];}
  for(let q=0;q<n;q++)a[base+stride*q]=d[q];
 }
 for(let k=0;k<nz;k++)for(let j=0;j<ny;j++)line(nx*(j+ny*k),1,nx);
 for(let k=0;k<nz;k++)for(let i=0;i<nx;i++)line(i+nx*ny*k,nx,ny);
 for(let j=0;j<ny;j++)for(let i=0;i<nx;i++)line(i+nx*j,nx*ny,nz);
 return a;
}
export class DistanceVolume {
 constructor({nx,ny,nz,h,origin,data}){Object.assign(this,{nx,ny,nz,h,origin,data});}
 static fromFunction(spec,fn){
  const {nx,ny,nz,h,origin:o}=spec,mask=new Uint8Array(nx*ny*nz);
  for(let k=0;k<nz;k++)for(let j=0;j<ny;j++)for(let i=0;i<nx;i++)mask[i+nx*(j+ny*k)]=fn(o[0]+i*h,o[1]+j*h,o[2]+k*h)<=0?1:0;
  const outside=squaredDistance(mask,nx,ny,nz,1),inside=squaredDistance(mask,nx,ny,nz,0);
  const data=Float32Array.from(mask,(m,i)=>(m?-1:1)*(Math.sqrt(m?inside[i]:outside[i])-.5)*h);
  return new DistanceVolume({...spec,data});
 }
 sample(x,y,z){
  const {nx,ny,nz,h,origin:o,data}=this;
  x=(x-o[0])/h;y=(y-o[1])/h;z=(z-o[2])/h;
  const cx=clamp(x,0,nx-1.00001),cy=clamp(y,0,ny-1.00001),cz=clamp(z,0,nz-1.00001);
  return trilinear(data,nx,ny,nz,cx,cy,cz)+Math.hypot(x-cx,y-cy,z-cz)*h;
 }
 normal(x,y,z,out=[0,0,0]){
  const e=this.h*.75;
  out[0]=this.sample(x+e,y,z)-this.sample(x-e,y,z);out[1]=this.sample(x,y+e,z)-this.sample(x,y-e,z);out[2]=this.sample(x,y,z+e)-this.sample(x,y,z-e);
  const m=Math.hypot(...out);if(m<1e-8){out[0]=0;out[1]=1;out[2]=0;}else for(let i=0;i<3;i++)out[i]/=m;return out;
 }
 project(p,clearance=0){
  const n=[0,0,0];for(let i=0;i<12;i++){const d=this.sample(...p);if(d>=clearance-1e-5)break;this.normal(...p,n);for(let a=0;a<3;a++)p[a]+=n[a]*(clearance-d+.0001);}return p;
 }
 serialize(){const {nx,ny,nz,h,origin,data}=this;return {nx,ny,nz,h,origin,data};}
}

// Exterior adapter: rasterize triangle intersections vertically, seal from lowest
// to highest hit in each column. Deliberately bridges interior gaps/overhangs.
// Other scenes can supply analytic SDFs or their own DistanceVolume instead.
export function bakeColumnHull(triangles,h=.045){
 if(!triangles.length||triangles.length%9)throw new Error('Expected flat xyz triangle triples');
 const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
 for(let i=0;i<triangles.length;i++){const a=i%3,v=triangles[i];if(!Number.isFinite(v))throw new Error('Non-finite triangle');lo[a]=Math.min(lo[a],v);hi[a]=Math.max(hi[a],v);}
 const origin=lo.map(x=>x-h*4),[nx,ny,nz]=hi.map((x,a)=>Math.ceil((x-origin[a])/h)+5);
 const top=new Float32Array(nx*nz).fill(-Infinity),bottom=new Float32Array(nx*nz).fill(Infinity);
 for(let t=0;t<triangles.length;t+=9){
  const ax=triangles[t],ay=triangles[t+1],az=triangles[t+2],bx=triangles[t+3],by=triangles[t+4],bz=triangles[t+5],cx=triangles[t+6],cy=triangles[t+7],cz=triangles[t+8];
  const den=(bz-cz)*(ax-cx)+(cx-bx)*(az-cz);if(Math.abs(den)<1e-12)continue;
  const imin=clamp(Math.ceil((Math.min(ax,bx,cx)-origin[0])/h),0,nx-1),imax=clamp(Math.floor((Math.max(ax,bx,cx)-origin[0])/h),0,nx-1);
  const kmin=clamp(Math.ceil((Math.min(az,bz,cz)-origin[2])/h),0,nz-1),kmax=clamp(Math.floor((Math.max(az,bz,cz)-origin[2])/h),0,nz-1);
  for(let k=kmin;k<=kmax;k++)for(let i=imin;i<=imax;i++){
   const x=origin[0]+i*h,z=origin[2]+k*h,u=((bz-cz)*(x-cx)+(cx-bx)*(z-cz))/den,w=((cz-az)*(x-cx)+(ax-cx)*(z-cz))/den;
   if(u<-.0001||w<-.0001||u+w>1.0001)continue;
   const y=u*ay+w*by+(1-u-w)*cy,p=i+nx*k;top[p]=Math.max(top[p],y);bottom[p]=Math.min(bottom[p],y);
  }
 }
 return DistanceVolume.fromFunction({nx,ny,nz,h,origin},(x,y,z)=>{
  const i=Math.round((x-origin[0])/h),k=Math.round((z-origin[2])/h),p=i+nx*k;
  return Math.max(y-top[p],bottom[p]-y);
 });
}
