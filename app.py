import streamlit as st
import datetime
import re
import unicodedata
import requests
import json
import base64
from difflib import SequenceMatcher
import google.generativeai as genai
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from streamlit_oauth import OAuth2Component
from supabase import create_client, Client

# =========================================================
# 1. إعدادات النظام وقاعدة البيانات (CONFIGURATION)
# =========================================================

st.set_page_config(page_title="akin yurt AI", page_icon="🏰", layout="centered")

class AppConfig:
    # قائمة المعرفة للبحث في ويكيبيديا
    TOPICS = {
        "AR": [
            "كركوك", "التركمان العراقيون", "تركمان ايلي", "قلعة كركوك", "التون كوبري", 
            "الدولة العثمانية", "السلاجقة", "أذربيجان", "طوزخورماتو", "تلعفر", 
            "مجزرة كركوك 1959", "الجبهة التركمانية العراقية"
        ],
        "TR": [
            "Kerkük", "Irak Türkmenleri", "Türkmeneli", "Kerkük Kalesi", "Altunköprü", 
            "Osmanlı İmparatorluğu", "Selçuklu", "Azerbaycan", "Tuzhurmatu", "Telafer"
        ],
        "EN": [
            "Kirkuk", "Iraqi Turkmens", "Turkmeneli", "Kirkuk Citadel", "Altun Kupri", 
            "Ottoman Empire", "Seljuk Empire", "Azerbaijan", "Tuz Khurmatu", "Tal Afar"
        ]
    }

    @staticmethod
    def init_supabase():
        """تهيئة الاتصال بقاعدة بيانات Supabase"""
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            return create_client(url, key)
        except Exception:
            return None

# تهيئة متغير قاعدة البيانات
db: Client = AppConfig.init_supabase()

# =========================================================
# 2. طبقة الحماية والتشفير (SECURITY LAYER)
# =========================================================

class CryptoManager:
    def __init__(self):
        # محاولة جلب مفتاح التشفير من الأسرار
        if "encryption_key" in st.secrets:
            try:
                self.key = bytes.fromhex(st.secrets["encryption_key"])
            except ValueError:
                self.key = get_random_bytes(32)
        else:
            self.key = get_random_bytes(32)

    def encrypt(self, raw_text):
        """تشفير النص باستخدام AES-256"""
        try:
            cipher = AES.new(self.key, AES.MODE_CBC)
            ct_bytes = cipher.encrypt(pad(raw_text.encode('utf-8'), AES.block_size))
            return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')
        except: return ""

# =========================================================
# 3. إدارة المستخدمين (USER MANAGEMENT)
# =========================================================

class UserManager:
    def __init__(self):
        self.crypto = CryptoManager()

    def social_login_check(self, email):
        """التعامل مع مستخدمي Google"""
        if not db: return False
        try:
            response = db.table("users").select("username").eq("username", email).execute()
            if not response.data:
                # إنشاء حساب جديد لمستخدم جوجل بكلمة مرور عشوائية مشفرة لحفظ المستخدم في القاعدة فقط
                dummy_pass = self.crypto.encrypt("GOOGLE_AUTH_" + base64.b64encode(get_random_bytes(8)).decode())
                db.table("users").insert({"username": email, "password_hash": dummy_pass}).execute()
            return True
        except: return False

# =========================================================
# 4. منطق الذكاء والبحث (CHAT INTELLIGENCE)
# =========================================================

class ChatModel:
    def __init__(self):
        # جلب المفتاح تلقائياً من ملف الأسرار بدلاً من إدخاله يدوياً
        try:
            self.api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=self.api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        except Exception:
            self.api_key = None
            st.error("⚠️ لم يتم العثور على GEMINI_API_KEY في ملف secrets.toml")

    def normalize_text(self, text):
        text = text.strip()
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"http\S+|www\.\S+", "", text).strip()

    def guess_lang(self, text):
        if any('\u0600' <= c <= '\u06FF' for c in text): return "ar"
        if any(c in "çğıöşüÇĞİÖŞÜ" for c in text): return "tr"
        return "en"

    def save_interaction(self, user, q, a, source):
        """حفظ المحادثة في Supabase"""
        if db:
            try:
                db.table("chat_history").insert({
                    "username": user,
                    "question": self.normalize_text(q),
                    "answer": a,
                    "source": source
                }).execute()
            except Exception as e:
                print(f"Error saving chat: {e}")

    def search_db_history(self, query):
        if not db: return None
        try:
            q_norm = self.normalize_text(query)
            response = db.table("chat_history").select("answer").ilike("question", f"%{q_norm}%").limit(1).execute()
            if response.data:
                return response.data[0]["answer"]
        except: pass
        return None

    def search_wikipedia(self, query, lang):
        topics = AppConfig.TOPICS["AR"] if lang == "ar" else AppConfig.TOPICS["TR"] if lang == "tr" else AppConfig.TOPICS["EN"]
        best_topic, score = None, 0
        
        for t in topics:
            sc = SequenceMatcher(None, query.lower(), t.lower()).ratio()
            if sc > score: best_topic, score = t, sc
            
        if score >= 0.70:
            try:
                url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{best_topic.replace(' ', '%20')}"
                r = requests.get(url, timeout=3)
                if r.status_code == 200:
                    return r.json().get("extract"), f"Wikipedia ({best_topic})"
            except: pass
        return None, None

    def ask_gemini(self, query):
        if not self.api_key: return "⚠️ خطأ في إعدادات النظام (API Key missing)."
        try:
            return self.gemini_model.generate_content(query).text.strip()
        except Exception as e: return f"Error: {e}"

