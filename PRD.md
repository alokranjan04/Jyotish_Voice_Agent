# Product Requirements Document (PRD): Jyotish Mitra

## 1. Product Vision
To build a world-class, empathetic Vedic Astrology Voice Assistant that provides users with instant, accurate, and personalized spiritual guidance through a natural phone conversation.

## 2. Target Audience
- Individuals seeking spiritual or astrological guidance.
- Users who prefer voice interaction over typing.
- Existing customers of the Jyotish Mitra platform who want a faster, automated consultation.

## 3. User Personas
### **Alok (The Returning User)**
- **Needs**: Quick follow-up on previous consultations.
- **Goal**: Wants the AI to remember his details so he doesn't have to repeat them.
- **Success**: The AI recognizes him, greets him by name, and provides deep insights into his specific career/health concerns.

---

## 4. Functional Requirements

### **FR1: Real-time Voice Consultation**
- The system must handle bidirectional audio streaming with <1s latency.
- The system must support "Barge-in" (allowing users to interrupt the AI).

### **FR2: Vedic Consultation Script**
The AI must follow a structured 7-step process:
1. **Greeting & Identification**: Warm welcome and name capture.
2. **Birth Detail Collection**: DOB, TOB (exact/approx), and POB.
3. **Birth Time Rectification**: Collection of 1-2 major life incidents for chart verification.
4. **Deep Analysis**: Delivery of 3 core personality/life insights.
5. **Concern Resolution**: Detailed focus on a specific user concern (Career, Wealth, etc.).
6. **Data Capture**: Email ID collection and verification.
7. **Reporting**: Automatic delivery of a premium HTML report and transcript.

### **FR3: User Memory & Personalization**
- The system must identify returning users via Caller ID.
- The system must offer to resume or reference previous consultations.
- Stored data must include: Name, Birth Details, and Email.

### **FR4: Premium Reporting**
- Generate a dark-themed HTML report with gold accents.
- Include a full conversation transcript in the email.
- Delivery must be via a secure SMTP connection (Gmail).

---

## 5. Non-Functional Requirements

### **NFR1: Stability & Reliability**
- Call sessions must remain stable for up to 60 minutes.
- The system must automatically reconnect the AI engine if the WebSocket drops.
- Heartbeats must be sent every 30s to prevent idle timeouts.

### **NFR2: Performance**
- Audio resampling must be efficient to prevent CPU spikes on Cloud Run.
- Cold starts on Cloud Run should be minimized to avoid initial call lag.

### **NFR3: Scalability**
- The architecture must support multiple concurrent calls using Cloud Run's auto-scaling.

---

## 6. User Experience (UX) Guidelines
- **Voice Persona**: Use the `Aoede` female voice for a calm, professional, and empathetic tone.
- **Language**: Primary language is Hinglish (a natural mix of Hindi and English).
- **Empathy**: The AI should use phrases like "Main samajh sakti hoon" (I can understand) to build trust.

---

## 7. Future Roadmap (Phase 2)
- **Multilingual Support**: Expanding into Tamil, Telugu, and Marathi.
- **Payment Integration**: Pay-per-minute or pay-per-report via UPI.
- **Advanced Rectification**: Automated chart calculation within the toolset.
- **CRM Integration**: Syncing user memory with a cloud database (Firestore/PostgreSQL).
