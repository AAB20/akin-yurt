import streamlit as st
import re
import unicodedata
import requests
import json
import base64
import google.generativeai as genai
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
from streamlit_oauth import OAuth2Component
from supabase import create_client, Client

# =========================================================
# 1. إعدادات النظام والتصميم (CONFIGURATION & STYLE)
# =========================================================

st.set_page_config(
    page_title="Akın Yurt AI", 
    page_icon="🏰", 
    layout="wide", # تخطيط واسع للتصميم الاحترافي
    initial_sidebar_state="expanded"
)

# --- CSS مخصص لتحسين الواجهة وجعلها احترافية ---
def apply_custom_css():
    st.markdown("""
        <style>
        /* استيراد خط عربي عصري من جوجل (Cairo) */
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Cairo', sans-serif;
        }

        /* خلفية التطبيق */
        .stApp {
            background-color: #f8f9fa;
        }

        /* تخصيص القائمة الجانبية */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e0e0e0;
            box-shadow: 2px 0 5px rgba(0,0,0,0.02);
        }

        /* تحسين مظهر الأزرار */
        div.stButton > button {
            background-color: #0056b3;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 2rem;
            font-weight: 600;
            font-size: 16px;
            transition: all 0.3s ease;
            width: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        div.stButton > button:hover {
            background-color: #004494;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }

        /* تخصيص فقاعات المحادثة */
        .stChatMessage {
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            margin-bottom: 15px;
            border: 1px solid #f0f0f0;
        }
        
        /* تمييز رسالة المستخدم عن المساعد */
        [data-testid="stChatMessage"][data-testid="user-message"] {
            background-color: #eef5fc;
        }

        /* تحسين حقل الإدخال */
        .stChatInputContainer {
            padding-bottom: 20px;
        }
        .stChatInputContainer textarea {
            border-radius: 12px;
            border: 1px solid #ddd;
        }

        /* تصميم بطاقة تسجيل الدخول */
        .login-card {
            background-color: white;
            padding: 3rem;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
            text-align: center;
            margin-top: 2rem;
        }
        .login-header {
            color: #1a1a1a;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .login-sub {
            color: #666;
            margin-bottom: 2rem;
        }
        
        /* إخفاء القوائم الافتراضية */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

apply_custom_css()

class AppConfig:
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
        if "encryption_key" in st.secrets:
            try:
                self.key = bytes.fromhex(st.secrets["encryption_key"])
            except ValueError:
                self.key = get_random_bytes(32)
        else:
            self.key = get_random_bytes(32)

    def encrypt(self, raw_text):
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
        if not db: return False
        try:
            response = db.table("users").select("username").eq("username", email).execute()
            if not response.data:
                dummy_pass = self.crypto.encrypt("GOOGLE_AUTH_" + base64.b64encode(get_random_bytes(8)).decode())
                db.table("users").insert({"username": email, "password_hash": dummy_pass}).execute()
            return True
        except: return False

# =========================================================
# 4. منطق الذكاء والبحث (CHAT INTELLIGENCE)
# =========================================================

class ChatModel:
    def __init__(self):
        try:
            self.api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=self.api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        except Exception:
            self.api_key = None

    def normalize_text(self, text):
        text = text.strip()
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"http\S+|www\.\S+", "", text).strip()

    def guess_lang(self, text):
        if any('\u0600' <= c <= '\u06FF' for c in text): return "ar"
        if any(c in "çğıöşüÇĞİÖŞÜ" for c in text): return "tr"
        return "en"

    def save_interaction(self, user, q, a, source):
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
        """بحث ديناميكي في ويكيبيديا"""
        try:
            search_url = f"https://{lang}.wikipedia.org/w/api.php"
            search_params = {
                "action": "query", "format": "json", "list": "search", "srsearch": query, "srlimit": 1
            }
            search_response = requests.get(search_url, params=search_params, timeout=3)
            search_data = search_response.json()
            
            if "query" in search_data and "search" in search_data["query"]:
                results = search_data["query"]["search"]
                if results:
                    best_title = results[0]["title"]
                    summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{best_title}"
                    summary_response = requests.get(summary_url, timeout=3)
                    
                    if summary_response.status_code == 200:
                        data = summary_response.json()
                        extract = data.get("extract")
                        if extract:
                            return extract, f"Wikipedia ({best_title})"
        except Exception: pass
        return None, None

    def ask_gemini(self, query):
        if not self.api_key: return "⚠️ عذراً، الخدمة متوقفة مؤقتاً للصيانة (API Key)."
        try:
            return self.gemini_model.generate_content(query).text.strip()
        except Exception as e: return f"حدث خطأ غير متوقع: {e}"

# =========================================================
# 5. واجهة المستخدم (UI & MAIN LOGIC)
# =========================================================

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "messages" not in st.session_state: st.session_state.messages = []

auth_manager = UserManager()

def handle_google_login():
    if "google" not in st.secrets:
        st.warning("⚠️ إعدادات Google مفقودة")
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
        name="تسجيل الدخول عبر Google",
        icon="https://www.google.com/favicon.ico",
        redirect_uri=st.secrets["google"]["redirect_uri"],
        scope="email profile",
        key="google_auth_btn",
        use_container_width=True
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
        except Exception:
            st.error("فشل تسجيل الدخول، يرجى المحاولة مرة أخرى.")

def login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("""
            <div class='login-card'>
                <div style='font-size: 60px; margin-bottom: 10px;'>🏰</div>
                <h1 class='login-header'>Akın Yurt AI</h1>
                <p class='login-sub'>منصتك الذكية للبحث والمعرفة التاريخية</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        if not db:
            st.error("⚠️ تعذر الاتصال بقاعدة البيانات")
        
        handle_google_login()
        
        st.markdown("<div style='text-align: center; margin: 15px 0; color: #999;'>— أو —</div>", unsafe_allow_html=True)
        
        if st.button("متابعة كزائر", use_container_width=True):
             st.session_state.logged_in = True
             st.session_state.username = "Guest_User"
             st.rerun()
             
        st.markdown("""
            <div style='margin-top: 30px; font-size: 12px; color: #bbb; text-align: center;'>
                © 2024 Turkmeneli AI Platform. All rights reserved.
            </div>
        """, unsafe_allow_html=True)

def chat_interface():
    # --- Sidebar ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
        st.markdown(f"""
            <div style='margin-bottom: 20px;'>
                <h3 style='margin: 0; color: #333;'>الملف الشخصي</h3>
                <p style='color: #666; font-size: 14px;'>{st.session_state.username}</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### ⚙️ أدوات التحكم")
        if st.button("🗑️ مسح المحادثة", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        if st.button("تسجيل الخروج", key="logout_btn", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("""
            <div style='font-size: 12px; color: #888;'>
                Connected to <b>Supabase</b> 🟢<br>
                Powered by <b>Gemini 2.0</b> ⚡
            </div>
        """, unsafe_allow_html=True)

    # --- Main Chat Area ---
    col_main, _ = st.columns([8, 1])
    
    with col_main:
        st.markdown("""
            <h2 style='color: #0056b3; font-weight: 700;'>مرحباً بك في المساعد الذكي 👋</h2>
            <p style='color: #666;'>اسأل عن التاريخ، الجغرافيا، أو أي معلومة عامة.</p>
        """, unsafe_allow_html=True)

    model = ChatModel()

    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.messages:
            st.info("💡 ابدأ المحادثة بسؤال مثل: 'ما هو تاريخ قلعة كركوك؟'")
            
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if "source" in m:
                    st.markdown(f"<div style='font-size: 11px; color: #888; margin-top: 5px;'>مصدر المعلومات: {m['source']}</div>", unsafe_allow_html=True)

    if q := st.chat_input("اكتب سؤالك هنا..."):
        st.session_state.messages.append({"role": "user", "content": q})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(q)

        ans, src = "", ""
        lang = model.guess_lang(q)

        with st.status("جاري المعالجة والبحث...", expanded=True) as status:
            
            # 1. Memory Check
            status.write("🔍 البحث في الأرشيف السحابي...")
            db_ans = model.search_db_history(q)
            if db_ans:
                ans, src = db_ans, "Cloud Memory (Supabase)"
                status.update(label="تم العثور على الإجابة في الذاكرة!", state="complete", expanded=False)
            
            # 2. Wikipedia Search
            if not ans:
                status.write("🌐 البحث في المصادر المفتوحة (Wikipedia)...")
                wiki_ans, topic = model.search_wikipedia(model.normalize_text(q), lang)
                if wiki_ans:
                    ans, src = wiki_ans, topic
                    status.update(label="تم جلب المعلومات من ويكيبيديا", state="complete", expanded=False)
            
            # 3. Gemini AI
            if not ans:
                status.write("🧠 تحليل السؤال بواسطة Gemini AI...")
                gemini_resp = model.ask_gemini(q)
                ans, src = gemini_resp, "Gemini AI"
                status.update(label="تم التوليد بواسطة الذكاء الاصطناعي", state="complete", expanded=False)

        if ans and "Error" not in ans and st.session_state.username != "Guest_User":
            model.save_interaction(st.session_state.username, q, ans, src)

        st.session_state.messages.append({"role": "assistant", "content": ans, "source": src})
        
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(ans)
                st.markdown(f"<div style='font-size: 11px; color: #0056b3; margin-top: 5px;'>مصدر المعلومات: {src}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    if st.session_state.logged_in:
        chat_interface()
    else:
        login_page()
