import os

import requests

# مهم جداً: كان مفتاح OneSignal REST API ومعرّف التطبيق مكتوبين مباشرة في الكود
# وتم رفعهما إلى مستودع GitHub عام — هذا يعني أنهما مخترقان بالفعل ويجب إبطالهما
# (regenerate) فوراً من لوحة تحكم OneSignal بغض النظر عن هذا التعديل، ثم وضع
# القيم الجديدة فقط كمتغيرات بيئة (لا تُكتب في الكود ولا تُرفع إلى git).
ONESIGNAL_APP_ID = os.environ.get("ONESIGNAL_APP_ID")
ONESIGNAL_API_KEY = os.environ.get("ONESIGNAL_API_KEY")


def send_notification(title, message, segments=["All"]):
    if not ONESIGNAL_APP_ID or not ONESIGNAL_API_KEY:
        return {"error": "ONESIGNAL_APP_ID / ONESIGNAL_API_KEY غير مضبوطتين في متغيرات البيئة."}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {ONESIGNAL_API_KEY}",
    }

    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": segments,  # يمكنك تخصيصها لاحقًا
        "headings": {
            "en": title,
            "ar": title
        },
        "contents": {
            "en": message,
            "ar": message
        }
    }

    try:
        response = requests.post(
            "https://onesignal.com/api/v1/notifications",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
