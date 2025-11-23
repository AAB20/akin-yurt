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

# تهيئة متغيرات الجلسة الجديدة
if "language" not in st.session_state: st.session_state.language = "AR"
if "theme" not in st.session_state: st.session_state.theme = "Light"
if "history_loaded" not in st.session_state: st.session_state.history_loaded = []

# قاموس الترجمة للنصوص الثابتة
UI_TEXT = {
    "AR": {
        "title": "Akın Yurt AI",
        "subtitle": "منصتك الذكية للبحث والمعرفة التاريخية",
        "login_google": "تسجيل الدخول عبر Google",
        "guest_login": "متابعة كزائر",
        "or": "— أو —",
        "welcome_chat": "مرحباً بك في المساعد الذكي 👋",
        "desc_chat": "اسأل عن التاريخ، الجغرافيا، أو أي معلومة عامة.",
        "profile": "الملف الشخصي",
        "settings": "⚙️ الإعدادات",
        "language": "اللغة / Language",
        "theme": "المظهر / Theme",
        "clear_chat": "🗑️ مسح المحادثة الحالية",
        "logout": "تسجيل الخروج",
        "history_title": "📜 سجل المحادثات السابقة",
        "input_placeholder": "اكتب سؤالك هنا...",
        "status_memory": "🔍 البحث في الأرشيف السحابي...",
        "status_wiki": "🌐 البحث في المصادر المفتوحة (Wikipedia) + تلخيص ذكي...",
        "status_found_mem": "تم العثور على الإجابة في الذاكرة!",
        "status_found_wiki": "تم جلب وتلخيص المعلومات من ويكيبيديا",
        "status_ai": "تم التوليد بواسطة الذكاء الاصطناعي",
        "source": "المصدر",
        "rights": "© 2024 Turkmeneli AI Platform. All rights reserved.",
        "login_error": "فشل تسجيل الدخول، يرجى المحاولة مرة أخرى.",
        "db_error": "⚠️ تعذر الاتصال بقاعدة البيانات"
    },
    "TR": {
        "title": "Akın Yurt YZ",
        "subtitle": "Tarihsel bilgi ve araştırma için akıllı platformunuz",
        "login_google": "Google ile Giriş Yap",
        "guest_login": "Misafir olarak devam et",
        "or": "— veya —",
        "welcome_chat": "Akıllı Asistana Hoş Geldiniz 👋",
        "desc_chat": "Tarih, coğrafya veya genel bilgiler hakkında sorun.",
        "profile": "Profil",
        "settings": "⚙️ Ayarlar",
        "language": "Dil / Language",
        "theme": "Tema / Theme",
        "clear_chat": "🗑️ Sohbeti Temizle",
        "logout": "Çıkış Yap",
        "history_title": "📜 Geçmiş Sohbetler",
        "input_placeholder": "Sorunuzu buraya yazın...",
        "status_memory": "🔍 Bulut Arşivinde Aranıyor...",
        "status_wiki": "🌐 Açık Kaynaklarda Arama (Wikipedia) + Akıllı Özet...",
        "status_found_mem": "Cevap hafızada bulundu!",
        "status_found_wiki": "Bilgiler Wikipedia'dan alındı ve özetlendi",
        "status_ai": "Yapay Zeka tarafından oluşturuldu",
        "source": "Kaynak",
        "rights": "© 2024 Türkmeneli YZ Platformu. Tüm hakları saklıdır.",
        "login_error": "Giriş başarısız, lütfen tekrar deneyin.",
        "db_error": "⚠️ Veritabanına bağlanılamadı"
    },
    "EN": {
        "title": "Akın Yurt AI",
        "subtitle": "Your intelligent platform for historical research",
        "login_google": "Login with Google",
        "guest_login": "Continue as Guest",
        "or": "— or —",
        "welcome_chat": "Welcome to AI Assistant 👋",
        "desc_chat": "Ask about history, geography, or general knowledge.",
        "profile": "Profile",
        "settings": "⚙️ Settings",
        "language": "Language / Dil",
        "theme": "Theme / Tema",
        "clear_chat": "🗑️ Clear Chat",
        "logout": "Logout",
        "history_title": "📜 Previous Conversations",
        "input_placeholder": "Type your question here...",
        "status_memory": "🔍 Searching Cloud Archive...",
        "status_wiki": "🌐 Searching Open Source (Wikipedia) + Smart Summary...",
        "status_found_mem": "Answer found in memory!",
        "status_found_wiki": "Information fetched & summarized from Wikipedia",
        "status_ai": "Generated by AI",
        "source": "Source",
        "rights": "© 2024 Turkmeneli AI Platform. All rights reserved.",
        "login_error": "Login failed, please try again.",
        "db_error": "⚠️ Unable to connect to database"
    }
}

