const NAMES=['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'];
export const CHORD_PREVIEWS={major:{name:'Cmaj7',notes:[48,55,59,64]},minor:{name:'Am9',notes:[45,52,55,59,60]},suspended:{name:'G7sus4',notes:[43,50,53,60]},open:{name:'Fmaj9',notes:[41,48,52,57,67]}};
export function harmonyTarget(notes) {
  const pitches=[...new Set(notes.filter(n=>Number.isInteger(n)&&n>=0&&n<=127))].sort((a,b)=>a-b);
  if(!pitches.length)return {shape:[0,0,0],label:'Waiting for notes',notes:[]};
  const pcs=[...new Set(pitches.map(n=>n%12))],span=pitches.at(-1)-pitches[0];
  let close=0;for(let a=0;a<pcs.length;a++)for(let b=a+1;b<pcs.length;b++){const d=(pcs[a]-pcs[b]+12)%12;if([1,2,6,10,11].includes(d))close++;}
  return {shape:[Math.min(1,(pcs.length-1)/6+span/90),Math.min(1,close/6),pcs.reduce((s,n)=>s+Math.sin(n*Math.PI/6),0)/pcs.length],label:pcs.map(n=>NAMES[n]).join(' · '),notes:pitches};
}
// One selected input; each MIDI channel retains its own pedal and held/latching state.
export function createMidiNotes() {
  const held=new Set(),latched=new Set(),pedal=new Set();
  const clearChannel=ch=>{for(const set of [held,latched])for(const key of set)if(Math.floor(key/128)===ch)set.delete(key);pedal.delete(ch);};
  return {clear(){held.clear();latched.clear();pedal.clear();},notes(){return [...new Set([...held,...latched].map(k=>k%128))].sort((a,b)=>a-b);},message(data){
    const [status,note,value]=data;if(!Number.isInteger(status)||status<128||status>=240||!Number.isInteger(note)||note<0||note>127||!Number.isInteger(value)||value<0||value>127)return;
    const type=status&240,ch=status&15,key=ch*128+note;
    if(type===144&&value>0){held.add(key);latched.delete(key);}
    else if(type===128||(type===144&&value===0)){const wasHeld=held.delete(key);if(pedal.has(ch)&&wasHeld)latched.add(key);else if(!pedal.has(ch))latched.delete(key);}
    else if(type===176){
      if(note===64){if(value>=64)pedal.add(ch);else {pedal.delete(ch);for(const k of latched)if(Math.floor(k/128)===ch)latched.delete(k);}}
      else if(note===120||note===123)clearChannel(ch);
      else if(note===121){pedal.delete(ch);for(const k of latched)if(Math.floor(k/128)===ch)latched.delete(k);}
    }
  }};
}
