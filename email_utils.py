import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_astrology_report(to_email, name, dob, tob, pob, analysis_html, birth_chart_html, transcript=""):
    """Sends the exact premium web-version HTML report."""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_password:
        print("[ERROR] Email credentials not found.")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"Jyotish Mitra <{gmail_user}>"
    msg['To'] = to_email
    msg['Subject'] = f"✦ Aapki Janam Kundali - {name} ✦"

    # The exact HTML structure provided by the user
    html_content = f"""
    <div style="background:#0a0c12;margin:0;padding:20px;font-family:Georgia,serif">
      <div style="max-width:660px;margin:0 auto">
        <div style="margin-bottom:40px;border:1px solid #92400e;border-radius:6px;overflow:hidden;background:#111318">
          <div style="background-color:#1a1c24;padding:35px 20px;text-align:center;border-bottom:2px solid #d97706">
            <div style="font-family:'Cinzel',Georgia,serif;font-size:26px;color:#fbbf24;letter-spacing:4px;margin-bottom:8px;font-weight:bold">✦ ज्योतिष मित्र ✦</div>
            <div style="color:#fbbf24;opacity:0.6;font-size:11px;letter-spacing:3px;text-transform:uppercase;font-family:Arial,sans-serif">वैदिक ज्योतिष — रिपोर्ट</div>
          </div>

          <div style="padding:25px;border-bottom:1px solid #2d303a;background-color:#12141c">
            <h2 style="color:#fbbf24;font-size:14px;letter-spacing:1px;padding-left:12px;border-left:4px solid #d97706;margin:0 0 15px;font-family:Arial,sans-serif">📋 जन्म विवरण</h2>
            <table style="width:100%;border-collapse:collapse;color:#e2e8f0;font-size:13px;font-family:Arial,sans-serif">
              <tbody>
                <tr style="border-bottom:1px solid #ffffff05"><td style="color:#d97706;font-weight:bold;padding:8px 0;width:140px">नाम</td><td style="padding:8px 0">{name}</td></tr>
                <tr style="border-bottom:1px solid #ffffff05"><td style="color:#d97706;font-weight:bold;padding:8px 0">जन्म तिथि</td><td style="padding:8px 0">{dob}</td></tr>
                <tr style="border-bottom:1px solid #ffffff05"><td style="color:#d97706;font-weight:bold;padding:8px 0">जन्म समय</td><td style="padding:8px 0">{tob}</td></tr>
                <tr><td style="color:#d97706;font-weight:bold;padding:8px 0">जन्म स्थान</td><td style="padding:8px 0">{pob}</td></tr>
              </tbody>
            </table>
          </div>

          <div style="padding:20px 25px;border-bottom:1px solid #ffffff10;text-align:center;background:#0c0e14">
            <h2 style="color:#fbbf24;font-size:13px;letter-spacing:2px;padding-left:10px;border-left:3px solid #d97706;margin:0 0 14px;text-align:left">🌐 जन्म कुंडली चक्र</h2>
            <div style="display:inline-block;background:#080a0f;border:1px solid #d97706;padding:10px;border-radius:4px">
                {birth_chart_html}
            </div>
          </div>

          <div style="padding:25px">
            <h2 style="color:#fbbf24;font-size:14px;letter-spacing:1px;padding-left:12px;border-left:4px solid #d97706;margin:0 0 18px;font-family:Arial,sans-serif">🔮 कुंडली विश्लेषण</h2>
            <div style="font-family:Arial,sans-serif;color:#d1d5db">
                {analysis_html}
            </div>
          </div>
        </div>

        {f'<div style="text-align:center;color:#ffffff20;font-size:10px;padding:20px">Conversation History: {transcript}</div>' if transcript else ""}
        <div style="text-align:center;color:#ffffff20;font-size:10px;padding:20px">Jyotish Mitra — Vedic Intelligence System v2.5</div>
      </div>
    </div>
    """
    
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print(f"[SUCCESS] Web-Version Report sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False
