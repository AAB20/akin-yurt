import streamlit as st
import re
import unicodedata
import requests
import json
import base64
import time
import google.generativeai as genai
from difflib import SequenceMatcher
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
from streamlit_oauth import OAuth2Component
from supabase import create_client, Client

# =========================================================
# 1. إعدادات الجلسة (SESSION CONFIG)
# =========================================================

st.set_page_config(
    page_title="Akın Yurt AI", 
    page_icon="🤖", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# تهيئة متغيرات الجلسة
if "language" not in st.session_state: st.session_state.language = "AR"
if "theme" not in st.session_state: st.session_state.theme = "Dark" # الوضع الافتراضي داكن مثل ChatGPT
if "history_loaded" not in st.session_state: st.session_state.history_loaded = []

# =========================================================
# 2. الترجمة والنصوص (LOCALIZATION)
# =========================================================

UI_TEXT = {
    "AR": {
        "new_chat": "محادثة جديدة",
        "welcome_chat": "كيف يمكنني مساعدتك اليوم؟",
        "login_google": "المتابعة باستخدام Google",
        "guest_login": "الدخول كزائر",
        "input_placeholder": "أرسل رسالة...",
        "settings": "الإعدادات",
        "logout": "تسجيل الخروج",
        "history": "اليوم",
        "rights": "UI Design © 2025 Akın Yurt.",
        "source": "المصدر",
        "think_start": "جاري التفكير...",
        "think_identity": "التحقق من بروتوكولات الهوية...",
        "think_memory": "البحث في الذاكرة السحابية...",
        "think_wiki": "تحليل المصادر المفتوحة...",
        "think_ai": "المعالجة وتوليد الإجابة (Gemini)...",
        "think_done": "تمت المعالجة"
    },
    "TR": {
        "new_chat": "Yeni Sohbet",
        "welcome_chat": "Bugün size nasıl yardımcı olabilirim?",
        "login_google": "Google ile Devam Et",
        "guest_login": "Misafir Girişi",
        "input_placeholder": "Bir mesaj gönder...",
        "settings": "Ayarlar",
        "logout": "Çıkış Yap",
        "history": "Bugün",
        "rights": "UI Design © 2025 Akın Yurt.",
        "source": "Kaynak",
        "think_start": "Düşünülüyor...",
        "think_identity": "Kimlik protokolleri kontrol ediliyor...",
        "think_memory": "Bulut hafıza taranıyor...",
        "think_wiki": "Açık kaynaklar analiz ediliyor...",
        "think_ai": "İşleniyor ve Cevap Üretiliyor (Gemini)...",
        "think_done": "Tamamlandı"
    },
    "EN": {
        "new_chat": "New Chat",
        "welcome_chat": "How can I help you today?",
        "login_google": "Continue with Google",
        "guest_login": "Guest Login",
        "input_placeholder": "Send a message...",
        "settings": "Settings",
        "logout": "Log out",
        "history": "Today",
        "rights": "UI Design © 2025 Akın Yurt.",
        "source": "Source",
        "think_start": "Thinking...",
        "think_identity": "Checking identity protocols...",
        "think_memory": "Searching Knowledge Base...",
        "think_wiki": "Analyzing open sources...",
        "think_ai": "Processing & Generating (Gemini)...",
        "think_done": "Finished"
    }
}

def get_text(key):
    return UI_TEXT[st.session_state.language][key]

# =========================================================
# 3. تصميم CHATGPT (CSS STYLING)
# =========================================================

def apply_chatgpt_style():
    is_dark = st.session_state.theme == "Dark"
    
    if is_dark:
        bg_color = "#343541"
        sidebar_bg = "#202123"
        input_bg = "#40414F"
        text_color = "#ECECF1"
        border_color = "#565869"
        user_msg_bg = "#343541"
        bot_msg_bg = "#444654"
        btn_hover = "#2A2B32"
        scroll_thumb = "#565869"
    else:
        bg_color = "#FFFFFF"
        sidebar_bg = "#F9F9F9"
        input_bg = "#FFFFFF"
        text_color = "#343541"
        border_color = "#D9D9E3"
        user_msg_bg = "#FFFFFF"
        bot_msg_bg = "#F7F7F8"
        btn_hover = "#ECECF1"
        scroll_thumb = "#D9D9E3"

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Cairo:wght@400;600&display=swap');

        /* إعدادات الخطوط والألوان العامة */
        html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, div {{
            font-family: 'Inter', 'Cairo', sans-serif;
            color: {text_color} !important;
            background-color: {bg_color};
        }}

        /* إخفاء عناصر ستريم ليت الافتراضية */
        header {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* تنسيق الشريط الجانبي */
        section[data-testid="stSidebar"] {{
            background-color: {sidebar_bg};
            border-right: 1px solid {border_color}30;
        }}
        
        /* زر محادثة جديدة */
        .new-chat-btn {{
            border: 1px solid {border_color};
            border-radius: 5px;
            padding: 10px 15px;
            text-align: left;
            transition: background 0.2s;
            cursor: pointer;
            margin-bottom: 20px;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: {text_color};
        }}
        .new-chat-btn:hover {{
            background-color: {btn_hover};
        }}

        /* تنسيق منطقة المحادثة */
        .stApp {{
            background-color: {bg_color};
        }}
        
        .stChatMessage {{
            background-color: transparent !important;
            border: none !important;
            padding: 1.5rem 0 !important;
            margin: 0 !important;
        }}
        
        div[data-testid="stChatMessage"]:nth-child(even) {{
            background-color: {bot_msg_bg} !important;
        }}
        
        div[data-testid="stChatMessage"]:nth-child(odd) {{
            background-color: {user_msg_bg} !important;
        }}

        .stChatMessage .stAvatar {{
            background-color: { " #19c37d" if is_dark else "#10a37f" };
            color: white;
            border-radius: 2px;
        }}

        /* تنسيق حقل الإدخال */
        .stChatInputContainer {{
            background-color: {bg_color} !important;
            padding-bottom: 20px !important;
        }}
        .stChatInputContainer textarea {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border: 1px solid {border_color} !important;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
            border-radius: 12px;
            padding: 12px 15px;
            font-size: 1rem;
        }}
        .stChatInputContainer textarea:focus {{
            border-color: #8e8ea0 !important;
            box-shadow: none !important;
        }}

        /* تنسيق الأزرار */
        div.stButton > button {{
            background-color: transparent !important;
            color: {text_color} !important;
            border: 1px solid {border_color} !important;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        div.stButton > button:hover {{
            background-color: {btn_hover} !important;
        }}

        /* تنسيق شاشة الدخول */
        .login-wrapper {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 80vh;
            flex-direction: column;
        }}
        .login-box {{
            background-color: {sidebar_bg};
            padding: 40px;
            border-radius: 5px;
            width: 350px;
            text-align: center;
            border: 1px solid {border_color};
        }}
        
        /* تنسيق عنصر حالة التفكير */
        div[data-testid="stStatusWidget"] {{
            border: 1px solid {border_color};
            background-color: {input_bg};
            color: {text_color};
            border-radius: 8px;
        }}
        
        /* شريط التمرير */
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {scroll_thumb}; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #888; }}

        </style>
    """, unsafe_allow_html=True)

apply_chatgpt_style()

class AppConfig:
    # قائمة المواضيع ذات الأولوية في البحث
    TOPICS = {
        "AR": ["كركوك", "التركمان العراقيون", "تركمان ايلي", "قلعة كركوك", "التون كوبري", "الدولة العثمانية", "السلاجقة", "أذربيجان", "طوزخورماتو", "تلعفر", "مجزرة كركوك 1959", "الجبهة التركمانية العراقية", "العراق"],
        "TR": ["Kerkük", "Irak Türkmenleri", "Türkmeneli", "Kerkük Kalesi", "Altunköprü", "Osmanlı İmparatorluğu", "Selçuklu", "Azerbaycan", "Tuzhurmatu", "Telafer"],
        "EN": ["Kirkuk", "Iraqi Turkmens", "Turkmeneli", "Kirkuk Citadel", "Altun Kupri", "Ottoman Empire", "Seljuk Empire", "Azerbaijan", "Tuz Khurmatu", "Tal Afar"]
    }

    @staticmethod
    def init_supabase():
        try:
            return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        except: return None

db: Client = AppConfig.init_supabase()

# =========================================================
# 4. الأمن والمستخدمين (Logic)
# =========================================================

class CryptoManager:
    def __init__(self):
        if "encryption_key" in st.secrets:
            try:
                self.key = bytes.fromhex(st.secrets["encryption_key"])
            except:
                self.key = get_random_bytes(32)
        else:
            self.key = get_random_bytes(32)

    def encrypt(self, raw_text):
        try:
            cipher = AES.new(self.key, AES.MODE_CBC)
            ct_bytes = cipher.encrypt(pad(raw_text.encode('utf-8'), AES.block_size))
            return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')
        except: return ""

class UserManager:
    def __init__(self):
        self.crypto = CryptoManager()

    def social_login_check(self, email):
        if not db: return False
        try:
            response = db.table("users").select("username").eq("username", email).execute()
            if not response.data:
                dummy_pass = self.crypto.encrypt("GOOGLE_" + base64.b64encode(get_random_bytes(8)).decode())
                db.table("users").insert({"username": email, "password_hash": dummy_pass}).execute()
            return True
        except: return False
        
    def get_user_history(self, username):
        if not db or not username or username == "Guest_User": return []
        try:
            return db.table("chat_history").select("*").eq("username", username).order("created_at", desc=True).limit(15).execute().data
        except: return []

# =========================================================
# 5. منطق الذكاء (Core AI) - نظام تدوير المفاتيح (Key Rotation)
# =========================================================

class ChatModel:
    def __init__(self):
        # تحميل جميع المفاتيح المتاحة
        self.api_keys = self._load_api_keys()
        
    def _load_api_keys(self):
        """تحميل قائمة المفاتيح من الأسرار"""
        keys = []
        # المفتاح الرئيسي
        if "GEMINI_API_KEY" in st.secrets:
            keys.append(st.secrets["GEMINI_API_KEY"])
            
        # المفاتيح الاحتياطية (1 إلى 10)
        for i in range(1, 11):
            key_name = f"GEMINI_API_KEY_{i}"
            if key_name in st.secrets:
                keys.append(st.secrets[key_name])
                
        return keys

    def _run_gemini_query(self, prompt):
        """تشغيل الاستعلام مع تدوير المفاتيح تلقائياً عند الفشل"""
        if not self.api_keys:
            raise Exception("API Keys Missing")

        last_error = None
        # تجربة المفاتيح واحداً تلو الآخر
        for i, key in enumerate(self.api_keys):
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                last_error = e
                # يمكن إضافة طباعة هنا لأغراض التصحيح: print(f"Key {i} failed, switching to next...")
                continue
        
        # إذا فشلت جميع المفاتيح
        raise last_error

    def normalize_text(self, text):
        return re.sub(r"http\S+|www\.\S+", "", unicodedata.normalize("NFKC", text.strip())).strip()

    def guess_lang(self, text):
        if any('\u0600' <= c <= '\u06FF' for c in text): return "ar"
        if any(c in "çğıöşüÇĞİÖŞÜ" for c in text): return "tr"
        return "en"

    def save_interaction(self, user, q, a, source):
        if db:
            try:
                db.table("chat_history").insert({"username": user, "question": self.normalize_text(q), "answer": a, "source": source}).execute()
            except: pass

    def check_identity_query(self, query):
        q_clean = query.lower().strip()
        identity_keywords = ["من انت", "من تكون", "عرف بنفسك", "ما اسمك", "sen kimsin", "kimsin", "kendini tanıt", "adın ne", "who are you", "what is your name"]
        if any(k in q_clean for k in identity_keywords):
            return """Akın Yurt, Türkmen gençlerinin bilgi birikimi, teknik becerisi ve milli bilinciyle geliştirilen yeni nesil bir yapay zekâ simülasyonudur. O, sadece bir yazılım projesi değil; Türkmen gençlerinin dijital dünyada var olma iradesinin güçlü bir yansımasıdır.

Akın Yurt’un algoritmaları; gelişmiş analiz kabiliyeti, sürekli öğrenme yeteneği ve insani değerlere duyarlı bir yapay zekâ mimarisi üzerine kuruludur. Onun amacı yalnızca bilgi sunmak veya sorulara yanıt vermek değil; toplumunun kültürüne, kimliğine ve geleceğine değer katacak dijital bir yol arkadaşı olmaktır.

Genç Türkmen zekâları tarafından geliştirilen bu model:
• Toplumsal gelişime destek olmayı,
• Eğitim, kültür, teknoloji ve medya alanlarında kullanıcıları güçlendirmeyi,
• Bilgiyi doğru, hızlı ve etik şekilde sunmayı,
• Gençlerin üretim gücünü artırmayı,
• Dijital Türkmen zekâsının simgesi olmayı
hedeflemektedir.

Akın Yurt, kendisini sadece bir yapay sistem olarak değil; Türkmen gençliğinin vizyonunun dijital bir yansıması, düşünce gücünün teknolojik bir temsilcisi olarak konumlandırır.

Her etkileşimle öğrenen, gelişen ve kullanıcılarıyla birlikte büyüyen bir yapıya sahiptir.
Gücünü kodlarından değil, onu geliştiren gençlerin hayallerinden alır.

Akın Yurt — bir yazılım değil, bir vizyonun dijital geleceğidir."""
        return None

    def search_db_history(self, query):
        if not db: return None
        try:
            q_norm = self.normalize_text(query)
            response = db.table("chat_history").select("answer").ilike("question", f"%{q_norm}%").limit(1).execute()
            return response.data[0]["answer"] if response.data else None
        except: return None

    def smart_summarize(self, text, query):
        """التلخيص الذكي باستخدام Gemini (مع دعم تعدد المفاتيح)"""
        if len(text) < 300 or not self.api_keys: return text
        try:
            prompt = f"""
            You are a helpful assistant. Summarize this text based on the query: {query}.
            Keep the language same as the text.
            Text: {text}
            """
            return self._run_gemini_query(prompt)
        except: return text

    def search_wikipedia(self, query, lang):
        try:
            target_title = None
            is_priority = False
            topics = AppConfig.TOPICS.get(lang.upper(), [])
            
            # البحث أولاً في قائمة الأولويات
            for topic in topics:
                if topic.lower() in query.lower() or SequenceMatcher(None, query.lower(), topic.lower()).ratio() > 0.8:
                    target_title, is_priority = topic, True
                    break

            # إذا لم نجد، نبحث في API ويكيبيديا
            if not target_title:
                res = requests.get(f"https://{lang}.wikipedia.org/w/api.php", params={"action": "query", "format": "json", "list": "search", "srsearch": query, "srlimit": 1}, timeout=3).json()
                if res.get("query", {}).get("search"): target_title = res["query"]["search"][0]["title"]

            # جلب المحتوى والتلخيص
            if target_title:
                res = requests.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{target_title.replace(' ', '_')}", timeout=3)
                if res.status_code == 200 and res.json().get("extract"):
                    return self.smart_summarize(res.json()["extract"], query), f"Wikipedia ({target_title})" + (" ⭐" if is_priority else "")
        except: pass
        return None, None

    def ask_gemini(self, query):
        if not self.api_keys: return "⚠️ API Keys Missing. Please update secrets.toml"
        try: 
            return self._run_gemini_query(query)
        except Exception as e: return f"Error (All keys failed): {e}"

# =========================================================
# 6. الواجهة (UI & Views)
# =========================================================

auth_manager = UserManager()

def login_page():
    # تصميم صفحة الدخول البسيطة والمركزية
    st.markdown("<div class='login-wrapper'>", unsafe_allow_html=True)
    st.markdown(f"<div class='login-box'>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='font-size: 30px; margin-bottom: 20px;'>🤖</h2>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-bottom: 30px;'>Welcome to Akın Yurt</h3>", unsafe_allow_html=True)
    
    # Google Login
    if "google" in st.secrets:
        oauth2 = OAuth2Component(st.secrets["google"]["client_id"], st.secrets["google"]["client_secret"], "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/revoke")
        result = oauth2.authorize_button(name=get_text("login_google"), icon="https://www.google.com/favicon.ico", redirect_uri=st.secrets["google"]["redirect_uri"], scope="email profile", key="google_auth_btn", use_container_width=True)
        if result:
            try:
                # فك تشفير التوكن للحصول على الإيميل
                email = json.loads(base64.b64decode(result["token"]["id_token"].split(".")[1] + "==").decode("utf-8")).get("email")
                if email:
                    auth_manager.social_login_check(email)
                    st.session_state.logged_in = True
                    st.session_state.username = email
                    st.rerun()
            except: st.error("Login failed")

    st.markdown("<div style='margin: 15px 0; border-top: 1px solid #555;'></div>", unsafe_allow_html=True)
    
    # Guest Login
    if st.button(get_text("guest_login"), use_container_width=True):
        st.session_state.logged_in, st.session_state.username = True, "Guest_User"
        st.rerun()

    # إعدادات اللغة والثيم السفلية
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Lang", ["AR", "EN", "TR"], key="lang_login", on_change=lambda: st.session_state.update({"language": st.session_state.lang_login}))
    with c2:
        st.selectbox("Theme", ["Dark", "Light"], key="theme_login", on_change=lambda: st.session_state.update({"theme": st.session_state.theme_login}))

    st.markdown("</div></div>", unsafe_allow_html=True)

def chat_interface():
    # --- Sidebar ---
    with st.sidebar:
        # زر محادثة جديدة
        if st.button(f"➕ {get_text('new_chat')}", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
            
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.caption(get_text("history"))

        # قائمة السجل
        if st.session_state.username != "Guest_User":
            if not st.session_state.history_loaded:
                 st.session_state.history_loaded = auth_manager.get_user_history(st.session_state.username)
            
            for item in st.session_state.history_loaded:
                title = item['question'][:20] + "..." if len(item['question']) > 20 else item['question']
                if st.button(f"💬 {title}", key=f"hist_{item['id']}", use_container_width=True):
                    pass # يمكن إضافة كود لاسترجاع المحادثة هنا

        st.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True) 
        st.markdown("---")
        
        # إعدادات المستخدم السفلية
        with st.expander(f"👤 {st.session_state.username}"):
            st.selectbox("🌐 Language", ["AR", "EN", "TR"], key="lang_main", index=["AR", "EN", "TR"].index(st.session_state.language), on_change=lambda: st.session_state.update({"language": st.session_state.lang_main}))
            st.selectbox("🌓 Theme", ["Dark", "Light"], key="theme_main", index=["Dark", "Light"].index(st.session_state.theme), on_change=lambda: st.session_state.update({"theme": st.session_state.theme_main}))
            if st.button(get_text("logout")):
                st.session_state.logged_in = False
                st.rerun()

    # --- Main Chat Area ---
    model = ChatModel()

    # شاشة الترحيب (تظهر فقط عند عدم وجود رسائل)
    if not st.session_state.messages:
        _, col_c, _ = st.columns([1, 2, 1])
        with col_c:
            st.markdown(f"""
                <div style='text-align: center; margin-top: 20vh; color: { "#ECECF1" if st.session_state.theme == "Dark" else "#343541" };'>
                    <div style='font-size: 72px; margin-bottom: 20px;'>🤖</div>
                    <h2 style='font-weight: 600;'>Akın Yurt</h2>
                    <p style='font-size: 18px; opacity: 0.8;'>{get_text('welcome_chat')}</p>
                </div>
            """, unsafe_allow_html=True)

    # عرض الرسائل
    for m in st.session_state.messages:
        with st.chat_message(m["role"], avatar="👤" if m["role"] == "user" else "🤖"):
            st.markdown(m["content"])
            if "source" in m: st.caption(f"{get_text('source')}: {m['source']}")

    # حقل الإدخال
    if q := st.chat_input(get_text("input_placeholder")):
        st.session_state.messages.append({"role": "user", "content": q})
        st.rerun()

    # معالجة الرسالة الأخيرة
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        q = st.session_state.messages[-1]["content"]
        
        with st.chat_message("assistant", avatar="🤖"):
            # --- THINKING BLOCK (عرض خطوات التفكير) ---
            with st.status(get_text("think_start"), expanded=True) as status:
                
                lang_query = model.guess_lang(q)
                ans, src = "", ""

                # 0: التحقق من الهوية
                status.write(get_text("think_identity"))
                identity = model.check_identity_query(q)
                if identity:
                    ans, src = identity, "Akın Yurt Core"
                
                # 1: البحث في الذاكرة
                if not ans:
                    status.write(get_text("think_memory"))
                    db_ans = model.search_db_history(q)
                    if db_ans: ans, src = db_ans, "Memory"
                
                # 2: البحث في ويكيبيديا
                if not ans:
                    status.write(get_text("think_wiki"))
                    wiki_ans, topic = model.search_wikipedia(model.normalize_text(q), lang_query)
                    if wiki_ans: ans, src = wiki_ans, topic
                
                # 3: التوليد باستخدام الذكاء الاصطناعي (مع تدوير المفاتيح)
                if not ans:
                    status.write(get_text("think_ai"))
                    ans = model.ask_gemini(q)
                    src = "Gemini AI"
                
                status.update(label=get_text("think_done"), state="complete", expanded=False)
            
            # عرض الإجابة النهائية
            st.markdown(ans)
            st.caption(f"{get_text('source')}: {src}")
            
            if st.session_state.username != "Guest_User":
                model.save_interaction(st.session_state.username, q, ans, src)
                st.session_state.history_loaded = [] 

            st.session_state.messages.append({"role": "assistant", "content": ans, "source": src})

if __name__ == "__main__":
    if st.session_state.logged_in:
        chat_interface()
    else:
        login_page()
