import {CHORD_PREVIEWS,createMidiNotes,harmonyTarget} from './gyre-harmony.mjs';
export function mountGyreMusic({onNotes,onEnable}) {
  const $=id=>document.getElementById(id),notes=createMidiNotes();let access=null,input=null,preview=null;
  function show(values,label){const h=harmonyTarget(values);onNotes(h.shape);$('harmony-status').textContent=label?`${label} · ${h.label}`:h.label;}
  function clear(){preview=null;notes.clear();show([]);document.querySelectorAll('[data-chord]').forEach(b=>b.setAttribute('aria-pressed','false'));}
  function detach(){if(input)input.onmidimessage=null;input=null;clear();}
  function select(){detach();input=access?.inputs.get($('gyre-midi-input').value)||null;if(input)input.onmidimessage=e=>{preview=null;notes.message(e.data);document.querySelectorAll('[data-chord]').forEach(b=>b.setAttribute('aria-pressed','false'));show(notes.notes());};}
  function inputs(){
    const previous=input?.id;detach();$('gyre-midi-input').replaceChildren(new Option('Choose an input…',''));
    for(const port of access.inputs.values())if(port.state!=='disconnected')$('gyre-midi-input').add(new Option(port.name||'MIDI keyboard',port.id));
    $('gyre-midi-input').value=previous&&access.inputs.has(previous)?previous:'';select();
    $('midi-message').textContent=access.inputs.size?'Choose your keyboard above.':'No MIDI input found. You can use the chord previews.';
  }
  $('gyre-connect').addEventListener('click',async()=>{
    if(!navigator.requestMIDIAccess){$('midi-message').textContent='Web MIDI is unavailable here. The chord previews still work.';return;}
    try{access=await navigator.requestMIDIAccess({sysex:false});access.onstatechange=inputs;inputs();onEnable();$('gyre-connect').textContent='Refresh MIDI';}
    catch(e){$('midi-message').textContent=`MIDI was not connected: ${e.message}`;}
  });
  $('gyre-midi-input').addEventListener('change',select);
  document.querySelectorAll('[data-chord]').forEach(b=>b.addEventListener('click',()=>{
    const key=b.dataset.chord;if(preview===key){clear();return;}clear();preview=key;onEnable();
    b.setAttribute('aria-pressed','true');show(CHORD_PREVIEWS[key].notes,CHORD_PREVIEWS[key].name);
  }));
  $('harmony-clear').addEventListener('click',clear);
  return {clear,dispose(){detach();if(access)access.onstatechange=null;}};
}
