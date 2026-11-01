export interface User { id: string; fullName: string; email: string; role: "Admin" | "LandOfficer" | "User"; isActive: boolean; assignedAreaId: string | null; assignedAreaName: string | null; ownedLandIds: string[]; }
export interface Conversation { id: string; title: string; created_at: string; updated_at: string; }
export interface ChatMessage { id: string; conversation_id: string; role: "user" | "assistant"; content: string; sequence_no: number; created_at: string; }
