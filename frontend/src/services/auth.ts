import api from'./http/api-client';
export const authApi={register:(payload:any)=>api.post('/auth/register',payload),login:(payload:any)=>api.post('/auth/login',payload),me:()=>api.get('/auth/me'),logout:()=>api.post('/auth/logout',{}),refresh:()=>api.post('/auth/refresh',{})};
