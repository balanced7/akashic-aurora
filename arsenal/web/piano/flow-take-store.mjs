// New unique keys only. No automatic pruning or replacement of authored takes.
function open(){return new Promise((resolve,reject)=>{
 const r=indexedDB.open('violet-flow-takes',1);
 r.onupgradeneeded=()=>{r.result.createObjectStore('takes',{keyPath:'id'});r.result.createObjectStore('index',{keyPath:'id'});};
 r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.onblocked=()=>reject(new Error('The take library is open in another page version.'));
});}
async function transaction(mode,action){const db=await open();return new Promise((resolve,reject)=>{
 const tx=db.transaction('takes',mode);let value;const req=action(tx.objectStore('takes'));req.onsuccess=()=>{value=req.result;};
 tx.oncomplete=()=>{db.close();resolve(value);};tx.onerror=tx.onabort=()=>{db.close();reject(tx.error||req.error||new Error('Take storage failed'));};
});}
export async function saveTake(record){const db=await open();return new Promise((resolve,reject)=>{
 const tx=db.transaction(['takes','index'],'readwrite'),{id,name,created,duration,bytes}=record;
 tx.objectStore('takes').add(record);tx.objectStore('index').add({id,name,created,duration,bytes});
 tx.oncomplete=()=>{db.close();resolve();};tx.onerror=tx.onabort=()=>{db.close();reject(tx.error||new Error('Take storage failed'));};
});}
export const getTake=id=>transaction('readonly',store=>store.get(id));
// Metadata is kept in a separate lightweight index so listing never loads all clips.
export async function listTakes(){const db=await open();return new Promise((resolve,reject)=>{
 const tx=db.transaction('index','readonly'),r=tx.objectStore('index').getAll();
 tx.oncomplete=()=>{db.close();resolve(r.result.sort((a,b)=>b.created-a.created));};tx.onerror=()=>{db.close();reject(tx.error);};
});}
