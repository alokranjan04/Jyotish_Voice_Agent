import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_astrology_report(to_email, name, birth_details, analysis):
    """Sends a beautiful HTML astrology report via Gmail."""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_password:
        print("[ERROR] Email credentials not found.")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"Jyotish Mitra <{gmail_user}>"
    msg['To'] = to_email
    msg['Subject'] = f"Aapki Kundali Analysis - {name}"

    # Prepare analysis text for HTML (replace newlines with <br>)
    formatted_analysis = analysis.replace('\n', '<br>')

    # Beautiful HTML Template
    html_content = f"""
    <html>
    <body style="background-color: #0f0f0f; color: #ffffff; font-family: 'Arial', sans-serif; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #d4af37; padding: 20px; border-radius: 10px;">
            <div style="text-align: center; border-bottom: 2px solid #d4af37; padding-bottom: 20px; margin-bottom: 20px;">
                <h1 style="color: #d4af37; margin: 0; font-size: 28px;">✦ ज्योतिषा मित्र ✦</h1>
                <p style="color: #888; font-size: 14px; margin-top: 5px;">वैदिक ज्योतिष — रिपोर्ट</p>
            </div>
            
            <div style="margin-bottom: 30px;">
                <h2 style="color: #d4af37; font-size: 18px; border-left: 4px solid #d4af37; padding-left: 10px;">| जन्म विवरण</h2>
                <table style="width: 100%; color: #ccc; font-size: 15px; border-collapse: collapse;">
                    <tr><td style="padding: 8px 0; width: 40%;"><strong>नाम</strong></td><td style="color: #fff;">{name}</td></tr>
                    <tr><td style="padding: 8px 0;"><strong>विवरण</strong></td><td style="color: #fff;">{birth_details}</td></tr>
                </table>
            </div>

            <div style="margin-bottom: 30px;">
                <h2 style="color: #d4af37; font-size: 18px; border-left: 4px solid #d4af37; padding-left: 10px;">| कुंडली विश्लेषण</h2>
                <div style="color: #ddd; line-height: 1.6; font-size: 15px; background: #1a1a1a; padding: 15px; border-radius: 5px;">
                    {formatted_analysis}
                </div>
            </div>

            <div style="text-align: center; color: #888; font-size: 12px; border-top: 1px solid #333; padding-top: 20px;">
                <p>Aapki life ki raah dikhaane mein humein khushi hai.</p>
                <p>&copy; 2026 Jyotish Mitra | Vedic Astrology Insights</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print(f"[SUCCESS] Beautiful HTML Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False
