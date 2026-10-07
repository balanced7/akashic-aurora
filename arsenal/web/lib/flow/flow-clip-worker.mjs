import {encodeFlowClip} from './flow-clip.mjs';
self.onmessage=({data})=>{try{const buffer=encodeFlowClip(data);self.postMessage({buffer},[buffer]);}catch(e){self.postMessage({error:e.message});}};