# =========================================================
# 5. واجهة المستخدم (UI & MAIN LOGIC)
# =========================================================

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "messages" not in st.session_state: st.session_state.messages = []

auth_manager = UserManager()

def handle_google_login():
    """معالجة زر الدخول عبر جوجل"""
    if "google" not in st.secrets:
        st.warning("⚠️ إعدادات Google غير موجودة في secrets.toml")
        return

    oauth2 = OAuth2Component(
        st.secrets["google"]["client_id"],
        st.secrets["google"]["client_secret"],
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        "https://oauth2.googleapis.com/token",
        "https://oauth2.googleapis.com/revoke"
    )
    
    result = oauth2.authorize_button(
        name="الدخول باستخدام Google",
        icon="https://www.google.com.tw/favicon.ico",
        redirect_uri=st.secrets["google"]["redirect_uri"],
        scope="email profile",
        key="google_auth_btn"
    )

    if result:
        try:
            id_token = result.get("token", {}).get("id_token")
            part = id_token.split(".")[1]
            part += "=" * ((4 - len(part) % 4) % 4)
            decoded = base64.b64decode(part).decode("utf-8")
            user_info = json.loads(decoded)
            email = user_info.get("email")
            
            if email:
                auth_manager.social_login_check(email)
                st.session_state.logged_in = True
                st.session_state.username = email
                st.rerun()
        except Exception as e:
            st.error(f"فشل الدخول: {e}")

def login_page():
    st.title("🏰 بوابة الدخول - Turkmeneli AI")
    st.markdown("---")
    
    if not db:
        st.error("⚠️ خطأ: لم يتم الاتصال بقاعدة البيانات. تأكد من إعداد Secrets.")
    
    # تم حذف التسجيل المحلي، والإبقاء على خيار جوجل فقط
    st.subheader("🌐 تسجيل الدخول")
    st.write("مرحباً بك، يرجى تسجيل الدخول للمتابعة:")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        handle_google_login()
        
        # خيار "زائر" إذا أردت السماح بالدخول بدون جوجل (اختياري - يمكنك حذفه)
        st.markdown("---")
        if st.button("دخول كضيف (بدون حفظ السجل)", use_container_width=True):
             st.session_state.logged_in = True
             st.session_state.username = "Guest_User"
             st.rerun()

def chat_interface():
    # القائمة الجانبية
    with st.sidebar:
        st.title("👤 الملف الشخصي")
        st.write(f"المستخدم: **{st.session_state.username}**")
        st.markdown("---")
        # تم حذف حقل إدخال Gemini Key من هنا
        
        if st.button("تسجيل الخروج"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        st.caption("Status: Connected to Supabase 🟢")

    # واجهة الدردشة الرئيسية
    st.title("🤖 Turkmeneli AI Chatbot")
    st.caption("نظام محادثة مدعوم بذاكرة سحابية وذكاء اصطناعي")

    # تهيئة الموديل (سيجلب المفتاح تلقائياً)
    model = ChatModel()

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "source" in m: st.caption(f"المصدر: {m['source']}")

    if q := st.chat_input("اسأل عن تاريخ كركوك، أو أي موضوع آخر..."):
        st.session_state.messages.append({"role": "user", "content": q})
        st.chat_message("user").markdown(q)

        ans, src = "", ""
        lang = model.guess_lang(q)

        # 3. دورة البحث (Pipeline)
        with st.spinner("جاري البحث في الذاكرة..."):
            db_ans = model.search_db_history(q)
            if db_ans:
                ans, src = db_ans, "Cloud Memory (Supabase)"
        
        if not ans:
            with st.spinner("جاري البحث في المصادر المفتوحة..."):
                wiki_ans, topic = model.search_wikipedia(model.normalize_text(q), lang)
                if wiki_ans:
                    ans, src = wiki_ans, f"Wikipedia ({topic})"
        
        if not ans:
            with st.spinner("جاري التفكير (Gemini AI)..."):
                gemini_resp = model.ask_gemini(q)
                ans, src = gemini_resp, "Gemini AI"

        if ans and "Error" not in ans and "مفتاح" not in ans and st.session_state.username != "Guest_User":
            model.save_interaction(st.session_state.username, q, ans, src)

        st.session_state.messages.append({"role": "assistant", "content": ans, "source": src})
        with st.chat_message("assistant"):
            st.markdown(ans)
            st.caption(f"المصدر: {src}")

if __name__ == "__main__":
    if st.session_state.logged_in:
        chat_interface()
    else:
        login_page()

