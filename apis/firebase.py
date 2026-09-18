import logging
import os

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# مهم جداً: كان ملف مفتاح حساب خدمة Firebase (firebase_admin_sdk.json) مرفوعاً
# مباشرة داخل مستودع GitHub عام. هذا المفتاح مخترق بالفعل ويجب إبطاله فوراً من
# Google Cloud Console (IAM > Service Accounts > حذف هذا المفتاح وإصدار مفتاح
# جديد) بغض النظر عن هذا التعديل. لا تُعِد رفع أي ملف مفتاح إلى git بعد الآن —
# استخدم متغير بيئة FIREBASE_CREDENTIALS_PATH يشير إلى الملف على الخادم، أو
# FIREBASE_CREDENTIALS_JSON يحتوي محتوى JSON نفسه كسر (كما تفعل معظم منصات
# النشر مثل Render/Heroku عبر "Secret Files").
FIREBASE_KEY_PATH = os.environ.get(
    "FIREBASE_CREDENTIALS_PATH",
    os.path.join(BASE_DIR, "apis", "firebase_admin_sdk.json"),
)
FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if not firebase_admin._apps:
    try:
        if FIREBASE_CREDENTIALS_JSON:
            import json
            cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
        elif os.path.exists(FIREBASE_KEY_PATH):
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
        else:
            cred = None
            logger.error(
                "لم يتم العثور على بيانات اعتماد Firebase. اضبط FIREBASE_CREDENTIALS_PATH "
                "أو FIREBASE_CREDENTIALS_JSON كمتغير بيئة."
            )
        if cred is not None:
            firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("❌ فشل تهيئة Firebase Admin SDK")
