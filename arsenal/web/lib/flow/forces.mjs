// An optional, authored transverse wake force; pressure projection follows it.
// Reusable local coordinates, no model names or hard-coded world positions.
export function oscillatingWake({center=[0,0,0],radius=[1,1,1],strength=1,frequency=1}={}){
 return (x,y,z,time,out)=>{
  x=(x-center[0])/radius[0];y=(y-center[1])/radius[1];z=(z-center[2])/radius[2];
  const g=strength*Math.exp(-(x*x+y*y+z*z)),phase=x*2-time*frequency;
  out[0]=0;out[1]=g*Math.sin(phase+z*2);out[2]=g*.8*Math.cos(phase+y*2);return out;
 };
}
