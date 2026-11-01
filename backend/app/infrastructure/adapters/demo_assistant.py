
class DemoAssistant:
    """Local assistant implementation. No external LLM or Maira requests are made."""
    disclaimer = (
        "Prototype notice: this reply comes from the local demo assistant. It is not connected to Maira, "
        "live government records, or a document-verification engine."
    )

    def respond(self, message: str, history: list[dict[str, str]]) -> str:
        text = message.strip()
        normalized = text.lower()
        if any(greeting in normalized for greeting in ("hello", "hi", "hey", "assalamu", "salam")) and len(normalized) < 100:
            answer = (
                "Hello! Welcome to the National Land Integrity Platform prototype. You can ask me a question, "
                "describe a land-record concern, or explore how a future verification service could work. What would you like to discuss?"
            )
        elif any(term in normalized for term in ("khatian", "mutation", "dag", "mouza", "dakhila", "deed", "land record", "verify", "verification")):
            answer = (
                "I’ve received your land-record question. In a future connected version, the backend would identify the relevant Land ID, "
                "compare the submitted fields with authorized source records, load the parcel’s latest saved verification result, and apply "
                "privacy rules before explaining the outcome. This prototype cannot verify a Khatian, deed, ownership claim, or case because "
                "no government data source or verification engine is connected. For an actual check, use the relevant official land service or "
                "contact the competent land office."
            )
        elif any(term in normalized for term in ("who are you", "what can you do", "help", "features")):
            answer = (
                "I’m the starter chat assistant for the National Land Integrity Platform. Right now I can receive messages, return demo responses, "
                "and keep your conversations in your account history. Planned capabilities include explaining linked land records, cross-record "
                "inconsistencies, ownership/succession status, and review outcomes—but these are not active in this prototype."
            )
        else:
            preview = text if len(text) <= 180 else text[:177].rstrip() + "..."
            answer = (
                f"Thanks for sharing that: “{preview}”\n\n"
                "Your message has reached the backend and this conversation is saved to your account. This initial version uses a local response "
                "adapter rather than an AI API, so it can acknowledge messages but cannot perform live research or official land verification. "
                "The adapter can later be replaced with the approved Maira integration without changing the chat API or history model."
            )
        return answer + "\n\n" + self.disclaimer
