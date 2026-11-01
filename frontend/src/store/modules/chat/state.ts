import type{ChatState}from'./types';
export const state=():ChatState=>({conversations:[],activeConversationId:null,messages:[],loadingHistory:false,sending:false,error:null});
