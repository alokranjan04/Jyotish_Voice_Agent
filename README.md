# Jyotish Mitra Voice Agent (Telephony Bridge)

This repository contains the Python-based telephony bridge for the **Jyotish Mitra** Vedic astrology service. It connects **Vobiz** SIP/Websocket streams to the **Google Gemini Multimodal Live API**.

## Features
- **Real-time Vedic Consultation**: Uses the advanced Jyotish persona.
- **Telephony Integration**: Seamlessly connects to Vobiz XML Applications.
- **Hinglish/Hindi Support**: Native-feeling conversation in simple Hinglish.
- **Automated Deployment**: GitHub Actions deployment to Google Cloud Run.

## Local Setup
1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `.\.venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file with your keys.
5. Run: `python main.py`

## Cloud Deployment
Deployment is handled automatically via GitHub Actions when pushing to the `main` branch.
Required Secrets:
- `GCP_SA_KEY`: Service Account JSON Key
- `GEMINI_API_KEY`: Google Gemini API Key
- `GMAIL_USER`: Gmail address for reports
- `GMAIL_APP_PASSWORD`: Gmail App Password
- `VOBIZ_NUMBER`: Your Vobiz phone number