def get_text(key):
    return UI_TEXT[st.session_state.language][key]

# --- CSS مخصص (ديناميكي حسب الثيم) ---
def apply_custom_css():
    # تحديد الألوان بناءً على الثيم المختار
    is_dark = st.session_state.theme == "Dark"
    
    bg_color = "#121212" if is_dark else "#f8f9fa"
    sidebar_bg = "#1E1E1E" if is_dark else "#ffffff"
    text_color = "#E0E0E0" if is_dark else "#212529"
    card_bg = "#2D2D2D" if is_dark else "#ffffff"
    border_color = "#404040" if is_dark else "#e0e0e0"
    user_msg_bg = "#3a3a3a" if is_dark else "#eef5fc"
    bot_msg_bg = "#2D2D2D" if is_dark else "#ffffff"
    input_bg = "#2D2D2D" if is_dark else "#ffffff"
    
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Cairo', sans-serif;
            color: {text_color};
        }}

        .stApp {{
            background-color: {bg_color};
        }}

        /* تخصيص القائمة الجانبية */
        section[data-testid="stSidebar"] {{
            background-color: {sidebar_bg};
            border-right: 1px solid {border_color};
        }}

        div.stButton > button {{
            background-color: #0056b3;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 2rem;
            font-weight: 600;
            font-size: 16px;
            width: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        div.stButton > button:hover {{
            background-color: #004494;
        }}

        /* تخصيص فقاعات المحادثة */
        .stChatMessage {{
            background-color: {bot_msg_bg};
            border-radius: 15px;
            margin-bottom: 15px;
            border: 1px solid {border_color};
        }}
        
        [data-testid="stChatMessage"][data-testid="user-message"] {{
            background-color: {user_msg_bg};
            border: none;
        }}

        /* حقل الإدخال */
        .stChatInputContainer textarea {{
            border-radius: 12px;
            border: 1px solid {border_color};
            background-color: {input_bg};
            color: {text_color};
        }}

        /* بطاقة الدخول */
        .login-card {{
            background-color: {card_bg};
            padding: 3rem;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            text-align: center;
            margin-top: 2rem;
            border: 1px solid {border_color};
        }}
        .login-header {{
            color: {text_color};
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .login-sub {{
            color: #888;
            margin-bottom: 2rem;
        }}
        
        /* نصوص القوائم */
        .stSelectbox label, .stRadio label {{
            color: {text_color};
        }}
        
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
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
        """جلب سجل محادثات المستخدم من قاعدة البيانات"""
        if not db or not username or username == "Guest_User": return []
        try:
            # جلب آخر 10 محادثات
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
            You are a summarization engine. Summarize the provided text based on the query.
            Constraint: Use ONLY provided text. Keep same language. Be concise.
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
                        source_suffix = " ⭐ (Verified Topic)" if is_priority_topic else ""
                        return final_answer, f"Wikipedia ({target_title}){source_suffix}"
                
                if is_priority_topic:
                    return "عذراً، هذا الموضوع موجود ضمن القائمة المعتمدة ولكن تعذر جلب المحتوى من ويكيبيديا حالياً.", "Wikipedia (Error)"
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
    # إضافة خيار تغيير اللغة والثيم في صفحة الدخول أيضاً
    with st.sidebar:
        st.selectbox("Language / اللغة", ["AR", "EN", "TR"], key="lang_select_login", 
                     index=["AR", "EN", "TR"].index(st.session_state.language),
                     on_change=lambda: st.session_state.update({"language": st.session_state.lang_select_login}))
        st.radio("Theme", ["Light", "Dark"], key="theme_select_login",
                 index=["Light", "Dark"].index(st.session_state.theme),
                 on_change=lambda: st.session_state.update({"theme": st.session_state.theme_select_login}))

    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown(f"""
            <div class='login-card'>
                <div style='font-size: 60px; margin-bottom: 10px;'>🏰</div>
                <h1 class='login-header'>{get_text("title")}</h1>
                <p class='login-sub'>{get_text("subtitle")}</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        if not db:
            st.error(get_text("db_error"))
        
        handle_google_login()
        
        st.markdown(f"<div style='text-align: center; margin: 15px 0; color: #999;'>{get_text('or')}</div>", unsafe_allow_html=True)
        
        if st.button(get_text("guest_login"), use_container_width=True):
             st.session_state.logged_in = True
             st.session_state.username = "Guest_User"
             st.rerun()
             
        st.markdown(f"""
            <div style='margin-top: 30px; font-size: 12px; color: #bbb; text-align: center;'>
                {get_text('rights')}
            </div>
        """, unsafe_allow_html=True)

def chat_interface():
    # --- Sidebar ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
        
        # قسم الإعدادات (لغة وثيم)
        st.markdown(f"### {get_text('settings')}")
        
        col_l, col_t = st.columns(2)
        with col_l:
            selected_lang = st.selectbox("Lang", ["AR", "EN", "TR"], 
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

        st.markdown("---")
        
        # قسم الملف الشخصي
        st.markdown(f"### {get_text('profile')}")
        st.write(f"👤 {st.session_state.username}")
        
        if st.button(get_text("clear_chat"), use_container_width=True):
            st.session_state.messages = []
            st.rerun()
            
        if st.button(get_text("logout"), key="logout_btn", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.rerun()
        
        # قسم سجل المحادثات
        if st.session_state.username != "Guest_User":
            st.markdown("---")
            st.markdown(f"### {get_text('history_title')}")
            
            # جلب السجل مرة واحدة عند التحميل لتجنب البطء
            if not st.session_state.history_loaded:
                 st.session_state.history_loaded = auth_manager.get_user_history(st.session_state.username)
            
            history_data = st.session_state.history_loaded
            
            if history_data:
                for item in history_data:
                    # قص السؤال الطويل
                    q_short = (item['question'][:30] + '..') if len(item['question']) > 30 else item['question']
                    with st.expander(f"📅 {item.get('created_at', '')[:10]} - {q_short}"):
                        st.write(f"**Q:** {item['question']}")
                        st.write(f"**A:** {item['answer']}")
                        st.caption(f"{get_text('source')}: {item['source']}")
            else:
                st.caption("No history available.")
            
            if st.button("🔄 Refresh History", key="refresh_hist"):
                st.session_state.history_loaded = auth_manager.get_user_history(st.session_state.username)
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
        st.markdown(f"""
            <h2 style='color: #0056b3; font-weight: 700;'>{get_text('welcome_chat')}</h2>
            <p style='color: #666;'>{get_text('desc_chat')}</p>
        """, unsafe_allow_html=True)

    model = ChatModel()
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.messages:
            pass
            
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if "source" in m:
                    st.markdown(f"<div style='font-size: 11px; color: #888; margin-top: 5px;'>{get_text('source')}: {m['source']}</div>", unsafe_allow_html=True)

    if q := st.chat_input(get_text("input_placeholder")):
        st.session_state.messages.append({"role": "user", "content": q})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(q)

        ans, src = "", ""
        lang_query = model.guess_lang(q)

        with st.status(get_text("status_memory").replace("...", ""), expanded=True) as status:
            
            # 1. Memory Check
            status.write(get_text("status_memory"))
            db_ans = model.search_db_history(q)
            if db_ans:
                ans, src = db_ans, "Cloud Memory (Supabase)"
                status.update(label=get_text("status_found_mem"), state="complete", expanded=False)
            
            # 2. Wikipedia Search + Smart Summarization
            if not ans:
                status.write(get_text("status_wiki"))
                wiki_ans, topic = model.search_wikipedia(model.normalize_text(q), lang_query)
                if wiki_ans:
                    ans, src = wiki_ans, topic
                    status.update(label=get_text("status_found_wiki"), state="complete", expanded=False)
            
            # 3. Gemini AI
            if not ans:
                gemini_resp = model.ask_gemini(q)
                ans, src = gemini_resp, "Gemini AI"
                status.update(label=get_text("status_ai"), state="complete", expanded=False)

        if ans and "Error" not in ans and st.session_state.username != "Guest_User":
            model.save_interaction(st.session_state.username, q, ans, src)
            # تحديث السجل محلياً لإظهار المحادثة الجديدة فوراً في القائمة الجانبية عند الضغط على تحديث
            st.session_state.history_loaded = [] 

        st.session_state.messages.append({"role": "assistant", "content": ans, "source": src})
        
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(ans)
                st.markdown(f"<div style='font-size: 11px; color: #0056b3; margin-top: 5px;'>{get_text('source')}: {src}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    if st.session_state.logged_in:
        chat_interface()
    else:
        login_page()
