# ✦ Jyotish Mitra Voice Agent ✦

A state-of-the-art, real-time Vedic Astrology Voice Assistant powered by **Gemini 2.0/3.1 Multimodal Live** and **Vobiz Telephony**.

## 📖 Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [How to Use](#how-to-use)
- [Product Requirements (PRD)](#prd)
- [Architecture](#architecture)
- [Setup & Deployment](#setup--deployment)

---

## 🌟 Overview
Jyotish Mitra is a voice-first AI agent designed to provide deep Vedic astrological insights over a standard phone call. It handles the entire lifecycle of a consultation—from collecting birth details to performing time rectification and sending a premium digital report.

## ✨ Key Features
- **Real-time Voice-to-Voice**: Sub-second latency using Gemini's Bidi-Generate technology.
- **Smart Memory**: Recognizes returning callers and resumes previous conversations.
- **Birth Time Rectification**: Uses major life incidents to align and verify astrological charts.
- **Barge-in Support**: Users can naturally interrupt the AI during the consultation.
- **Premium Reporting**: Delivers beautiful, dark-themed HTML reports via email including full transcripts.
- **Production-Ready**: Hosted on Google Cloud Run with 1-hour session persistence.

---

## 🚀 How to Use
1. **Dial the Agent**: Call the dedicated Vobiz number: `+918065481243`.
2. **Consultation Flow**:
   - Provide your **Name** (AI will confirm complex names).
   - Share your **Birth Details** (Date, Time, Place).
   - Share **1-2 Important Life Incidents** (e.g., job change, marriage) for chart alignment.
   - Wait for the **3 Vedic Insights** and share your main concern (Career, Wealth, etc.).
3. **Receive Report**: Confirm your email, and a premium report will land in your inbox immediately after the call.

---

## 📋 Product Requirements (PRD)
### **Objective**
To provide an empathetic and accurate Vedic Astrology experience that feels like talking to a human expert, while automating the data collection and reporting process.

### **Core Requirements**
- **Latency**: Must respond in <1 second to maintain conversational flow.
- **Accuracy**: Must capture names and numbers (DOB/TOB) with 95% accuracy.
- **Persistence**: Sessions must last up to 60 minutes without resetting.
- **Notifications**: Reports must be visually premium and include full conversation transcripts.

---

## 🏗 Architecture
The system consists of three main layers:
1. **Telephony (Vobiz)**: Handles the SIP/PSTN connection and streams audio via WebSockets.
2. **Bridge (Cloud Run)**: A Python `aiohttp` server that performs real-time audio resampling (8kHz to 24kHz) and manages the session state.
3. **AI Core (Gemini Live)**: The multimodal "brain" that processes audio, enforces the persona, and triggers tools (Email/Memory).

*For a detailed deep dive, see [architecture.md](./architecture.md).*

---

## 🛠 Setup & Deployment
### **Environment Variables**
Ensure the following are set in GitHub Secrets or your `.env` file:
- `GEMINI_API_KEY`: Your Google AI Studio API Key.
- `GMAIL_USER`: The sender email address.
- `GMAIL_APP_PASSWORD`: Gmail App Password for SMTP.
- `VOBIZ_NUMBER`: Your Vobiz virtual number.

### **Local Testing**
```bash
pip install -r requirements.txt
python main.py
```

### **Cloud Deployment**
Deployment is automated via GitHub Actions on every push to the `main` branch.
- **Platform**: Google Cloud Run
- **Region**: `us-central1`
- **Memory**: 512MB
- **Timeout**: 3600s

---

## 📜 License
© 2026 Jyotish Mitra. All Rights Reserved.
