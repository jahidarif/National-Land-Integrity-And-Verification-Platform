import type{ChatMessage,Conversation}from'@/types';
export interface ChatState{conversations:Conversation[];activeConversationId:string|null;messages:ChatMessage[];loadingHistory:boolean;sending:boolean;error:string|null}
