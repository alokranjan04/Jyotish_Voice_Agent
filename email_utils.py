import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_astrology_report(to_email, name, birth_details, analysis):
    """Sends the astrology report via Gmail."""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_password:
        print("[ERROR] Email credentials not found in environment variables.")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"Jyotish Mitra <{gmail_user}>"
    msg['To'] = to_email
    msg['Subject'] = f"Aapki Kundali Analysis - {name}"

    body = f"""
    Namaste {name} ji,
    
    Main Jyotish Mitra hoon. Aapne jo birth details share kiye hain, unke aadhar par aapki kundali ka preliminary analysis niche diya gaya hai:
    
    Birth Details:
    {birth_details}
    
    Analysis:
    {analysis}
    
    Future mein detailed report ke liye aap hamari website par visit kar sakte hain.
    
    Shubhkamnaayein,
    Jyotish Mitra
    """
    
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print(f"[SUCCESS] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False
