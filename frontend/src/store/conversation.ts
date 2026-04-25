import { create } from "zustand";

import type { ChatMessage, MessageRole } from "@/components/MessageBubble";

export interface ConversationState {
  messages: ChatMessage[];
  addMessage: (role: MessageRole, text: string) => ChatMessage;
  clearMessages: () => void;
  resetToGreeting: () => void;
}

const GREETING: ChatMessage = {
  id: "welcome",
  role: "assistant",
  text: "Merhaba, size nasıl yardımcı olabilirim?",
  createdAt: 0,
};

let messageCounter = 0;
const nextId = (role: MessageRole) => `${role}-${Date.now()}-${++messageCounter}`;

export const useConversation = create<ConversationState>((set) => ({
  messages: [GREETING],
  addMessage: (role, text) => {
    const message: ChatMessage = {
      id: nextId(role),
      role,
      text,
      createdAt: Date.now(),
    };
    set((state) => ({ messages: [...state.messages, message] }));
    return message;
  },
  clearMessages: () => set({ messages: [] }),
  resetToGreeting: () => set({ messages: [GREETING] }),
}));
