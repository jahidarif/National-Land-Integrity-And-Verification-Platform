import { ref } from 'vue';
let activeWindow: string | null = null;
export function useVoiceInput(windowId: string, onText: (text: string) => void) {
  const listening = ref(false); let recognition: any = null;
  function start() {
    if (typeof window === 'undefined') return;
    if (activeWindow && activeWindow !== windowId) return;
    const Speech = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Speech) return;
    activeWindow = windowId; recognition = new Speech(); recognition.lang = 'en-US'; recognition.interimResults = false;
    recognition.onresult = (event: any) => { const text = event.results?.[0]?.[0]?.transcript; if (text) onText(text); };
    recognition.onend = () => { listening.value = false; if (activeWindow === windowId) activeWindow = null; };
    recognition.onerror = () => { listening.value = false; if (activeWindow === windowId) activeWindow = null; };
    listening.value = true; recognition.start();
  }
  function stop() { recognition?.stop(); listening.value = false; if (activeWindow === windowId) activeWindow = null; }
  return { listening, start, stop };
}
