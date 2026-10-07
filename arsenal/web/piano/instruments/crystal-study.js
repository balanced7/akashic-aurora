import { createStudy, STUDIES } from '../crystal-studies.js';

// The same sculptures as the standalone studies, using the host's note/sustain clock and render loop.
export function crystalInstrument(id) {
  return {
    id, name: STUDIES[id].name,
    create(ctx) {
      const study = createStudy(ctx, id, ctx.envMap, { canopy: 'ribbons' });
      // Portrait lighting travels with the instrument and is removed with its group.
      const T=ctx.THREE;
      const key=new T.DirectionalLight(0xffefdc,2.3);key.position.set(-25,55,25);
      const rim=new T.DirectionalLight(0xa2bdff,2);rim.position.set(20,30,-50);
      const fill=new T.DirectionalLight(0xffffff,.7);fill.position.set(50,10,20);
      study.group.add(key,rim,fill,new T.HemisphereLight(0xb8c8e8,0x18131c,.45));
      let canopy = 'ribbons';
      return {
        ...study, studyId: id,
        update(dt, t, state) { return study.update(dt, t, state, ctx.ornamentalMotion?.() !== false); },
        setCanopy(form) { study.setCanopy(form); canopy = form; },
        get canopy() { return canopy; },
      };
    },
  };
}
