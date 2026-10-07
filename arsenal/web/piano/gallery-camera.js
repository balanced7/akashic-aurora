import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function createGalleryCamera({ THREE: T, scene, camera, canvas, getInstrument, invalidate }) {
  const controls = new OrbitControls(camera, canvas);
  controls.enabled = false; controls.enableDamping = true; controls.dampingFactor = .08;
  controls.minDistance = 20; controls.maxDistance = 480; controls.maxPolarAngle = Math.PI * .52;
  let mode = 'auto', current = null, pose = null, orbiting = false, dirty = true, updating = false;
  const from = new T.Vector3(), target = new T.Vector3(), saved = new T.Vector3();
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const performanceFog=scene.fog, galleryFog=new T.FogExp2(scene.background,.0032);
  const active = () => mode !== 'performance' && (mode !== 'auto' || !!getInstrument()?.views?.hero);
  const readPose = (handle, kind) => {
    const view = handle?.views?.[kind];
    return (typeof view === 'function' ? view() : view) || { from:[80,55,100],target:[0,0,-18],fov:38 };
  };
  controls.addEventListener('start', () => { if (active()) { orbiting = true; saved.copy(camera.position); } });
  controls.addEventListener('change', () => { if (orbiting) saved.copy(camera.position); if (!updating) invalidate(); });
  function update(dt, t) {
    const handle = getInstrument();
    controls.enabled = active();
    const fog=controls.enabled?galleryFog:performanceFog;
    fog.color.copy(scene.background);scene.fog=fog;
    if (!controls.enabled) return;
    if (current !== handle || dirty) {
      current = handle; pose = readPose(handle, mode === 'detail' ? 'close' : 'hero');
      orbiting = mode === 'orbit'; dirty = false;
      target.fromArray(pose.target); from.fromArray(pose.from);
      const fit = Math.max(1, (mode === 'detail' ? 1 : 1.55) / camera.aspect);
      from.sub(target).multiplyScalar(fit).add(target);
      controls.target.copy(target); saved.copy(from);
    }
    camera.clearViewOffset(); camera.fov = pose.fov; camera.updateProjectionMatrix();
    if (orbiting) camera.position.copy(saved);
    else {
      camera.position.copy(from);
      if (!reduced.matches) { camera.position.x += Math.sin(t*.045)*3; camera.position.y += Math.sin(t*.031)*1.2; }
      controls.target.copy(target);
    }
    updating = true; controls.update(dt); updating = false; saved.copy(camera.position);
  }
  return { active, update, get mode(){return mode;}, setMode(value){
    if (!['auto','performance','sculpture','detail','orbit'].includes(value)) return false;
    mode=value;dirty=true;invalidate();return true;
  }, resize(){dirty=true;}, home(){dirty=true;invalidate();}, dispose(){controls.dispose();} };
}
