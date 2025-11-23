import streamlit as st
import re
import unicodedata
import requests
import json
import base64
import google.generativeai as genai
from difflib import SequenceMatcher
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
from streamlit_oauth import OAuth2Component
from supabase import create_client, Client

# =========================================================
# 1. إعدادات الجلسة والترجمة (SESSION & TRANSLATION)
# =========================================================

st.set_page_config(
    page_title="Akın Yurt AI", 
    page_icon="🏰", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# تهيئة متغيرات الجلسة
if "language" not in st.session_state: st.session_state.language = "AR"
if "theme" not in st.session_state: st.session_state.theme = "Light"
if "history_loaded" not in st.session_state: st.session_state.history_loaded = []

# قاموس الترجمة
UI_TEXT = {
    "AR": {
        "title": "Akın Yurt AI",
        "subtitle": "الذكاء المعرفي للمستقبل",
        "login_google": "المتابعة باستخدام Google",
        "guest_login": "تجربة كزائر",
        "or": "أو",
        "welcome_chat": "مرحباً",
        "desc_chat": "كيف يمكنني مساعدتك في استكشاف التاريخ اليوم؟",
        "profile": "الحساب",
        "settings": "تفضيلات العرض",
        "language": "اللغة",
        "theme": "المظهر",
        "clear_chat": "محو الذاكرة المؤقتة",
        "logout": "إنهاء الجلسة",
        "history_title": "الأرشيف",
        "input_placeholder": "اسأل شيئاً...",
        "status_memory": "جاري استرجاع البيانات...",
        "status_wiki": "تحليل المصادر المفتوحة...",
        "status_found_mem": "تم الاسترجاع من الذاكرة",
        "status_found_wiki": "تم التوثيق عبر ويكيبيديا",
        "status_ai": "تمت المعالجة بواسطة AI",
        "source": "المصدر",
        "rights": "© 2025 Akın Yurt Technologies.",
        "login_error": "فشل المصادقة.",
        "db_error": "النظام غير متصل"
    },
    "TR": {
        "title": "Akın Yurt AI",
        "subtitle": "Geleceğin Bilişsel Zekası",
        "login_google": "Google ile Devam Et",
        "guest_login": "Misafir Girişi",
        "or": "veya",
        "welcome_chat": "Merhaba",
        "desc_chat": "Bugün tarihi keşfetmenize nasıl yardımcı olabilirim?",
        "profile": "Hesap",
        "settings": "Tercihler",
        "language": "Dil",
        "theme": "Tema",
        "clear_chat": "Önbelleği Temizle",
        "logout": "Oturumu Kapat",
        "history_title": "Arşiv",
        "input_placeholder": "Bir şeyler sorun...",
        "status_memory": "Veri alınıyor...",
        "status_wiki": "Açık kaynak analizi...",
        "status_found_mem": "Hafızadan alındı",
        "status_found_wiki": "Wikipedia üzerinden doğrulandı",
        "status_ai": "YZ tarafından işlendi",
        "source": "Kaynak",
        "rights": "© 2025 Akın Yurt Technologies.",
        "login_error": "Kimlik doğrulama başarısız.",
        "db_error": "Sistem çevrimdışı"
    },
    "EN": {
        "title": "Akın Yurt AI",
        "subtitle": "Cognitive Intelligence for the Future",
        "login_google": "Continue with Google",
        "guest_login": "Try as Guest",
        "or": "or",
        "welcome_chat": "Hello",
        "desc_chat": "How can I assist you in exploring history today?",
        "profile": "Account",
        "settings": "Preferences",
        "language": "Language",
        "theme": "Theme",
        "clear_chat": "Clear Cache",
        "logout": "Sign Out",
        "history_title": "Archive",
        "input_placeholder": "Ask anything...",
        "status_memory": "Retrieving data...",
        "status_wiki": "Analyzing open sources...",
        "status_found_mem": "Retrieved from memory",
        "status_found_wiki": "Verified via Wikipedia",
        "status_ai": "Processed by AI",
        "source": "Source",
        "rights": "© 2025 Akın Yurt Technologies.",
        "login_error": "Authentication failed.",
        "db_error": "System offline"
    }
}

def get_text(key):
    return UI_TEXT[st.session_state.language][key]

# --- CSS "Trillion Dollar" Design System ---
def apply_custom_css():
    is_dark = st.session_state.theme == "Dark"
    
    # تحديد الألوان بدقة: أسود كامل للفاتح، أبيض كامل للداكن
    if is_dark:
        bg_color = "#000000"
        sec_bg_color = "#111111"
        text_color = "#FFFFFF"      # أبيض نقي
        sub_text_color = "#DDDDDD"  # أبيض مائل للرمادي قليلاً للتمييز
        border_color = "#333333"
        input_bg = "#1A1A1A"
        card_bg = "#111111"
        button_bg = "#FFFFFF"
        button_text = "#000000"     # نص الزر عكس الخلفية
        user_msg_bg = "#1A1A1A"
        shadow = "0 4px 20px rgba(0,0,0,0.5)"
    else:
        bg_color = "#FFFFFF"
        sec_bg_color = "#FAFAFA"
        text_color = "#000000"      # أسود نقي
        sub_text_color = "#333333"  # رمادي غامق جداً للتمييز
        border_color = "#EAEAEA"
        input_bg = "#FFFFFF"
        card_bg = "#FFFFFF"
        button_bg = "#000000"
        button_text = "#FFFFFF"     # نص الزر عكس الخلفية
        user_msg_bg = "#FAFAFA"
        shadow = "0 10px 40px rgba(0,0,0,0.04)"

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;700&family=Inter:wght@300;400;600&display=swap');

        /* --- Global Typography Enforcement --- */
        html, body, [class*="css"], .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, span, div, label, li {{
            font-family: 'Inter', 'Cairo', sans-serif;
            color: {text_color} !important; /* فرض اللون المختار على جميع النصوص */
            -webkit-font-smoothing: antialiased;
        }}

        /* Reset Elements */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* --- Layout & Backgrounds --- */
        .stApp {{
            background-color: {bg_color};
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: {sec_bg_color};
            border-right: 1px solid {border_color};
        }}
        
        /* Sidebar Headers Specific Override */
        section[data-testid="stSidebar"] h3 {{
            color: {text_color} !important;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.8;
        }}

        /* --- Buttons (High Contrast) --- */
        div.stButton > button {{
            background-color: {button_bg} !important;
            color: {button_text} !important; /* لون نص الزر معاكس للخلفية */
            border: 1px solid {button_bg};
            border-radius: 8px;
            padding: 0.6rem 1.5rem;
            font-weight: 500;
            box-shadow: none;
            transition: transform 0.1s;
        }}
        div.stButton > button:hover {{
            opacity: 0.9;
            transform: scale(0.99);
        }}
        div.stButton > button:active {{
            transform: scale(0.97);
        }}

        /* --- Inputs & Text Areas --- */
        .stTextInput input, 
        .stSelectbox div[data-baseweb="select"] > div, 
        .stChatInputContainer textarea {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border: 1px solid {border_color} !important;
            border-radius: 8px;
        }}
        
        /* Dropdown Menu Items */
        ul[data-baseweb="menu"] li, ul[data-baseweb="menu"] span {{
            color: {text_color} !important;
        }}

        /* --- Login Card --- */
        .login-card {{
            background-color: {card_bg};
            padding: 3rem 4rem;
            border-radius: 24px;
            border: 1px solid {border_color};
            box-shadow: {shadow};
            text-align: center;
        }}
        .login-header {{
            color: {text_color} !important;
        }}
        .login-sub {{
            color: {sub_text_color} !important;
        }}

        /* --- Chat Bubbles --- */
        [data-testid="stChatMessage"][data-testid="user-message"] {{
            background-color: {user_msg_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
        }}
        
        /* Expanders */
        .streamlit-expanderHeader {{
            color: {text_color} !important;
            background-color: transparent !important;
        }}
        
        /* Status Widget Text */
        div[data-testid="stStatusWidget"] div {{
             color: {text_color} !important;
        }}
        </style>
    """, unsafe_allow_html=True)

apply_custom_css()

class AppConfig:
    TOPICS = {
        "AR": [
            "كركوك", "التركمان العراقيون", "تركمان ايلي", "قلعة كركوك", "التون كوبري", 
            "الدولة العثمانية", "السلاجقة", "أذربيجان", "طوزخورماتو", "تلعفر", 
            "مجزرة كركوك 1959", "الجبهة التركمانية العراقية", "العراق"
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
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            return create_client(url, key)
        except Exception:
            return None

db: Client = AppConfig.init_supabase()

# =========================================================
# 2. طبقة الحماية والتشفير
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
# 3. إدارة المستخدمين
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
        
    def get_user_history(self, username):
        if not db or not username or username == "Guest_User": return []
        try:
            response = db.table("chat_history")\
                .select("*")\
                .eq("username", username)\
                .order("created_at", desc=True)\
                .limit(10)\
                .execute()
            return response.data
        except Exception:
            return []

# =========================================================
# 4. منطق الذكاء والبحث
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

    def smart_summarize(self, text, query):
        if len(text) < 300: return text
        if not self.api_key: return text
        try:
            prompt = f"""
            You are an elite summarization engine. Summarize the provided text based strictly on the query.
            Constraint: Use ONLY provided text. Keep same language. Be extremely concise and professional.
            User Query: {query}
            Source Text: {text}
            """
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception: return text

    def search_wikipedia(self, query, lang):
        try:
            target_title = None
            is_priority_topic = False
            topics = AppConfig.TOPICS.get(lang.upper(), [])
            
            for topic in topics:
                if topic.lower() in query.lower():
                    target_title = topic
                    is_priority_topic = True
                    break
                if SequenceMatcher(None, query.lower(), topic.lower()).ratio() > 0.8:
                    target_title = topic
                    is_priority_topic = True
                    break

            if not target_title:
                search_url = f"https://{lang}.wikipedia.org/w/api.php"
                search_params = {"action": "query", "format": "json", "list": "search", "srsearch": query, "srlimit": 1}
                search_response = requests.get(search_url, params=search_params, timeout=3)
                search_data = search_response.json()
                if "query" in search_data and "search" in search_data["query"]:
                    results = search_data["query"]["search"]
                    if results: target_title = results[0]["title"]

            if target_title:
                safe_title = target_title.replace(" ", "_")
                summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
                summary_response = requests.get(summary_url, timeout=3)
                if summary_response.status_code == 200:
                    data = summary_response.json()
                    extract = data.get("extract")
                    if extract:
                        final_answer = self.smart_summarize(extract, query)
                        source_suffix = " ⭐" if is_priority_topic else ""
                        return final_answer, f"Wikipedia ({target_title}){source_suffix}"
        except Exception: pass
        return None, None

    def ask_gemini(self, query):
        if not self.api_key: return "⚠️ API Key Missing"
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
    if "google" not in st.secrets:
        st.warning("⚠️ Google secrets missing")
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
        name=get_text("login_google"),
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
            st.error(get_text("login_error"))

def login_page():
    # تصميم صفحة الدخول: مركزي، بسيط، راقي جداً
    with st.sidebar:
        # إخفاء عناصر الشريط الجانبي في صفحة الدخول لتركيز الانتباه
        pass 

    # استخدام حاوية مركزية عبر الأعمدة
    _, col_center, _ = st.columns([1, 2, 1])
    
    with col_center:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class='login-card'>
                <div class='login-logo'>🏰</div>
                <h1 class='login-header'>{get_text("title")}</h1>
                <p class='login-sub'>{get_text("subtitle")}</p>
        """, unsafe_allow_html=True)
        
        if not db:
            st.error(get_text("db_error"))
        
        handle_google_login()
        
        st.markdown(f"<div style='font-size: 12px; margin: 20px 0;'>{get_text('or')}</div>", unsafe_allow_html=True)
        
        if st.button(get_text("guest_login"), use_container_width=True):
             st.session_state.logged_in = True
             st.session_state.username = "Guest_User"
             st.rerun()
             
        st.markdown(f"""
            <div style='margin-top: 40px; font-size: 11px; opacity: 0.7; letter-spacing: 0.5px;'>
                {get_text('rights')}
            </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # أدوات التحكم في الأسفل بشكل خفي
    st.markdown("---")
    c1, c2, c3 = st.columns([10, 1, 1])
    with c2:
        st.selectbox("Lang", ["AR", "EN", "TR"], key="lang_select_login", 
                 index=["AR", "EN", "TR"].index(st.session_state.language),
                 on_change=lambda: st.session_state.update({"language": st.session_state.lang_select_login}),
                 label_visibility="collapsed")
    with c3:
        st.selectbox("Theme", ["Light", "Dark"], key="theme_select_login",
                 index=["Light", "Dark"].index(st.session_state.theme),
                 on_change=lambda: st.session_state.update({"theme": st.session_state.theme_select_login}),
                 label_visibility="collapsed")

def chat_interface():
    # --- Sidebar: Minimalist Navigation ---
    with st.sidebar:
        st.markdown(f"<div style='font-size: 24px; font-weight: 700; margin-bottom: 20px;'>🏰 Akın Yurt</div>", unsafe_allow_html=True)
        
        st.markdown(f"<h3>{get_text('settings')}</h3>", unsafe_allow_html=True)
        col_l, col_t = st.columns(2)
        with col_l:
            selected_lang = st.selectbox("Language", ["AR", "EN", "TR"], 
                                       index=["AR", "EN", "TR"].index(st.session_state.language),
                                       label_visibility="collapsed")
            if selected_lang != st.session_state.language:
                st.session_state.language = selected_lang
                st.rerun()
        
        with col_t:
            selected_theme = st.selectbox("Theme", ["Light", "Dark"], 
                                        index=["Light", "Dark"].index(st.session_state.theme),
                                        label_visibility="collapsed")
            if selected_theme != st.session_state.theme:
                st.session_state.theme = selected_theme
                st.rerun()

        st.markdown(f"<h3>{get_text('profile')}</h3>", unsafe_allow_html=True)
        st.caption(st.session_state.username)
        
        if st.button(get_text("clear_chat")):
            st.session_state.messages = []
            st.rerun()
            
        if st.button(get_text("logout"), key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.rerun()
        
        # History
        if st.session_state.username != "Guest_User":
            st.markdown(f"<div style='margin-top: 30px;'><h3>{get_text('history_title')}</h3></div>", unsafe_allow_html=True)
            
            if not st.session_state.history_loaded:
                 st.session_state.history_loaded = auth_manager.get_user_history(st.session_state.username)
            
            history_data = st.session_state.history_loaded
            
            if history_data:
                for item in history_data:
                    q_short = (item['question'][:25] + '..') if len(item['question']) > 25 else item['question']
                    with st.expander(f"{q_short}"):
                        st.write(item['answer'])
            
            if st.button("↻", key="refresh_hist"):
                st.session_state.history_loaded = auth_manager.get_user_history(st.session_state.username)
                st.rerun()

    # --- Main Chat Area: Clean & Spacious ---
    
    # Header area (Clean text only)
    st.markdown(f"""
        <div style='margin-bottom: 3rem;'>
            <h1 style='font-size: 2.5rem; font-weight: 700; letter-spacing: -1px;'>{get_text('welcome_chat')}</h1>
            <p style='font-size: 1.1rem; opacity: 0.7; font-weight: 300;'>{get_text('desc_chat')}</p>
        </div>
    """, unsafe_allow_html=True)

    model = ChatModel()
    chat_container = st.container()
    
    with chat_container:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if "source" in m:
                    st.caption(f"{get_text('source')}: {m['source']}")

    if q := st.chat_input(get_text("input_placeholder")):
        st.session_state.messages.append({"role": "user", "content": q})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(q)

        ans, src = "", ""
        lang_query = model.guess_lang(q)

        # Status: Minimalist & fast
        with st.status(get_text("status_memory"), expanded=True) as status:
            
            db_ans = model.search_db_history(q)
            if db_ans:
                ans, src = db_ans, "Cloud Memory"
                status.update(label=get_text("status_found_mem"), state="complete", expanded=False)
            
            if not ans:
                status.write(get_text("status_wiki"))
                wiki_ans, topic = model.search_wikipedia(model.normalize_text(q), lang_query)
                if wiki_ans:
                    ans, src = wiki_ans, topic
                    status.update(label=get_text("status_found_wiki"), state="complete", expanded=False)
            
            if not ans:
                gemini_resp = model.ask_gemini(q)
                ans, src = gemini_resp, "AI Model"
                status.update(label=get_text("status_ai"), state="complete", expanded=False)

        if ans and "Error" not in ans and st.session_state.username != "Guest_User":
            model.save_interaction(st.session_state.username, q, ans, src)
            st.session_state.history_loaded = [] 

        st.session_state.messages.append({"role": "assistant", "content": ans, "source": src})
        st.rerun()

if __name__ == "__main__":
    if st.session_state.logged_in:
        chat_interface()
    else:
        login_page()
