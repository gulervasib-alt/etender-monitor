import os
import requests
import urllib.parse
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFİQURASİYA ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
SPREADSHEET_ID = "1b8_5J6crGz7284BjP-8wno95035znDJ0VE9QKouNkMo"

KEYWORDS = [
    'veb sayt', 'veb', 'sayt', 'www',
    'proqram təminatı', 'proqram', 'portal',
    'web', 'rəqəmsal', 'hackathon', 'hakaton'
]

def get_google_sheet():
    import json
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram xətası: {e}")

def fetch_tenders_by_keyword(keyword):
    encoded_kw = urllib.parse.quote(keyword)
    api_url = (
        f"https://etender.gov.az/api/events"
        f"?EventType=2&PageSize=50&PageNumber=1&EventStatus=1"
        f"&Keyword={encoded_kw}"
        f"&buyerOrganizationName=&documentNumber="
        f"&publishDateFrom=&publishDateTo="
        f"&AwardedparticipantName=&AwardedparticipantVoen="
        f"&DocumentViewType=&IsArchived=false"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://etender.gov.az/main/competitions/1/0"
    }
    try:
        res = requests.get(api_url, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data.get("items", [])
    except Exception as e:
        print(f"API xətası ({keyword}): {e}")
    return []

def format_date(date_str):
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_str

def main():
    sheet = get_google_sheet()

    # Mövcud ID-ləri oxu (2-ci sütun = id, başlığı keçirik)
    existing_ids = set(sheet.col_values(2)[1:])
    print(f"Mövcud tender sayı: {len(existing_ids)}")

    new_rows = []

    for kw in KEYWORDS:
        print(f"Axtarılır: {kw}")
        items = fetch_tenders_by_keyword(kw)

        for item in items:
            event_id = str(item.get("eventId", ""))
            if not event_id or event_id in existing_ids:
                continue

            org = item.get("buyerOrganizationName", "N/A")
            subject = item.get("eventName", "N/A")
            p_date = format_date(item.get("publishDate"))
            e_date = format_date(item.get("endDate"))
            t_url = f"https://etender.gov.az/main/competition/detail/{event_id}"

            row = [kw, event_id, org, subject, p_date, e_date, t_url]
            new_rows.append(row)
            existing_ids.add(event_id)

            msg = (
                f"🔔 <b>YENİ TENDER TAPILDI!</b>\n\n"
                f"🔑 <b>Keyword:</b> <code>{kw}</code>\n\n"
                f"🏢 <b>Təşkilat:</b>\n{org}\n\n"
                f"📋 <b>Satınalma predmeti:</b>\n{subject}\n\n"
                f"📅 <b>Dərc tarixi:</b> {p_date}\n"
                f"⏰ <b>Bitmə tarixi:</b> {e_date}\n\n"
                f"🔗 <a href='{t_url}'>Ətraflı bax</a>\n"
                f"━━━━━━━━━━━━━━\n"
                f"🤖 E-Tender Monitor"
            )

            send_telegram_message(msg)
            print(f"Göndərildi: {event_id} - {subject[:50]}")

    if new_rows:
        sheet.append_rows(new_rows)
        print(f"✅ {len(new_rows)} yeni tender Sheets-ə əlavə olundu.")
    else:
        print("ℹ️ Yeni tender tapılmadı.")

if __name__ == "__main__":
    main()
