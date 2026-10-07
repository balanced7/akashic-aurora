// A conservative mesh envelope and authored stream paths; this is not a CFD solver.
export const FLOW_START=-7, FLOW_END=9, CAR_LENGTH=4.8;
export const DEFAULTS=Object.freeze({speed:1,trail:.68,clearance:.16,wake:.65,density:72,style:'mixed',paint:'pearl'});
export const LOOKS=Object.freeze({
  violet:{...DEFAULTS,name:'Violet silk'},
  ion:{...DEFAULTS,speed:1.45,trail:.36,wake:1.35,density:108,style:'sparks',paint:'graphite',name:'Ion storm'},
  hush:{...DEFAULTS,speed:.55,trail:.9,wake:.35,density:48,style:'silk',paint:'pearl',name:'Afterglow'}
});
export const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export const smooth=(a,b,x)=>{const u=clamp((x-a)/(b-a),0,1);return u*u*(3-2*u);};
export function normalizeSettings(s={}) {
  const out={...DEFAULTS};
  for(const [k,[a,b]] of Object.entries({speed:[.2,2.5],trail:[.15,1],clearance:[.06,.65],wake:[0,1.8]})){
    const n=Number(s[k]);if(Number.isFinite(n))out[k]=clamp(n,a,b);
  }
  if([48,72,108].includes(Number(s.density)))out.density=Number(s.density);
  if(['silk','sparks','mixed'].includes(s.style))out.style=s.style;
  if(['pearl','graphite'].includes(s.paint))out.paint=s.paint;
  return out;
}
export function buildEnvelope(points,minX=-2.4,maxX=2.4,bins=97){
  const widths=new Float64Array(bins),heights=new Float64Array(bins);
  for(const [x,y,z] of points){
    if(!Number.isFinite(x+y+z))throw new Error('Non-finite model vertex');
    const i=clamp(Math.round((x-minX)/(maxX-minX)*(bins-1)),0,bins-1);
    widths[i]=Math.max(widths[i],Math.abs(z));heights[i]=Math.max(heights[i],y);
  }
  function filter(values){
    const expanded=values.map((_,i)=>{let v=0;for(let j=Math.max(0,i-6);j<=Math.min(bins-1,i+6);j++)v=Math.max(v,values[j]);return v;});
    return expanded.map((_,i)=>{let sum=0,total=0;for(let j=-3;j<=3;j++){const weight=4-Math.abs(j);sum+=expanded[clamp(i+j,0,bins-1)]*weight;total+=weight;}return sum/total;});
  }
  return {minX,maxX,widths:filter(widths),heights:filter(heights)};
}
export function envelopeAt(x,e){
  const u=clamp((x-e.minX)/(e.maxX-e.minX),0,1)*(e.widths.length-1),i=Math.floor(u),j=Math.min(i+1,e.widths.length-1),f=u-i;
  const approach=smooth(e.minX-1.2,e.minX,x),release=1-smooth(e.maxX,e.maxX+1.5,x);
  return [(e.widths[i]*(1-f)+e.widths[j]*f)*approach*release,(e.heights[i]*(1-f)+e.heights[j]*f)*approach*release];
}
export function makeSeeds(count){
  return Array.from({length:count},(_,i)=>{const row=i%3,column=Math.floor(i/3),columns=Math.ceil(count/3);
    return {theta:.12+(Math.PI-.24)*(column+.2+row*.23)/columns,radius:.82+row*.42,row,id:i};
  });
}
export function flowPoint(u,seed,envelope,settings,out=[0,0,0]){
  const x=FLOW_START+(FLOW_END-FLOW_START)*u,[w,h]=envelopeAt(x,envelope);
  const sn=Math.sin(seed.theta),cs=Math.cos(seed.theta),gate=smooth(envelope.minX-1.2,envelope.minX,x)*(1-smooth(envelope.maxX,envelope.maxX+1.5,x));
  const obstacle=Math.min((w+settings.clearance*gate)/Math.max(Math.abs(cs),.0001),(h+settings.clearance*gate)/Math.max(sn,.0001));
  // Smooth maximum stays outside both the original radius and conservative obstacle radius.
  const radius=.5*(seed.radius+obstacle+Math.sqrt((seed.radius-obstacle)**2+.012));
  let y=.035+radius*sn,z=radius*cs;
  const downstream=smooth(envelope.maxX+.15,envelope.maxX+3.8,x),phase=(x-envelope.maxX)*1.7+seed.row*.5;
  const side=cs>=0?1:-1;
  z+=settings.wake*downstream*(side*.3+Math.cos(phase+seed.theta*2)*.3);
  y+=settings.wake*downstream*(.22+Math.sin(phase)*.19)*( .55+sn*.45);
  out[0]=x;out[1]=Math.max(.065,y);out[2]=z;return out;
}
