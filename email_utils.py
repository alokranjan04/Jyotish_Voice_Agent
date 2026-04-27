import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def build_kundali_table(planets_str: str) -> str:
    """Build a South Indian 4x4 Kundali chart from a planet positions string.

    planets_str format: "Sun=X,Moon=X,Mars=X,Mercury=X,Jupiter=X,Venus=X,Saturn=X,Rahu=X,Ketu=X"
    where X is a house number 1-12.
    """
    planet_colors = {
        'Sun': '#f97316', 'Moon': '#93c5fd', 'Mars': '#ef4444',
        'Mercury': '#22c55e', 'Jupiter': '#fbbf24', 'Venus': '#e879f9',
        'Saturn': '#94a3b8', 'Rahu': '#a78bfa', 'Ketu': '#fb923c',
    }
    planet_names_hi = {
        'Sun': 'सूर्य', 'Moon': 'चंद्र', 'Mars': 'मंगल',
        'Mercury': 'बुध', 'Jupiter': 'गुरु', 'Venus': 'शुक्र',
        'Saturn': 'शनि', 'Rahu': 'राहु', 'Ketu': 'केतु',
    }

    # Parse planet positions into house buckets
    house_contents: dict[int, list[str]] = {}
    for part in planets_str.split(','):
        part = part.strip()
        if '=' not in part:
            continue
        planet, house_str = part.split('=', 1)
        planet = planet.strip()
        try:
            house = int(house_str.strip())
        except ValueError:
            continue
        if 1 <= house <= 12 and planet in planet_colors:
            color = planet_colors[planet]
            name = planet_names_hi.get(planet, planet)
            house_contents.setdefault(house, []).append(
                f'<span style="color:{color};font-weight:bold;font-size:11px;">{name}</span>'
            )

    # South Indian 4x4 grid layout (0 = centre cells)
    grid = [
        [12, 1,  2, 3],
        [11,  0,  0, 4],
        [10,  0,  0, 5],
        [ 9,  8,  7, 6],
    ]

    html = (
        '<table border="0" cellpadding="0" cellspacing="4" '
        'style="background:#080a0f;border:1px solid #d97706;margin:0 auto;font-family:Arial,sans-serif;">'
    )
    for r, row in enumerate(grid):
        html += '<tr>'
        for c, house_num in enumerate(row):
            if house_num == 0:
                if r == 1 and c == 1:
                    html += (
                        '<td colspan="2" rowspan="2" style="background:#0c0e14;text-align:center;'
                        'color:#d97706;font-size:10px;border:1px solid #ffffff05;">'
                        '<div style="font-size:18px;margin-bottom:4px;">✦</div>'
                        'जन्म कुंडली</td>'
                    )
                continue
            planets_html = '<br>'.join(house_contents.get(house_num, []))
            html += (
                f'<td style="width:75px;height:75px;background:#111318;border:1px solid #92400e;'
                f'text-align:center;vertical-align:middle;padding:4px;">'
                f'<div style="color:#ffffff20;font-size:9px;margin-bottom:2px;">{house_num}</div>'
                f'<div style="line-height:1.3;">{planets_html}</div></td>'
            )
        html += '</tr>'
    html += '</table>'
    return html


def send_astrology_report(to_email, name, dob, tob, pob, analysis_html, planets="", transcript=""):
    """Sends the premium dark/gold Kundali HTML report via Gmail SMTP."""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        print("[ERROR] Email credentials not found.")
        return False

    # Build the Kundali chart from planet positions; fall back to a blank grid message
    if planets:
        kundali_chart_html = build_kundali_table(planets)
    else:
        kundali_chart_html = '<p style="color:#d97706;font-size:12px;">Chart data unavailable</p>'

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
              {kundali_chart_html}
            </div>
          </div>

          <div style="padding:25px">
            <h2 style="color:#fbbf24;font-size:14px;letter-spacing:1px;padding-left:12px;border-left:4px solid #d97706;margin:0 0 18px;font-family:Arial,sans-serif">🔮 कुंडली विश्लेषण</h2>
            <div style="font-family:Arial,sans-serif;color:#d1d5db">
              {analysis_html}
            </div>
          </div>

        </div>

        {f'<div style="padding:20px;border:1px solid #92400e;border-radius:4px;background:#111318;margin-bottom:20px"><h2 style="color:#fbbf24;font-size:13px;padding-left:10px;border-left:3px solid #d97706;margin:0 0 12px;font-family:Arial,sans-serif">💬 वार्तालाप इतिहास</h2><div style="color:#d1d5db;font-size:12px;line-height:1.8;font-family:Arial,sans-serif">{transcript}</div></div>' if transcript else ""}

        <div style="text-align:center;color:#ffffff20;font-size:10px;padding:20px">
          Jyotish Mitra — Vedic Intelligence System v2.5
        </div>
      </div>
    </div>
    """

    msg = MIMEMultipart()
    msg['From'] = f"ज्योतिष मित्र 🔮 <{gmail_user}>"
    msg['To'] = to_email
    msg['Subject'] = f"✦ {name} Ji — Aapki Kundali Report | ज्योतिष मित्र"
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print(f"[SUCCESS] Kundali report sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False
