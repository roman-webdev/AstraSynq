export interface PreviewRow { row_number:number; data:Record<string,string>; classification:'valid'|'invalid'|'duplicate'; issues:{field:string;code:string}[] }
export interface ImportResult { id:string;filename:string;status:string;columns:string[];mapping:Record<string,string>;total:number;valid:number;invalid:number;duplicate:number;rows:PreviewRow[];inserted:number;created_at:string }
export interface Summary {integration_count:number;record_count:number;import_count:number;valid:number;invalid:number;duplicate:number;quality:number;series:{label:string;date:string;records:number}[];imports:{id:string;filename:string;created_at:string;total:number;valid:number;invalid:number;duplicate:number;status:string}[];records:Record<string,string>[];mode:string}
export interface Identity {id:string;email:string;role:'admin'|'operator'|'viewer';workspace_id:string;csrf_token:string}
let csrf='';
export function setCsrf(value:string){csrf=value;}
function headers(body?:BodyInit|null){const h:Record<string,string>={};if(csrf)h['X-CSRF-Token']=csrf;if(body && !(body instanceof FormData))h['Content-Type']='application/json';return h;}
async function checked(response:Response){
 if(response.status===401)window.dispatchEvent(new Event('auth-expired'));
 if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(error.detail?.code??(response.status===403?'forbidden':'api_unavailable'));}
 return response;
}
export async function request<T>(path:string,options:RequestInit={}):Promise<T>{
 let response:Response;try{response=await fetch(`/api/v1${path}`,{credentials:'same-origin',...options,headers:{...headers(options.body),...options.headers}});}catch{throw new Error('api_unavailable');}
 await checked(response);return response.status===204?undefined as T:response.json();
}
export async function download(path:string,filename:string){const response=await checked(await fetch(`/api/v1${path}`,{credentials:'same-origin',headers:headers()}));const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

