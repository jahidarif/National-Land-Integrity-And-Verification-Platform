import { reactive } from 'vue';
export interface ToastItem { id:number; message:string; kind:'success'|'error'|'info' }
export const toastState=reactive<{items:ToastItem[];dialog:ToastItem|null}>({items:[],dialog:null});
let nextId=1;
export function notify(message:string,kind:ToastItem['kind']='info'){
  const id=nextId++;
  if(kind==='error'){toastState.dialog={id,message,kind};return id;}
  toastState.items.push({id,message,kind});
  return id;
}
export function dismissToast(id:number){toastState.items=toastState.items.filter(item=>item.id!==id);}
export function dismissDialog(){toastState.dialog=null;}
