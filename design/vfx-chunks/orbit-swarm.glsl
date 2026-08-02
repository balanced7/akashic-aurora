//! {"name": "orbit-swarm", "kind": "source", "from": "the background flock, reduced to one object", "note": "Thin lines with glowing trails on tilted orbits. Trails are ANALYTIC -- sampling the orbit at t-k*dt IS the past, so there is no history buffer to keep or desynchronise. Golden-angle spacing so no two orbiters ever bunch. Needs segment-distance and rot2.", "order": 50, "cat": "motion", "in": {}, "out": {"col": "vec3", "alpha": "float"}}
for(int i=0;i<10;i++){
  float fi=float(i);
  float a1=fract(sin(fi*17.13+3.1)*43758.5453), a2=fract(sin(fi*31.77+9.7)*43758.5453);
  vec3 pp,pc; vec2 sp,sc; float dp,dc;
  for(int k=0;k<=5;k++){
    float tt=u_time-float(k)*0.085;
    float rad=1.30+a1*0.44, rate=(0.55+a2*0.9)*(0.45+u_spin*2.4);
    float an=tt*rate+fi*2.39996;
    pc=vec3(cos(an)*rad,0.,sin(an)*rad);
    pR(pc.yz,(a1-0.5)*2.4); pR(pc.xy,a2*6.28318);
    dc=pc.z+3.4; sc=pc.xy*2.3/max(dc,0.2);
    if(k>0){
      float dd=segD(uv,sp,sc);
      float w=0.020/max(dc*0.42,0.2);
      float g=w/(dd+w*0.5), fade=1.-float(k)/6.;
      col+=mix(u_id1,u_tint,0.55)*(g*g*2.3)*fade*fade;
    }
    sp=sc; dp=dc;
  }
}
alpha=clamp(dot(col,vec3(.5)),0.,1.);
