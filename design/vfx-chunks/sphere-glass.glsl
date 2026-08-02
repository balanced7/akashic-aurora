//! {"name": "sphere-glass", "kind": "source", "from": "the marble, reduced to its shell", "note": "A raymarch-free glass sphere: the ray-sphere crossing is closed form, so this costs one sqrt rather than a march. Fresnel rim plus a tinted interior. The cheapest way to get a believable solid into a composition.", "order": 50, "cat": "shape", "in": {"uv": "vec2"}, "out": {"col": "vec3", "alpha": "float"}}
{
  vec3 ro=vec3(0,0,-3.2), rd=normalize(vec3(uv,2.2));
  float b=dot(ro,rd), cc=dot(ro,ro)-1.0, dsc=b*b-cc;
  if(dsc>0.){
    float s=sqrt(dsc);
    vec3 nn=normalize(ro+rd*(-b-s));
    float fres=pow(1.-max(0.,dot(-rd,nn)),3.2);
    float lam=max(0.,dot(nn,normalize(vec3(.5,.7,-.6))));
    col+=mix(u_id0,u_id1,nn.y*.5+.5)*(0.18+0.55*lam);
    col+=fres*mix(u_tint,vec3(1.),0.4)*1.3;
    alpha=clamp(0.55+fres,0.,1.);
  }
}
