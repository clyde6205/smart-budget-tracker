"""
Annual Smart Budget Tracker — Enterprise Multi-User Edition
=============================================================

A multi-tenant Streamlit personal & business finance platform, gated by
license keys, with automatic refund-triggered account suspension (via
the companion webhook_receiver.py for Gumroad), self-service password
reset, and a multi-language interface.

See README.md for full setup: Postgres, SMTP, admin access, license key
generation, and deploying the Gumroad webhook receiver.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import json
import io
import secrets
import smtplib
from email.mime.text import MIMEText
import sqlalchemy as sa
import streamlit.components.v1 as components

try:
    import anthropic
    ANTHROPIC_SDK_AVAILABLE = True
except ImportError:
    ANTHROPIC_SDK_AVAILABLE = False

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    import pyotp
    import qrcode
    import io as _io_qr
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

try:
    import plaid
    from plaid.api import plaid_api
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.transactions_sync_request import TransactionsSyncRequest
    from plaid.model.item_remove_request import ItemRemoveRequest
    PLAID_SDK_AVAILABLE = True
except ImportError:
    PLAID_SDK_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# ---------------------------------------------------------------------------
# PAGE CONFIG & STYLE
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Annual Smart Budget Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = {
    "navy": "#1A2530", "card_bg": "#F8F9FA", "border": "#E2E8F0",
    "green": "#137333", "red": "#C5221F", "blue": "#1A73E8", "gold": "#B8860B",
}

st.markdown(
    f"""
    <style>
        .main {{ background-color: #FFFFFF; }}
        div[data-testid="stMetric"] {{
            background-color: {PALETTE['card_bg']};
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
            padding: 14px 16px;
        }}
        div[data-testid="stMetricLabel"] {{ font-size: 12px; color: #4A5568; }}
        h1, h2, h3 {{ color: {PALETTE['navy']}; }}
        .stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
        .app-header {{
            background-color: {PALETTE['navy']}; color: white;
            padding: 18px 24px; border-radius: 10px; margin-bottom: 14px;
        }}
        .mode-badge {{
            display: inline-block; padding: 3px 12px; border-radius: 999px;
            font-size: 12px; font-weight: 700; background-color: {PALETTE['gold']};
            color: white; margin-left: 10px;
        }}
        .ai-badge {{
            display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 11px; font-weight: 700; background-color: {PALETTE['blue']};
            color: white;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------------------------------
# Covers the core navigation, login/signup, and dashboard experience — the
# screens every user sees regardless of how deep they go into the app.
# Deeper/rarer screens (category text-editor, Admin tab) remain English
# pending a fuller localization pass; see README for details on scope.
LANGUAGES = {
    "en": "English", "es": "Español", "hi": "हिन्दी", "fil": "Filipino",
    "pt": "Português", "fr": "Français", "id": "Bahasa Indonesia",
    "ar": "العربية", "zh": "中文（简体）", "de": "Deutsch",
}

TRANSLATIONS = {
    "en": {
        "app_title": "Annual Smart Budget Tracker",
        "tab_dashboard": "📊 Dashboard", "tab_transactions": "💳 Transactions Log",
        "tab_budget": "📅 Monthly Budget", "tab_debt": "🧊 Debt Calculator",
        "tab_networth": "📈 Net Worth", "tab_setup": "⚙️ Setup & Account",
        "tab_admin": "🛡️ Admin",
        "book_personal": "🏠 Personal", "book_business": "💼 Business",
        "welcome_back": "Welcome back, {username}",
        "budget_year": "Budget Year", "payday": "Payday",
        "login_tab": "🔑 Log In", "signup_tab": "✨ Create Account", "forgot_tab": "❓ Forgot Password",
        "username_label": "Username", "password_label": "Password", "email_label": "Email",
        "login_button": "Log In", "signup_button": "Create Account", "logout_button": "Log Out",
        "starting_balance": "Starting Balance", "total_income": "Total Income",
        "total_expenses": "Total Expenses", "current_balance": "Current Balance",
        "language_label": "🌐 Language",
        "incorrect_login": "Incorrect username or password.",
        "account_suspended": "This account has been suspended. Contact support if you believe this is a mistake.",
    },
    "es": {
        "app_title": "Rastreador Inteligente de Presupuesto Anual",
        "tab_dashboard": "📊 Panel", "tab_transactions": "💳 Registro de Transacciones",
        "tab_budget": "📅 Presupuesto Mensual", "tab_debt": "🧊 Calculadora de Deudas",
        "tab_networth": "📈 Patrimonio Neto", "tab_setup": "⚙️ Configuración y Cuenta",
        "tab_admin": "🛡️ Administración",
        "book_personal": "🏠 Personal", "book_business": "💼 Negocio",
        "welcome_back": "Bienvenido de nuevo, {username}",
        "budget_year": "Año Presupuestario", "payday": "Día de Pago",
        "login_tab": "🔑 Iniciar Sesión", "signup_tab": "✨ Crear Cuenta", "forgot_tab": "❓ Olvidé mi Contraseña",
        "username_label": "Usuario", "password_label": "Contraseña", "email_label": "Correo Electrónico",
        "login_button": "Iniciar Sesión", "signup_button": "Crear Cuenta", "logout_button": "Cerrar Sesión",
        "starting_balance": "Saldo Inicial", "total_income": "Ingresos Totales",
        "total_expenses": "Gastos Totales", "current_balance": "Saldo Actual",
        "language_label": "🌐 Idioma",
        "incorrect_login": "Usuario o contraseña incorrectos.",
        "account_suspended": "Esta cuenta ha sido suspendida. Contacte a soporte si cree que es un error.",
    },
    "hi": {
        "app_title": "वार्षिक स्मार्ट बजट ट्रैकर",
        "tab_dashboard": "📊 डैशबोर्ड", "tab_transactions": "💳 लेन-देन लॉग",
        "tab_budget": "📅 मासिक बजट", "tab_debt": "🧊 ऋण कैलकुलेटर",
        "tab_networth": "📈 निवल मूल्य", "tab_setup": "⚙️ सेटअप और खाता",
        "tab_admin": "🛡️ एडमिन",
        "book_personal": "🏠 व्यक्तिगत", "book_business": "💼 व्यवसाय",
        "welcome_back": "वापसी पर स्वागत है, {username}",
        "budget_year": "बजट वर्ष", "payday": "वेतन दिवस",
        "login_tab": "🔑 लॉग इन करें", "signup_tab": "✨ खाता बनाएं", "forgot_tab": "❓ पासवर्ड भूल गए",
        "username_label": "उपयोगकर्ता नाम", "password_label": "पासवर्ड", "email_label": "ईमेल",
        "login_button": "लॉग इन करें", "signup_button": "खाता बनाएं", "logout_button": "लॉग आउट करें",
        "starting_balance": "प्रारंभिक शेष", "total_income": "कुल आय",
        "total_expenses": "कुल व्यय", "current_balance": "वर्तमान शेष",
        "language_label": "🌐 भाषा",
        "incorrect_login": "गलत उपयोगकर्ता नाम या पासवर्ड।",
        "account_suspended": "यह खाता निलंबित कर दिया गया है। यदि आपको लगता है कि यह गलती है तो सहायता से संपर्क करें।",
    },
    "fil": {
        "app_title": "Taunang Matalinong Budget Tracker",
        "tab_dashboard": "📊 Dashboard", "tab_transactions": "💳 Talaan ng mga Transaksyon",
        "tab_budget": "📅 Buwanang Badyet", "tab_debt": "🧊 Kalkulator ng Utang",
        "tab_networth": "📈 Net Worth", "tab_setup": "⚙️ Setup at Account",
        "tab_admin": "🛡️ Admin",
        "book_personal": "🏠 Personal", "book_business": "💼 Negosyo",
        "welcome_back": "Maligayang pagbabalik, {username}",
        "budget_year": "Taon ng Badyet", "payday": "Araw ng Sahod",
        "login_tab": "🔑 Mag-log In", "signup_tab": "✨ Gumawa ng Account", "forgot_tab": "❓ Nakalimutan ang Password",
        "username_label": "Username", "password_label": "Password", "email_label": "Email",
        "login_button": "Mag-log In", "signup_button": "Gumawa ng Account", "logout_button": "Mag-log Out",
        "starting_balance": "Panimulang Balanse", "total_income": "Kabuuang Kita",
        "total_expenses": "Kabuuang Gastos", "current_balance": "Kasalukuyang Balanse",
        "language_label": "🌐 Wika",
        "incorrect_login": "Maling username o password.",
        "account_suspended": "Ang account na ito ay na-suspend. Makipag-ugnayan sa support kung sa tingin mo ay may pagkakamali.",
    },
    "pt": {
        "app_title": "Rastreador Inteligente de Orçamento Anual",
        "tab_dashboard": "📊 Painel", "tab_transactions": "💳 Registro de Transações",
        "tab_budget": "📅 Orçamento Mensal", "tab_debt": "🧊 Calculadora de Dívidas",
        "tab_networth": "📈 Patrimônio Líquido", "tab_setup": "⚙️ Configuração e Conta",
        "tab_admin": "🛡️ Administração",
        "book_personal": "🏠 Pessoal", "book_business": "💼 Empresa",
        "welcome_back": "Bem-vindo de volta, {username}",
        "budget_year": "Ano Orçamentário", "payday": "Dia de Pagamento",
        "login_tab": "🔑 Entrar", "signup_tab": "✨ Criar Conta", "forgot_tab": "❓ Esqueci a Senha",
        "username_label": "Usuário", "password_label": "Senha", "email_label": "E-mail",
        "login_button": "Entrar", "signup_button": "Criar Conta", "logout_button": "Sair",
        "starting_balance": "Saldo Inicial", "total_income": "Receita Total",
        "total_expenses": "Despesas Totais", "current_balance": "Saldo Atual",
        "language_label": "🌐 Idioma",
        "incorrect_login": "Usuário ou senha incorretos.",
        "account_suspended": "Esta conta foi suspensa. Entre em contato com o suporte se achar que isso é um erro.",
    },
    "fr": {
        "app_title": "Suivi de Budget Annuel Intelligent",
        "tab_dashboard": "📊 Tableau de Bord", "tab_transactions": "💳 Journal des Transactions",
        "tab_budget": "📅 Budget Mensuel", "tab_debt": "🧊 Calculateur de Dette",
        "tab_networth": "📈 Valeur Nette", "tab_setup": "⚙️ Configuration et Compte",
        "tab_admin": "🛡️ Administration",
        "book_personal": "🏠 Personnel", "book_business": "💼 Entreprise",
        "welcome_back": "Content de vous revoir, {username}",
        "budget_year": "Année Budgétaire", "payday": "Jour de Paie",
        "login_tab": "🔑 Connexion", "signup_tab": "✨ Créer un Compte", "forgot_tab": "❓ Mot de Passe Oublié",
        "username_label": "Nom d'utilisateur", "password_label": "Mot de passe", "email_label": "E-mail",
        "login_button": "Connexion", "signup_button": "Créer un Compte", "logout_button": "Déconnexion",
        "starting_balance": "Solde Initial", "total_income": "Revenu Total",
        "total_expenses": "Dépenses Totales", "current_balance": "Solde Actuel",
        "language_label": "🌐 Langue",
        "incorrect_login": "Nom d'utilisateur ou mot de passe incorrect.",
        "account_suspended": "Ce compte a été suspendu. Contactez le support si vous pensez qu'il s'agit d'une erreur.",
    },
    "id": {
        "app_title": "Pelacak Anggaran Tahunan Cerdas",
        "tab_dashboard": "📊 Dasbor", "tab_transactions": "💳 Catatan Transaksi",
        "tab_budget": "📅 Anggaran Bulanan", "tab_debt": "🧊 Kalkulator Utang",
        "tab_networth": "📈 Kekayaan Bersih", "tab_setup": "⚙️ Pengaturan & Akun",
        "tab_admin": "🛡️ Admin",
        "book_personal": "🏠 Pribadi", "book_business": "💼 Bisnis",
        "welcome_back": "Selamat datang kembali, {username}",
        "budget_year": "Tahun Anggaran", "payday": "Hari Gajian",
        "login_tab": "🔑 Masuk", "signup_tab": "✨ Buat Akun", "forgot_tab": "❓ Lupa Kata Sandi",
        "username_label": "Nama Pengguna", "password_label": "Kata Sandi", "email_label": "Email",
        "login_button": "Masuk", "signup_button": "Buat Akun", "logout_button": "Keluar",
        "starting_balance": "Saldo Awal", "total_income": "Total Pendapatan",
        "total_expenses": "Total Pengeluaran", "current_balance": "Saldo Saat Ini",
        "language_label": "🌐 Bahasa",
        "incorrect_login": "Nama pengguna atau kata sandi salah.",
        "account_suspended": "Akun ini telah ditangguhkan. Hubungi dukungan jika Anda yakin ini kesalahan.",
    },
    "ar": {
        "app_title": "متتبع الميزانية الذكي السنوي",
        "tab_dashboard": "📊 لوحة التحكم", "tab_transactions": "💳 سجل المعاملات",
        "tab_budget": "📅 الميزانية الشهرية", "tab_debt": "🧊 حاسبة الديون",
        "tab_networth": "📈 صافي الثروة", "tab_setup": "⚙️ الإعداد والحساب",
        "tab_admin": "🛡️ الإدارة",
        "book_personal": "🏠 شخصي", "book_business": "💼 عمل",
        "welcome_back": "مرحبًا بعودتك، {username}",
        "budget_year": "السنة المالية", "payday": "يوم الدفع",
        "login_tab": "🔑 تسجيل الدخول", "signup_tab": "✨ إنشاء حساب", "forgot_tab": "❓ نسيت كلمة المرور",
        "username_label": "اسم المستخدم", "password_label": "كلمة المرور", "email_label": "البريد الإلكتروني",
        "login_button": "تسجيل الدخول", "signup_button": "إنشاء حساب", "logout_button": "تسجيل الخروج",
        "starting_balance": "الرصيد الابتدائي", "total_income": "إجمالي الدخل",
        "total_expenses": "إجمالي المصروفات", "current_balance": "الرصيد الحالي",
        "language_label": "🌐 اللغة",
        "incorrect_login": "اسم المستخدم أو كلمة المرور غير صحيحة.",
        "account_suspended": "تم تعليق هذا الحساب. اتصل بالدعم إذا كنت تعتقد أن هذا خطأ.",
    },
    "zh": {
        "app_title": "年度智能预算追踪器",
        "tab_dashboard": "📊 仪表盘", "tab_transactions": "💳 交易记录",
        "tab_budget": "📅 月度预算", "tab_debt": "🧊 债务计算器",
        "tab_networth": "📈 净资产", "tab_setup": "⚙️ 设置与账户",
        "tab_admin": "🛡️ 管理员",
        "book_personal": "🏠 个人", "book_business": "💼 商业",
        "welcome_back": "欢迎回来，{username}",
        "budget_year": "预算年度", "payday": "发薪日",
        "login_tab": "🔑 登录", "signup_tab": "✨ 创建账户", "forgot_tab": "❓ 忘记密码",
        "username_label": "用户名", "password_label": "密码", "email_label": "电子邮箱",
        "login_button": "登录", "signup_button": "创建账户", "logout_button": "登出",
        "starting_balance": "起始余额", "total_income": "总收入",
        "total_expenses": "总支出", "current_balance": "当前余额",
        "language_label": "🌐 语言",
        "incorrect_login": "用户名或密码不正确。",
        "account_suspended": "此账户已被暂停。如果您认为这是错误，请联系支持。",
    },
    "de": {
        "app_title": "Jährlicher Smart-Budget-Tracker",
        "tab_dashboard": "📊 Übersicht", "tab_transactions": "💳 Transaktionsprotokoll",
        "tab_budget": "📅 Monatsbudget", "tab_debt": "🧊 Schuldenrechner",
        "tab_networth": "📈 Nettovermögen", "tab_setup": "⚙️ Einstellungen & Konto",
        "tab_admin": "🛡️ Admin",
        "book_personal": "🏠 Privat", "book_business": "💼 Geschäftlich",
        "welcome_back": "Willkommen zurück, {username}",
        "budget_year": "Haushaltsjahr", "payday": "Zahltag",
        "login_tab": "🔑 Anmelden", "signup_tab": "✨ Konto Erstellen", "forgot_tab": "❓ Passwort Vergessen",
        "username_label": "Benutzername", "password_label": "Passwort", "email_label": "E-Mail",
        "login_button": "Anmelden", "signup_button": "Konto Erstellen", "logout_button": "Abmelden",
        "starting_balance": "Startguthaben", "total_income": "Gesamteinkommen",
        "total_expenses": "Gesamtausgaben", "current_balance": "Aktueller Kontostand",
        "language_label": "🌐 Sprache",
        "incorrect_login": "Falscher Benutzername oder falsches Passwort.",
        "account_suspended": "Dieses Konto wurde gesperrt. Kontaktieren Sie den Support, falls dies ein Fehler ist.",
    },
}


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "en")
    text = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text


# ---------------------------------------------------------------------------
# LEGAL — Terms of Service & Privacy Policy
# ---------------------------------------------------------------------------
# TEMPLATE ONLY — this is a plain-language starting point, not a substitute
# for review by a lawyer licensed in the jurisdiction(s) you're operating
# in. Before relying on this for a real global commercial launch, have it
# reviewed — data protection obligations differ meaningfully by country
# (GDPR in the EU, the Philippines' Data Privacy Act, India's DPDP Act,
# etc.), and this template does not attempt to satisfy each one precisely.
TOS_TEXT = """
**Terms of Service (Template — Have This Reviewed by a Lawyer Before Launch)**

By creating an account you agree to the following:

1. **License, not ownership.** Your account is licensed for your personal
   or business use under the terms of your purchase. It is not
   transferable without the operator's consent.
2. **Accurate information.** You agree to provide accurate account
   information, including a working email address for account recovery.
3. **Acceptable use.** You agree not to use this service for unlawful
   purposes, to attempt to disrupt or gain unauthorized access to it, or
   to resell access without authorization.
4. **No financial advice.** This app is a budgeting and tracking tool.
   Nothing in it constitutes financial, tax, legal, or investment advice.
5. **Service availability.** The service is provided "as is." The
   operator makes reasonable efforts to keep it available and your data
   safe, but does not guarantee uninterrupted availability.
6. **Termination.** The operator may suspend or terminate accounts for
   violation of these terms, fraud, or non-payment/refund of the
   associated purchase.
7. **Changes.** These terms may be updated; continued use after an update
   constitutes acceptance of the revised terms.
"""

PRIVACY_TEXT = """
**Privacy Policy (Template — Have This Reviewed by a Lawyer Before Launch)**

1. **What we collect.** Your username, email address, and the financial
   data you choose to enter (transactions, balances, debts, goals, etc.).
2. **Why we collect it.** To operate your account, authenticate you, send
   password-reset and (if enabled) transactional emails, and — only if
   you choose to enable it — to send data to the AI provider you've
   configured your own API key for.
3. **Who can see your data.** Only you. Data is isolated per account; the
   operator can access the underlying database for support and
   administrative purposes but does not sell or share your data with
   third parties.
4. **AI features.** If you add your own AI API key, transaction
   descriptions and budget summaries you choose to submit are sent to
   that AI provider (e.g., Anthropic) under their own privacy terms —
   this only happens for users who opt in.
5. **Your rights.** You may request a data export (CSV, available in
   Setup) and full account deletion at any time (also in Setup — this
   permanently removes your account and all associated data).
6. **Data storage.** Your data is stored in a database operated on your
   behalf; if hosted outside your country of residence, it may be
   processed in that hosting location.
7. **Contact.** For privacy questions or data requests not covered by
   the self-service tools above, contact the operator directly.
"""


def legal_expanders():
    with st.expander("📜 Terms of Service"):
        st.markdown(TOS_TEXT)
    with st.expander("🔒 Privacy Policy"):
        st.markdown(PRIVACY_TEXT)


# ---------------------------------------------------------------------------
# SECRETS / CONFIG HELPERS
# ---------------------------------------------------------------------------
def get_secret(key: str, fallback=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, fallback)


def get_admin_usernames() -> list:
    raw = str(get_secret("ADMIN_USERNAMES", "") or "")
    return [a.strip() for a in raw.split(",") if a.strip()]


# ---------------------------------------------------------------------------
# DATABASE ENGINE & SCHEMA
# ---------------------------------------------------------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


@st.cache_resource
def get_engine():
    db_url = get_secret("DATABASE_URL")
    if not db_url:
        db_url = f"sqlite:///{DATA_DIR}/budget.db"
    return sa.create_engine(db_url, pool_pre_ping=True)


ENGINE = get_engine()
USING_POSTGRES = ENGINE.url.get_backend_name().startswith("postgres")

_metadata = sa.MetaData()

_users_table = sa.Table(
    "users", _metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("username", sa.String(80), unique=True, nullable=False),
    sa.Column("email", sa.String(255)),
    sa.Column("password_hash", sa.String(255), nullable=False),
    sa.Column("created_at", sa.String(50)),
    sa.Column("is_active", sa.Integer, server_default=sa.text("1")),
    sa.Column("totp_secret", sa.String(64)),
    sa.Column("totp_enabled", sa.Integer, server_default=sa.text("0")),
    sa.Column("tos_accepted_at", sa.String(50)),
)

_login_attempts_table = sa.Table(
    "login_attempts", _metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("username", sa.String(80), nullable=False),
    sa.Column("attempted_at", sa.String(50)),
    sa.Column("success", sa.Integer),
)

_collaborators_table = sa.Table(
    "book_collaborators", _metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("owner_user_id", sa.Integer, nullable=False),
    sa.Column("owner_username", sa.String(80)),
    sa.Column("track", sa.String(20), nullable=False),
    sa.Column("collaborator_username", sa.String(80), nullable=False),
    sa.Column("role", sa.String(20)),  # "Viewer" or "Editor"
    sa.Column("invited_at", sa.String(50)),
    sa.Column("accepted", sa.Integer, server_default=sa.text("0")),
)

_license_keys_table = sa.Table(
    "license_keys", _metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("license_key", sa.String(64), unique=True, nullable=False),
    sa.Column("tier", sa.String(50)),
    sa.Column("source", sa.String(100)),
    sa.Column("created_at", sa.String(50)),
    sa.Column("redeemed_by_user_id", sa.Integer),
    sa.Column("redeemed_by_username", sa.String(80)),
    sa.Column("redeemed_at", sa.String(50)),
    sa.Column("revoked", sa.Boolean, default=False),
    sa.Column("notes", sa.String(255)),
    sa.Column("external_sale_id", sa.String(120)),
)

_password_resets_table = sa.Table(
    "password_resets", _metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("token", sa.String(128), unique=True, nullable=False),
    sa.Column("user_id", sa.Integer, nullable=False),
    sa.Column("created_at", sa.String(50)),
    sa.Column("expires_at", sa.String(50)),
    sa.Column("used", sa.Boolean, default=False),
)

_metadata.create_all(ENGINE, tables=[
    _users_table, _license_keys_table, _password_resets_table, _login_attempts_table,
    _collaborators_table,
])


def ensure_column(table_name: str, column_name: str, column_type_sql: str, backfill_sql=None):
    """Lightweight migration: adds a column to an already-existing table
    (from a database created by an earlier version of this app) if it's
    not already there. Safe to call every startup."""
    try:
        inspector = sa.inspect(ENGINE)
        existing_cols = [c["name"] for c in inspector.get_columns(table_name)]
    except Exception:
        return
    if column_name not in existing_cols:
        try:
            with ENGINE.begin() as conn:
                conn.execute(sa.text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}"))
                if backfill_sql is not None:
                    conn.execute(sa.text(
                        f"UPDATE {table_name} SET {column_name} = {backfill_sql} WHERE {column_name} IS NULL"
                    ))
        except Exception:
            pass  # column may already exist under a race, or DB doesn't support this — non-fatal


ensure_column("users", "is_active", "INTEGER DEFAULT 1", backfill_sql="1")
ensure_column("license_keys", "external_sale_id", "TEXT")
ensure_column("users", "totp_secret", "TEXT")
ensure_column("users", "totp_enabled", "INTEGER DEFAULT 0", backfill_sql="0")
ensure_column("users", "tos_accepted_at", "TEXT")


def ensure_kv_table():
    with ENGINE.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE IF NOT EXISTS kv_store (user_id INTEGER, kv_key TEXT, kv_value TEXT)"
        ))


def load_kv(user_id: int, key: str, default):
    ensure_kv_table()
    with ENGINE.connect() as conn:
        row = conn.execute(
            sa.text("SELECT kv_value FROM kv_store WHERE user_id = :u AND kv_key = :k"),
            {"u": user_id, "k": key},
        ).fetchone()
    if row:
        return json.loads(row[0])
    save_kv(user_id, key, default)
    return default


def save_kv(user_id: int, key: str, value):
    ensure_kv_table()
    with ENGINE.begin() as conn:
        conn.execute(sa.text("DELETE FROM kv_store WHERE user_id = :u AND kv_key = :k"),
                     {"u": user_id, "k": key})
        conn.execute(
            sa.text("INSERT INTO kv_store (user_id, kv_key, kv_value) VALUES (:u, :k, :v)"),
            {"u": user_id, "k": key, "v": json.dumps(value)},
        )


def load_table(table_name: str, default_df: pd.DataFrame, user_id: int, track: str) -> pd.DataFrame:
    init_key = f"__init_{table_name}:{track}"
    already_init = load_kv(user_id, init_key, False)

    try:
        full_df = pd.read_sql_table(table_name, ENGINE)
    except Exception:
        full_df = None

    if full_df is not None and "user_id" in full_df.columns and "track" in full_df.columns:
        mask = (full_df["user_id"] == user_id) & (full_df["track"] == track)
        user_df = full_df.loc[mask, default_df.columns].reset_index(drop=True)
    else:
        user_df = pd.DataFrame(columns=default_df.columns)

    if not already_init:
        seed = default_df.copy()
        seed["user_id"] = user_id
        seed["track"] = track
        if full_df is None:
            seed.to_sql(table_name, ENGINE, index=False, if_exists="replace")
        else:
            seed.to_sql(table_name, ENGINE, index=False, if_exists="append")
        save_kv(user_id, init_key, True)
        return default_df.copy()

    return user_df


def save_table(df: pd.DataFrame, table_name: str, user_id: int, track: str) -> None:
    to_write = df.copy()
    to_write["user_id"] = user_id
    to_write["track"] = track
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text(f"DELETE FROM {table_name} WHERE user_id = :uid AND track = :trk"),
            {"uid": user_id, "trk": track},
        )
    to_write.to_sql(table_name, ENGINE, index=False, if_exists="append")


# ---------------------------------------------------------------------------
# PASSWORD HELPERS
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    import hashlib
    return "sha256$" + hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if password_hash.startswith("sha256$"):
            import hashlib
            return password_hash == "sha256$" + hashlib.sha256(password.encode()).hexdigest()
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def get_user_by_username(username: str):
    with ENGINE.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT id, username, email, password_hash, is_active, totp_secret, totp_enabled "
                "FROM users WHERE username = :u"
            ),
            {"u": username},
        ).fetchone()
    return row


def user_count() -> int:
    with ENGINE.connect() as conn:
        row = conn.execute(sa.text("SELECT COUNT(*) AS c FROM users")).fetchone()
    return row.c if row else 0


def create_user(username: str, email: str, password: str) -> None:
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO users (username, email, password_hash, created_at, is_active, tos_accepted_at) "
                "VALUES (:u, :e, :p, :c, 1, :tos)"
            ),
            {"u": username, "e": email, "p": hash_password(password), "c": str(datetime.utcnow()),
             "tos": str(datetime.utcnow())},
        )


def change_password(user_id: int, new_password: str) -> None:
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text("UPDATE users SET password_hash = :p WHERE id = :id"),
            {"p": hash_password(new_password), "id": user_id},
        )


def set_user_active(username: str, active: bool) -> None:
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text("UPDATE users SET is_active = :a WHERE username = :u"),
            {"a": 1 if active else 0, "u": username.strip()},
        )


# ---------------------------------------------------------------------------
# MULTI-USER PER BOOK — invite a bookkeeper/partner to a specific book
# ---------------------------------------------------------------------------
def invite_collaborator(owner_user_id: int, owner_username: str, track: str,
                         collaborator_username: str, role: str) -> str:
    clean = collaborator_username.strip()
    if not clean:
        return "Enter a username to invite."
    if clean == owner_username:
        return "You can't invite yourself."
    target = get_user_by_username(clean)
    if not target:
        return f"No account found with username '{clean}'. They need to create an account first."
    with ENGINE.connect() as conn:
        existing = conn.execute(
            sa.text(
                "SELECT id FROM book_collaborators WHERE owner_user_id = :o AND track = :t "
                "AND collaborator_username = :c"
            ),
            {"o": owner_user_id, "t": track, "c": clean},
        ).fetchone()
    if existing:
        return f"{clean} already has (or is pending) access to this book."
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO book_collaborators (owner_user_id, owner_username, track, "
                "collaborator_username, role, invited_at, accepted) VALUES (:o, :ou, :t, :c, :r, :ia, 0)"
            ),
            {"o": owner_user_id, "ou": owner_username, "t": track, "c": clean,
             "r": role, "ia": str(datetime.utcnow())},
        )
    return f"Invitation sent to {clean}. They'll see it next time they log in."


def list_book_collaborators(owner_user_id: int, track: str):
    with ENGINE.connect() as conn:
        return conn.execute(
            sa.text(
                "SELECT id, collaborator_username, role, accepted, invited_at "
                "FROM book_collaborators WHERE owner_user_id = :o AND track = :t"
            ),
            {"o": owner_user_id, "t": track},
        ).fetchall()


def list_pending_invites(username: str):
    with ENGINE.connect() as conn:
        return conn.execute(
            sa.text(
                "SELECT id, owner_username, track, role, invited_at FROM book_collaborators "
                "WHERE collaborator_username = :u AND accepted = 0"
            ),
            {"u": username},
        ).fetchall()


def list_accepted_collaborations(username: str):
    with ENGINE.connect() as conn:
        return conn.execute(
            sa.text(
                "SELECT bc.id, bc.owner_user_id, bc.owner_username, bc.track, bc.role "
                "FROM book_collaborators bc WHERE bc.collaborator_username = :u AND bc.accepted = 1"
            ),
            {"u": username},
        ).fetchall()


def respond_to_invite(invite_id: int, accept: bool) -> None:
    with ENGINE.begin() as conn:
        if accept:
            conn.execute(sa.text("UPDATE book_collaborators SET accepted = 1 WHERE id = :id"), {"id": invite_id})
        else:
            conn.execute(sa.text("DELETE FROM book_collaborators WHERE id = :id"), {"id": invite_id})


def revoke_collaborator(collab_row_id: int) -> None:
    with ENGINE.begin() as conn:
        conn.execute(sa.text("DELETE FROM book_collaborators WHERE id = :id"), {"id": collab_row_id})


def delete_user_and_all_data(user_id: int) -> None:
    """Full right-to-erasure delete: removes the account and every row
    tied to it across every table. Irreversible."""
    data_tables = ["transactions", "debts", "assets", "liabilities",
                    "targets", "networth_history", "recurring_transactions", "goals"]
    with ENGINE.begin() as conn:
        for tbl in data_tables:
            try:
                conn.execute(sa.text(f"DELETE FROM {tbl} WHERE user_id = :u"), {"u": user_id})
            except Exception:
                pass  # table may not exist if this user never touched that feature
        conn.execute(sa.text("DELETE FROM kv_store WHERE user_id = :u"), {"u": user_id})
        conn.execute(sa.text("UPDATE license_keys SET redeemed_by_user_id = NULL WHERE redeemed_by_user_id = :u"), {"u": user_id})
        conn.execute(sa.text("DELETE FROM password_resets WHERE user_id = :u"), {"u": user_id})
        conn.execute(sa.text("DELETE FROM users WHERE id = :u"), {"u": user_id})


# --- Login rate limiting -----------------------------------------------
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def record_login_attempt(username: str, success: bool) -> None:
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO login_attempts (username, attempted_at, success) VALUES (:u, :t, :s)"),
            {"u": username.strip().lower(), "t": str(datetime.utcnow()), "s": 1 if success else 0},
        )


def is_locked_out(username: str) -> bool:
    cutoff = datetime.utcnow() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    with ENGINE.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT attempted_at, success FROM login_attempts WHERE username = :u "
                "ORDER BY id DESC LIMIT :n"
            ),
            {"u": username.strip().lower(), "n": MAX_LOGIN_ATTEMPTS},
        ).fetchall()
    if len(rows) < MAX_LOGIN_ATTEMPTS:
        return False
    recent_failures = 0
    for r in rows:
        try:
            if datetime.fromisoformat(r.attempted_at) < cutoff:
                break
        except Exception:
            break
        if r.success:
            break
        recent_failures += 1
    return recent_failures >= MAX_LOGIN_ATTEMPTS


# --- Two-factor authentication (TOTP) -----------------------------------
def get_totp_status(user_id: int):
    with ENGINE.connect() as conn:
        row = conn.execute(
            sa.text("SELECT totp_secret, totp_enabled FROM users WHERE id = :id"), {"id": user_id}
        ).fetchone()
    return row


def enable_totp(user_id: int, secret: str) -> None:
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text("UPDATE users SET totp_secret = :s, totp_enabled = 1 WHERE id = :id"),
            {"s": secret, "id": user_id},
        )


def disable_totp(user_id: int) -> None:
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text("UPDATE users SET totp_secret = NULL, totp_enabled = 0 WHERE id = :id"),
            {"id": user_id},
        )


# ---------------------------------------------------------------------------
# LICENSE KEY HELPERS
# ---------------------------------------------------------------------------
def generate_license_key() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I ambiguity
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "-".join(parts)


def create_license_keys(n: int, tier: str, source: str, notes: str) -> list:
    created = []
    with ENGINE.begin() as conn:
        for _ in range(n):
            key = generate_license_key()
            for _ in range(5):
                exists = conn.execute(
                    sa.text("SELECT 1 FROM license_keys WHERE license_key = :k"), {"k": key}
                ).fetchone()
                if not exists:
                    break
                key = generate_license_key()
            conn.execute(
                sa.text(
                    "INSERT INTO license_keys (license_key, tier, source, created_at, revoked, notes) "
                    "VALUES (:k, :t, :s, :c, 0, :n)"
                ),
                {"k": key, "t": tier, "s": source, "c": str(datetime.utcnow()), "n": notes},
            )
            created.append(key)
    return created


def validate_license_key(key: str):
    clean = (key or "").strip().upper()
    if not clean:
        return None, "Enter your license key."
    with ENGINE.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, revoked, redeemed_by_user_id FROM license_keys WHERE license_key = :k"),
            {"k": clean},
        ).fetchone()
    if not row:
        return None, "That license key wasn't found. Double-check it and try again."
    if row.revoked:
        return None, "This license key has been revoked."
    if row.redeemed_by_user_id:
        return None, "This license key has already been used."
    return row, None


def redeem_license_key(key: str, user_id: int, username: str) -> None:
    clean = (key or "").strip().upper()
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE license_keys SET redeemed_by_user_id = :u, redeemed_by_username = :un, "
                "redeemed_at = :t WHERE license_key = :k"
            ),
            {"u": user_id, "un": username, "t": str(datetime.utcnow()), "k": clean},
        )


def revoke_key_and_maybe_suspend(license_key: str, cascade_suspend: bool) -> str:
    clean_key = (license_key or "").strip().upper()
    with ENGINE.begin() as conn:
        row = conn.execute(
            sa.text("SELECT redeemed_by_user_id, redeemed_by_username FROM license_keys WHERE license_key = :k"),
            {"k": clean_key},
        ).fetchone()
        conn.execute(sa.text("UPDATE license_keys SET revoked = 1 WHERE license_key = :k"), {"k": clean_key})
        if cascade_suspend and row and row.redeemed_by_user_id:
            conn.execute(sa.text("UPDATE users SET is_active = 0 WHERE id = :id"), {"id": row.redeemed_by_user_id})
    if row and row.redeemed_by_user_id and cascade_suspend:
        return f"Key revoked and user '{row.redeemed_by_username}' suspended."
    return "Key revoked."


# ---------------------------------------------------------------------------
# PASSWORD RESET HELPERS (email-based, requires SMTP secrets)
# ---------------------------------------------------------------------------
def send_reset_email(to_email: str, username: str, token: str) -> bool:
    if not to_email:
        return False
    smtp_host = get_secret("SMTP_HOST")
    smtp_port = get_secret("SMTP_PORT", 587)
    smtp_user = get_secret("SMTP_USERNAME")
    smtp_pass = get_secret("SMTP_PASSWORD")
    smtp_from = get_secret("SMTP_FROM_EMAIL", smtp_user)
    app_base_url = get_secret("APP_BASE_URL", "")

    if not (smtp_host and smtp_user and smtp_pass):
        return False

    reset_link = f"{app_base_url}?reset_token={token}" if app_base_url else f"?reset_token={token}"
    body = (
        f"Hi {username},\n\n"
        f"We received a request to reset your Annual Smart Budget Tracker password.\n"
        f"Click the link below to set a new password (valid for 1 hour):\n\n"
        f"{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )
    msg = MIMEText(body)
    msg["Subject"] = "Reset your Annual Smart Budget Tracker password"
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_email], msg.as_string())
        return True
    except Exception:
        return False


def request_password_reset(identifier: str) -> bool:
    clean = (identifier or "").strip()
    if not clean:
        return False
    with ENGINE.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, username, email FROM users WHERE username = :v OR email = :v"),
            {"v": clean},
        ).fetchone()
    if not row:
        return False
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO password_resets (token, user_id, created_at, expires_at, used) "
                "VALUES (:tok, :uid, :c, :e, 0)"
            ),
            {"tok": token, "uid": row.id, "c": str(datetime.utcnow()), "e": str(expires)},
        )
    return send_reset_email(row.email, row.username, token)


def validate_reset_token(token: str):
    with ENGINE.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, user_id, expires_at, used FROM password_resets WHERE token = :t"),
            {"t": token},
        ).fetchone()
    if not row or row.used:
        return None
    try:
        if datetime.utcnow() > datetime.fromisoformat(row.expires_at):
            return None
    except Exception:
        return None
    return row


def complete_password_reset(token: str, new_password: str, reset_row) -> None:
    with ENGINE.begin() as conn:
        conn.execute(sa.text("UPDATE users SET password_hash = :p WHERE id = :id"),
                     {"p": hash_password(new_password), "id": reset_row.user_id})
        conn.execute(sa.text("UPDATE password_resets SET used = 1 WHERE token = :t"), {"t": token})


# ---------------------------------------------------------------------------
# AUTH GATE (login / signup / forgot-password / reset-token screens)
# ---------------------------------------------------------------------------
def language_picker(key_suffix: str = ""):
    codes = list(LANGUAGES.keys())
    current = st.session_state.get("lang", "en")
    idx = codes.index(current) if current in codes else 0
    chosen = st.selectbox(
        t("language_label"), codes, index=idx,
        format_func=lambda c: LANGUAGES[c], key=f"lang_picker_{key_suffix}",
    )
    if chosen != current:
        st.session_state["lang"] = chosen
        if st.session_state.get("user_id"):
            save_kv(st.session_state["user_id"], "lang", chosen)
        st.rerun()


def auth_gate() -> bool:
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"

    reset_token = st.query_params.get("reset_token")
    if reset_token:
        st.markdown(
            f"""<div class="app-header"><h2 style="color:white;margin:0;">💰 {t('app_title')}</h2>
            <p style="margin:4px 0 0 0;opacity:0.85;">Set a new password.</p></div>""",
            unsafe_allow_html=True,
        )
        reset_row = validate_reset_token(reset_token)
        if not reset_row:
            st.error("This reset link is invalid or has expired. Request a new one from the login page.")
            if st.button("Back to Login"):
                st.query_params.clear()
                st.rerun()
            return False

        with st.form("reset_pw_form"):
            pw1 = st.text_input("New password", type="password")
            pw2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Update Password", use_container_width=True):
                if len(pw1) < 6:
                    st.error("Password must be at least 6 characters.")
                elif pw1 != pw2:
                    st.error("Passwords don't match.")
                else:
                    complete_password_reset(reset_token, pw1, reset_row)
                    st.success("Password updated! Click below to continue.")
                    if st.button("Continue to Login"):
                        st.query_params.clear()
                        st.rerun()
        return False

    if st.session_state.get("user_id"):
        return True

    language_picker("prelogin")

    st.markdown(
        f"""<div class="app-header"><h2 style="color:white;margin:0;">💰 {t('app_title')}</h2>
        <p style="margin:4px 0 0 0;opacity:0.85;">Log in, create an account with your license key, or reset your password.</p></div>""",
        unsafe_allow_html=True,
    )

    tab_login, tab_signup, tab_forgot = st.tabs([t("login_tab"), t("signup_tab"), t("forgot_tab")])

    with tab_login:
        pending_uid = st.session_state.get("pending_2fa_user_id")
        if pending_uid:
            st.info("Enter the 6-digit code from your authenticator app.")
            with st.form("totp_verify_form"):
                code = st.text_input("Authentication Code", max_chars=6)
                col_a, col_b = st.columns(2)
                verify_clicked = col_a.form_submit_button("Verify", use_container_width=True)
                cancel_clicked = col_b.form_submit_button("Cancel", use_container_width=True)
                if cancel_clicked:
                    st.session_state.pop("pending_2fa_user_id", None)
                    st.session_state.pop("pending_2fa_username", None)
                    st.session_state.pop("totp_attempts", None)
                    st.rerun()
                if verify_clicked:
                    _attempts = st.session_state.get("totp_attempts", 0)
                    if _attempts >= 5:
                        st.error("Too many incorrect codes. Please log in again from the start.")
                        st.session_state.pop("pending_2fa_user_id", None)
                        st.session_state.pop("pending_2fa_username", None)
                        st.session_state.pop("totp_attempts", None)
                        st.rerun()
                    totp_row = get_totp_status(pending_uid)
                    valid = False
                    if PYOTP_AVAILABLE and totp_row and totp_row.totp_secret:
                        valid = pyotp.TOTP(totp_row.totp_secret).verify(code.strip(), valid_window=1)
                    if valid:
                        st.session_state["user_id"] = pending_uid
                        st.session_state["username"] = st.session_state.pop("pending_2fa_username")
                        st.session_state.pop("pending_2fa_user_id", None)
                        st.session_state.pop("totp_attempts", None)
                        st.session_state["lang"] = load_kv(pending_uid, "lang", st.session_state["lang"])
                        st.rerun()
                    else:
                        st.session_state["totp_attempts"] = _attempts + 1
                        st.error(f"Incorrect or expired code. ({5 - (_attempts + 1)} attempts remaining)")
        else:
            with st.form("login_form"):
                username = st.text_input(t("username_label"))
                password = st.text_input(t("password_label"), type="password")
                if st.form_submit_button(t("login_button"), use_container_width=True):
                    clean_username = username.strip()
                    if is_locked_out(clean_username):
                        st.error(
                            f"Too many failed attempts. This account is temporarily locked — "
                            f"try again in {LOCKOUT_WINDOW_MINUTES} minutes."
                        )
                    else:
                        row = get_user_by_username(clean_username)
                        if row and verify_password(password, row.password_hash):
                            record_login_attempt(clean_username, success=True)
                            if row.is_active is not None and int(row.is_active) == 0:
                                st.error(t("account_suspended"))
                            elif row.totp_enabled:
                                st.session_state["pending_2fa_user_id"] = row.id
                                st.session_state["pending_2fa_username"] = row.username
                                st.rerun()
                            else:
                                st.session_state["user_id"] = row.id
                                st.session_state["username"] = row.username
                                st.session_state["lang"] = load_kv(row.id, "lang", st.session_state["lang"])
                                st.rerun()
                        else:
                            record_login_attempt(clean_username, success=False)
                            st.error(t("incorrect_login"))

    with tab_signup:
        admin_usernames = get_admin_usernames()
        with st.form("signup_form"):
            new_username = st.text_input(t("username_label"))
            new_email = st.text_input(t("email_label") + " (required — used for password recovery)")
            new_password = st.text_input(t("password_label"), type="password")
            new_password2 = st.text_input("Confirm " + t("password_label").lower(), type="password")
            needs_key = not (user_count() == 0)
            license_key_input = ""
            if needs_key:
                license_key_input = st.text_input(
                    "License Key", placeholder="XXXX-XXXX-XXXX-XXXX",
                    help="Sent to you after purchase. Contact support if you haven't received one.",
                )
            tos_agree = st.checkbox("I agree to the Terms of Service and Privacy Policy (see links below).")
            if st.form_submit_button(t("signup_button"), use_container_width=True):
                clean_username = new_username.strip()
                is_bootstrap_or_admin = (user_count() == 0) or (clean_username in admin_usernames)

                if not clean_username or not new_password or not new_email.strip():
                    st.error("Username, email, and password are all required.")
                elif not tos_agree:
                    st.error("You must agree to the Terms of Service and Privacy Policy to create an account.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif new_password != new_password2:
                    st.error("Passwords don't match.")
                elif get_user_by_username(clean_username):
                    st.error("That username is already taken.")
                else:
                    proceed = True
                    license_row = None
                    if not is_bootstrap_or_admin:
                        license_row, err = validate_license_key(license_key_input)
                        if err:
                            st.error(err)
                            proceed = False
                    if proceed:
                        create_user(clean_username, new_email.strip(), new_password)
                        if license_row:
                            created_user = get_user_by_username(clean_username)
                            redeem_license_key(license_key_input, created_user.id, created_user.username)
                        st.success("Account created! Switch to the Log In tab to sign in.")

    with tab_forgot:
        st.caption("Enter the username or email on your account. If it matches, we'll email a reset link (valid for 1 hour).")
        with st.form("forgot_pw_form"):
            identifier = st.text_input("Username or Email")
            if st.form_submit_button("Send Reset Link", use_container_width=True):
                if not get_secret("SMTP_HOST"):
                    st.error("Password reset email isn't configured on this deployment yet — contact support directly.")
                else:
                    request_password_reset(identifier)
                    st.success("If that account exists, a reset link has been sent to its email address.")

    st.markdown("---")
    legal_expanders()

    return False


if not auth_gate():
    st.stop()

USER_ID = st.session_state["user_id"]
USERNAME = st.session_state["username"]
IS_ADMIN = USERNAME in get_admin_usernames()

# These stay fixed to whoever actually logged in — used for personal
# account settings, admin checks, and managing invites. Data access
# below may point at a DIFFERENT owner if the user is working inside a
# book shared with them as a collaborator.
LOGGED_IN_USER_ID = USER_ID
LOGGED_IN_USERNAME = USERNAME

# ---------------------------------------------------------------------------
# PERSONAL / BUSINESS MODE CONFIG
# ---------------------------------------------------------------------------
MODE_CONFIG = {
    "Personal": {
        "icon": "🏠", "cashflow_label": "Net Cashflow", "breakdown_title": "50/30/20 Budget Breakdown",
        "groups": [
            {"name": "Needs (50%)", "pct": 0.50, "type": "cap"},
            {"name": "Wants (30%)", "pct": 0.30, "type": "cap"},
            {"name": "Savings/Debt (20%)", "pct": 0.20, "type": "reserve"},
        ],
        "default_categories": {
            "income": ["Salary / Wages", "Freelance / Side Hustle", "Investment Returns", "Refunds / Gifts"],
            "expense": {
                "Rent / Mortgage": "Needs (50%)", "Utilities & Internet": "Needs (50%)",
                "Groceries": "Needs (50%)", "Insurance & Healthcare": "Needs (50%)",
                "Dining & Takeout": "Wants (30%)", "Entertainment & Streaming": "Wants (30%)",
                "Shopping & Apparel": "Wants (30%)", "Emergency Fund": "Savings/Debt (20%)",
                "Investment / Retirement": "Savings/Debt (20%)", "Debt Service / Credit Card": "Savings/Debt (20%)",
            },
        },
    },
    "Business": {
        "icon": "💼", "cashflow_label": "Net Profit", "breakdown_title": "60/25/15 Operating Breakdown",
        "groups": [
            {"name": "Operating Costs (60%)", "pct": 0.60, "type": "cap"},
            {"name": "Growth & Marketing (25%)", "pct": 0.25, "type": "cap"},
            {"name": "Reserves & Tax (15%)", "pct": 0.15, "type": "reserve"},
        ],
        "default_categories": {
            "income": ["Client Revenue", "Product Sales", "Consulting Fees", "Other Business Income"],
            "expense": {
                "Payroll & Contractors": "Operating Costs (60%)", "Office Rent & Utilities": "Operating Costs (60%)",
                "Software & Subscriptions": "Operating Costs (60%)", "Supplies & Inventory": "Operating Costs (60%)",
                "Marketing & Advertising": "Growth & Marketing (25%)", "Travel & Client Meals": "Growth & Marketing (25%)",
                "Professional Development": "Growth & Marketing (25%)", "Taxes & Licenses": "Reserves & Tax (15%)",
                "Equipment & Capital Reserve": "Reserves & Tax (15%)", "Rainy Day / Contingency Fund": "Reserves & Tax (15%)",
            },
        },
    },
}

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def default_transactions(mode: str) -> pd.DataFrame:
    year = datetime.now().year
    if mode == "Business":
        return pd.DataFrame([
            {"Date": f"{year}-01-01", "Description": "Client Payment — Acme Co", "Type": "Income",
             "Amount": 4500.00, "Group": "N/A", "Category": "Client Revenue"},
            {"Date": f"{year}-01-03", "Description": "Office Rent", "Type": "Expense",
             "Amount": 1200.00, "Group": "Operating Costs (60%)", "Category": "Office Rent & Utilities"},
            {"Date": f"{year}-01-05", "Description": "Software Subscriptions", "Type": "Expense",
             "Amount": 180.00, "Group": "Operating Costs (60%)", "Category": "Software & Subscriptions"},
            {"Date": f"{year}-01-10", "Description": "Social Ad Campaign", "Type": "Expense",
             "Amount": 350.00, "Group": "Growth & Marketing (25%)", "Category": "Marketing & Advertising"},
        ])
    return pd.DataFrame([
        {"Date": f"{year}-01-01", "Description": "Monthly Salary", "Type": "Income",
         "Amount": 5000.00, "Group": "N/A", "Category": "Salary / Wages"},
        {"Date": f"{year}-01-02", "Description": "Apartment Rent", "Type": "Expense",
         "Amount": 1500.00, "Group": "Needs (50%)", "Category": "Rent / Mortgage"},
        {"Date": f"{year}-01-05", "Description": "Grocery Store", "Type": "Expense",
         "Amount": 250.00, "Group": "Needs (50%)", "Category": "Groceries"},
        {"Date": f"{year}-01-10", "Description": "Streaming Services", "Type": "Expense",
         "Amount": 45.00, "Group": "Wants (30%)", "Category": "Entertainment & Streaming"},
    ])


def default_debts(mode: str) -> pd.DataFrame:
    if mode == "Business":
        return pd.DataFrame([
            {"Debt Name": "Business Line of Credit", "Balance": 15000.00, "APR (%)": 12.50, "Min Payment": 400.00},
            {"Debt Name": "Equipment Loan", "Balance": 8000.00, "APR (%)": 7.25, "Min Payment": 220.00},
        ])
    return pd.DataFrame([
        {"Debt Name": "Credit Card A", "Balance": 5000.00, "APR (%)": 19.99, "Min Payment": 150.00},
        {"Debt Name": "Auto Loan", "Balance": 12000.00, "APR (%)": 5.49, "Min Payment": 250.00},
    ])


def default_assets(mode: str) -> pd.DataFrame:
    if mode == "Business":
        return pd.DataFrame([
            {"Asset": "Business Checking", "Category": "Liquid Cash", "Value": 12000.00},
            {"Asset": "Accounts Receivable", "Category": "Receivables", "Value": 6500.00},
            {"Asset": "Equipment & Inventory", "Category": "Fixed Assets", "Value": 22000.00},
        ])
    return pd.DataFrame([
        {"Asset": "Checking & Savings", "Category": "Liquid Cash", "Value": 8500.00},
        {"Asset": "Investment / 401(k)", "Category": "Retirement", "Value": 24000.00},
        {"Asset": "Primary Residence", "Category": "Real Estate", "Value": 350000.00},
    ])


def default_liabilities(mode: str) -> pd.DataFrame:
    if mode == "Business":
        return pd.DataFrame([
            {"Liability": "Business Term Loan", "Category": "Business Debt", "Value": 25000.00},
            {"Liability": "Vendor Payables", "Category": "Accounts Payable", "Value": 4200.00},
        ])
    return pd.DataFrame([
        {"Liability": "Mortgage Balance", "Category": "Real Estate Debt", "Value": 210000.00},
        {"Liability": "Auto Loan", "Category": "Vehicle Debt", "Value": 12000.00},
        {"Liability": "Credit Card Balance", "Category": "Revolving Debt", "Value": 5000.00},
    ])


def default_targets(categories: dict) -> pd.DataFrame:
    rows = [{"Category": cat, "Annual Target": 0.0} for cat in categories["expense"].keys()]
    return pd.DataFrame(rows)


def default_nw_history() -> pd.DataFrame:
    return pd.DataFrame(columns=["Date", "Total Assets", "Total Liabilities", "Net Worth"])


def default_recurring() -> pd.DataFrame:
    return pd.DataFrame(columns=["Description", "Type", "Amount", "Category", "Group", "Frequency", "Next Date", "Active"])


def default_goals() -> pd.DataFrame:
    return pd.DataFrame(columns=["Goal Name", "Target Amount", "Saved So Far", "Target Date", "Achieved"])


def compute_next_date(current: date, frequency: str) -> date:
    if frequency == "Weekly":
        return current + timedelta(days=7)
    if frequency == "Monthly":
        month = current.month + 1
        year = current.year + (1 if month > 12 else 0)
        month = month if month <= 12 else 1
        day = min(current.day, 28)
        return date(year, month, day)
    if frequency == "Yearly":
        return date(current.year + 1, current.month, current.day)
    return current + timedelta(days=30)


DEFAULT_SETTINGS = {
    "currency": "$", "starting_balance": 1000.00,
    "payday": "1st of the Month", "budget_year": datetime.now().year,
}

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# MULTI-USER PER BOOK — "Working In" selector (own books, or a book someone
# shared with you as a collaborator). Zero-overhead for the vast majority
# of users who have no collaborations — the extra UI only appears if
# list_accepted_collaborations returns something.
# ---------------------------------------------------------------------------
ACCEPTED_COLLABS = list_accepted_collaborations(LOGGED_IN_USERNAME)

if "working_as" not in st.session_state:
    st.session_state["working_as"] = "own"

VIEWING_OWN_BOOKS = True
ROLE = "Owner"

if ACCEPTED_COLLABS and st.session_state["working_as"] != "own":
    _collab_id = int(str(st.session_state["working_as"]).replace("collab_", ""))
    _matched = next((c for c in ACCEPTED_COLLABS if c.id == _collab_id), None)
    if _matched:
        USER_ID = _matched.owner_user_id
        USERNAME = _matched.owner_username
        MODE = _matched.track
        ROLE = _matched.role
        VIEWING_OWN_BOOKS = False

# ---------------------------------------------------------------------------
# ACTIVE MODE (Personal / Business) — persisted per user, switchable anytime.
# Only applies when working in your own books; a shared book's track is
# fixed to whatever the owner shared.
# ---------------------------------------------------------------------------
if VIEWING_OWN_BOOKS:
    if "active_mode" not in st.session_state:
        st.session_state["active_mode"] = load_kv(USER_ID, "active_mode", "Personal")
    MODE = st.session_state["active_mode"]

MODE_CFG = MODE_CONFIG[MODE]

settings = load_kv(USER_ID, f"settings:{MODE}", DEFAULT_SETTINGS)
categories = load_kv(USER_ID, f"categories:{MODE}", MODE_CFG["default_categories"])
ai_api_key = load_kv(USER_ID, "ai_api_key", "")

df_txn = load_table("transactions", default_transactions(MODE), USER_ID, MODE)
df_debts = load_table("debts", default_debts(MODE), USER_ID, MODE)
df_assets = load_table("assets", default_assets(MODE), USER_ID, MODE)
df_liab = load_table("liabilities", default_liabilities(MODE), USER_ID, MODE)
df_targets = load_table("targets", default_targets(categories), USER_ID, MODE)
df_nw_hist = load_table("networth_history", default_nw_history(), USER_ID, MODE)
df_recurring = load_table("recurring_transactions", default_recurring(), USER_ID, MODE)
df_goals = load_table("goals", default_goals(), USER_ID, MODE)

# Auto-post any recurring transactions whose Next Date has arrived, and
# roll their Next Date forward — runs once per page load.
if not df_recurring.empty:
    _today = date.today()
    _posted_any = False
    for _idx, _rrow in df_recurring.iterrows():
        if not bool(_rrow.get("Active", True)):
            continue
        try:
            _next_dt = datetime.strptime(str(_rrow["Next Date"]), "%Y-%m-%d").date()
        except Exception:
            continue
        while _next_dt <= _today:
            new_txn = pd.DataFrame([{
                "Date": str(_next_dt), "Description": f"{_rrow['Description']} (auto)",
                "Type": _rrow["Type"], "Amount": _rrow["Amount"],
                "Group": _rrow["Group"], "Category": _rrow["Category"],
            }])
            df_txn = pd.concat([df_txn, new_txn], ignore_index=True)
            df_recurring.at[_idx, "Next Date"] = str(compute_next_date(_next_dt, _rrow["Frequency"]))
            _next_dt = compute_next_date(_next_dt, _rrow["Frequency"])
            _posted_any = True
    if _posted_any:
        save_table(df_txn, "transactions", USER_ID, MODE)
        save_table(df_recurring, "recurring_transactions", USER_ID, MODE)

currency = settings["currency"]
starting_balance = float(settings["starting_balance"])
budget_year = int(settings["budget_year"])


def fmt(amount) -> str:
    try:
        return f"{currency}{amount:,.2f}"
    except (TypeError, ValueError):
        return f"{currency}0.00"


# ---------------------------------------------------------------------------
# FORECASTING & ANOMALY DETECTION (pure statistics — no AI/API needed, so
# this works for every user regardless of whether they've added an AI key)
# ---------------------------------------------------------------------------
def compute_spending_forecast(df: pd.DataFrame, months_ahead: int = 1):
    """Simple, transparent trend projection: average monthly expense per
    category over the last up-to-6 months, projected forward. Not a
    machine-learning model — deliberately simple so the number is easy to
    explain to a user, which matters more than sophistication here."""
    exp = df[df["Type"] == "Expense"].copy()
    if exp.empty:
        return pd.DataFrame(columns=["Category", "Avg Monthly", f"Projected (+{months_ahead}mo)"])
    exp["Date"] = pd.to_datetime(exp["Date"], errors="coerce")
    exp = exp.dropna(subset=["Date"])
    if exp.empty:
        return pd.DataFrame(columns=["Category", "Avg Monthly", f"Projected (+{months_ahead}mo)"])
    exp["YearMonth"] = exp["Date"].dt.to_period("M")
    recent_months = sorted(exp["YearMonth"].unique())[-6:]
    exp = exp[exp["YearMonth"].isin(recent_months)]
    monthly = exp.groupby(["Category", "YearMonth"])["Amount"].sum().reset_index()
    avg_by_cat = monthly.groupby("Category")["Amount"].mean().reset_index()
    avg_by_cat.columns = ["Category", "Avg Monthly"]
    avg_by_cat[f"Projected (+{months_ahead}mo)"] = avg_by_cat["Avg Monthly"] * months_ahead
    return avg_by_cat.sort_values("Avg Monthly", ascending=False)


def detect_spending_anomalies(df: pd.DataFrame, z_threshold: float = 2.0):
    """Flags individual transactions that are unusually large relative to
    that category's own historical average — a simple z-score check, not
    a black box. Needs at least 3 prior transactions in a category to
    judge what's 'unusual' for it."""
    exp = df[df["Type"] == "Expense"].copy()
    if exp.empty or len(exp) < 4:
        return []
    flags = []
    for cat, group in exp.groupby("Category"):
        if len(group) < 4:
            continue
        mean = group["Amount"].mean()
        std = group["Amount"].std()
        if not std or pd.isna(std) or std == 0:
            continue
        for _, row in group.iterrows():
            z = (row["Amount"] - mean) / std
            if z >= z_threshold and row["Amount"] > mean * 1.5:
                flags.append({
                    "Description": row["Description"], "Category": cat,
                    "Amount": row["Amount"], "Usual Average": round(mean, 2), "Date": row["Date"],
                })
    return sorted(flags, key=lambda f: f["Amount"], reverse=True)[:5]


def ai_answer_question(client, question: str, context_summary: str):
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=400,
            messages=[{"role": "user", "content": (
                "You are a financial assistant answering a question about the user's own "
                "budget data below. Answer directly and concisely based only on this data. "
                "If the data doesn't contain what's needed to answer, say so plainly rather "
                f"than guessing.\n\nBudget data:\n{context_summary}\n\nQuestion: {question}"
            )}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ACCOUNTANT-READY PDF EXPORT
# ---------------------------------------------------------------------------
def _pdf_safe(text) -> str:
    """fpdf2's core Helvetica font only supports Latin-1 — sanitize any
    text (emoji, non-Latin scripts from multilingual users) before it
    hits pdf.cell(), or PDF generation crashes on real-world data."""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf_report(mode: str, username: str, currency_symbol: str,
                          txn_df: pd.DataFrame, breakdown_df: pd.DataFrame,
                          nw_summary: dict, budget_year_val: int) -> bytes:
    if not FPDF_AVAILABLE:
        return b""

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _pdf_safe(f"Annual Smart Budget Tracker - {mode} Financial Report"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _pdf_safe(f"Account: {username}  |  Budget Year: {budget_year_val}  |  Generated: {date.today()}"), ln=True)
    pdf.ln(4)

    total_income = txn_df.loc[txn_df["Type"] == "Income", "Amount"].sum()
    total_expenses = txn_df.loc[txn_df["Type"] == "Expense", "Amount"].sum()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Total Income: {currency_symbol}{total_income:,.2f}", ln=True)
    pdf.cell(0, 6, f"Total Expenses: {currency_symbol}{total_expenses:,.2f}", ln=True)
    pdf.cell(0, 6, f"Net: {currency_symbol}{(total_income - total_expenses):,.2f}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Budget Breakdown", ln=True)
    pdf.set_font("Helvetica", "B", 9)
    for col_name, width in [("Group", 60), ("Target", 40), ("Actual", 40), ("Variance", 40)]:
        pdf.cell(width, 7, col_name, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for _, row in breakdown_df.iterrows():
        pdf.cell(60, 7, _pdf_safe(row["Group"]), border=1)
        pdf.cell(40, 7, f"{currency_symbol}{row['Target Amount']:,.2f}", border=1)
        pdf.cell(40, 7, f"{currency_symbol}{row['Actual Spent']:,.2f}", border=1)
        pdf.cell(40, 7, f"{currency_symbol}{row['Variance']:,.2f}", border=1)
        pdf.ln()
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Net Worth Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Total Assets: {currency_symbol}{nw_summary.get('assets', 0):,.2f}", ln=True)
    pdf.cell(0, 6, f"Total Liabilities: {currency_symbol}{nw_summary.get('liabilities', 0):,.2f}", ln=True)
    pdf.cell(0, 6, f"Net Worth: {currency_symbol}{nw_summary.get('net_worth', 0):,.2f}", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Transaction Log ({len(txn_df)} entries)", ln=True)
    pdf.set_font("Helvetica", "B", 8)
    for col_name, width in [("Date", 25), ("Description", 65), ("Type", 20), ("Category", 45), ("Amount", 30)]:
        pdf.cell(width, 6, col_name, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for _, row in txn_df.sort_values("Date").iterrows():
        pdf.cell(25, 6, _pdf_safe(str(row["Date"])[:10]), border=1)
        pdf.cell(65, 6, _pdf_safe(str(row["Description"])[:38]), border=1)
        pdf.cell(20, 6, _pdf_safe(row["Type"]), border=1)
        pdf.cell(45, 6, _pdf_safe(str(row["Category"])[:26]), border=1)
        pdf.cell(30, 6, f"{currency_symbol}{row['Amount']:,.2f}", border=1)
        pdf.ln()
        if pdf.get_y() > 270:
            pdf.add_page()

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# AI HELPERS (optional — only active if the user supplied their own key)
# ---------------------------------------------------------------------------
def get_ai_client():
    if not ai_api_key or not ANTHROPIC_SDK_AVAILABLE:
        return None
    try:
        return anthropic.Anthropic(api_key=ai_api_key)
    except Exception:
        return None


def ai_suggest_category(client, description: str, options: list):
    if not description.strip():
        return None
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=20,
            messages=[{"role": "user", "content": (
                "Pick the single best-matching category for this transaction "
                "from this exact list (respond with ONLY the category name, "
                f"nothing else):\n{options}\n\nTransaction: {description}"
            )}],
        )
        suggestion = msg.content[0].text.strip()
        return suggestion if suggestion in options else None
    except Exception:
        return None


def ai_generate_insights(client, summary_text: str):
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=350,
            messages=[{"role": "user", "content": (
                "You are a friendly financial assistant. Based on this budget "
                "summary, give 2-3 short, specific, encouraging insights or "
                "suggestions in plain sentences (no markdown headers, no bullet "
                f"symbols):\n\n{summary_text}"
            )}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None


AI_CLIENT = get_ai_client()

# ---------------------------------------------------------------------------
# PLAID (BANK CONNECTIVITY) HELPERS
# ---------------------------------------------------------------------------
# Coverage note: Plaid supports the US, Canada, UK, and parts of Europe.
# It does NOT support banks in the Philippines, India, Indonesia, or most
# of the world. This is a real, permanent limitation of Plaid itself, not
# something this integration can work around. Users in unsupported
# countries simply won't see a matching institution when they try to link.
PLAID_COUNTRY_CODES = ["US", "CA", "GB", "FR", "ES", "NL", "IE", "DE", "IT", "PL", "DK", "NO", "SE", "EE", "LT", "LV", "PT", "BE"]


def get_fernet():
    if not CRYPTO_AVAILABLE:
        return None
    key = get_secret("PLAID_ENCRYPTION_KEY")
    if not key:
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None


def encrypt_token(raw_token: str) -> str:
    f = get_fernet()
    if f:
        return f.encrypt(raw_token.encode()).decode()
    return raw_token  # falls back to plaintext if no encryption key configured — flagged in UI


def decrypt_token(stored_token: str) -> str:
    f = get_fernet()
    if f:
        try:
            return f.decrypt(stored_token.encode()).decode()
        except Exception:
            return stored_token
    return stored_token


def get_plaid_client():
    if not PLAID_SDK_AVAILABLE:
        return None
    client_id = get_secret("PLAID_CLIENT_ID")
    secret_key = get_secret("PLAID_SECRET")
    env_name = str(get_secret("PLAID_ENV", "sandbox")).lower()
    if not (client_id and secret_key):
        return None
    host_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development,
        "production": plaid.Environment.Production,
    }
    configuration = plaid.Configuration(
        host=host_map.get(env_name, plaid.Environment.Sandbox),
        api_key={"clientId": client_id, "secret": secret_key},
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))


PLAID_CLIENT = get_plaid_client()


def create_plaid_link_token(user_id: int):
    if not PLAID_CLIENT:
        return None
    try:
        req = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
            client_name="Annual Smart Budget Tracker",
            products=[Products("transactions")],
            country_codes=[CountryCode(c) for c in PLAID_COUNTRY_CODES],
            language="en",
        )
        resp = PLAID_CLIENT.link_token_create(req)
        return resp["link_token"]
    except Exception:
        return None


def exchange_public_token(public_token: str):
    if not PLAID_CLIENT:
        return None
    try:
        req = ItemPublicTokenExchangeRequest(public_token=public_token)
        resp = PLAID_CLIENT.item_public_token_exchange(req)
        return resp["access_token"], resp["item_id"]
    except Exception:
        return None, None


def ensure_plaid_table():
    with ENGINE.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE IF NOT EXISTS plaid_items ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, track TEXT, "
            "item_id TEXT, access_token TEXT, institution_name TEXT, "
            "created_at TEXT, last_synced_at TEXT, plaid_cursor TEXT"
            ")" if not USING_POSTGRES else
            "CREATE TABLE IF NOT EXISTS plaid_items ("
            "id SERIAL PRIMARY KEY, user_id INTEGER, track TEXT, "
            "item_id TEXT, access_token TEXT, institution_name TEXT, "
            "created_at TEXT, last_synced_at TEXT, plaid_cursor TEXT"
            ")"
        ))


def save_plaid_item(user_id: int, track: str, access_token: str, item_id: str, institution_name: str):
    ensure_plaid_table()
    with ENGINE.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO plaid_items (user_id, track, item_id, access_token, institution_name, created_at) "
                "VALUES (:u, :t, :iid, :at, :inst, :c)"
            ),
            {"u": user_id, "t": track, "iid": item_id, "at": encrypt_token(access_token),
             "inst": institution_name, "c": str(datetime.utcnow())},
        )


def get_plaid_items(user_id: int, track: str):
    ensure_plaid_table()
    with ENGINE.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT id, item_id, institution_name, access_token, last_synced_at "
                     "FROM plaid_items WHERE user_id = :u AND track = :t"),
            {"u": user_id, "t": track},
        ).fetchall()
    return rows


def remove_plaid_item(plaid_row_id: int, access_token_encrypted: str):
    if PLAID_CLIENT:
        try:
            raw = decrypt_token(access_token_encrypted)
            PLAID_CLIENT.item_remove(ItemRemoveRequest(access_token=raw))
        except Exception:
            pass  # continue removing our record even if the remote call fails
    with ENGINE.begin() as conn:
        conn.execute(sa.text("DELETE FROM plaid_items WHERE id = :id"), {"id": plaid_row_id})


def ensure_plaid_dedup_table():
    with ENGINE.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE IF NOT EXISTS plaid_imported_txns (user_id INTEGER, plaid_transaction_id TEXT)"
        ))


def filter_new_plaid_txn_ids(user_id: int, txn_ids: list) -> set:
    ensure_plaid_dedup_table()
    if not txn_ids:
        return set()
    with ENGINE.connect() as conn:
        placeholders = ", ".join(f":id{i}" for i in range(len(txn_ids)))
        params = {"u": user_id}
        params.update({f"id{i}": tid for i, tid in enumerate(txn_ids)})
        rows = conn.execute(
            sa.text(f"SELECT plaid_transaction_id FROM plaid_imported_txns "
                     f"WHERE user_id = :u AND plaid_transaction_id IN ({placeholders})"),
            params,
        ).fetchall()
    already_have = {r[0] for r in rows}
    return set(txn_ids) - already_have


def mark_plaid_txn_ids_imported(user_id: int, txn_ids: list) -> None:
    ensure_plaid_dedup_table()
    with ENGINE.begin() as conn:
        for tid in txn_ids:
            conn.execute(
                sa.text("INSERT INTO plaid_imported_txns (user_id, plaid_transaction_id) VALUES (:u, :t)"),
                {"u": user_id, "t": tid},
            )


def sync_plaid_transactions(plaid_row_id: int, user_id: int, access_token_encrypted: str, categories: dict):
    """Pulls new transactions from Plaid since the last sync, skips any
    already imported (via a dedup table, so this table's schema never
    needs to touch the main transactions table), and best-effort maps
    Plaid's categories onto the user's own category list. Returns a
    DataFrame shaped exactly like the transactions table, ready to
    concat + save directly."""
    if not PLAID_CLIENT:
        return pd.DataFrame(), "Plaid isn't configured."

    raw_token = decrypt_token(access_token_encrypted)
    with ENGINE.connect() as conn:
        cursor_row = conn.execute(
            sa.text("SELECT plaid_cursor FROM plaid_items WHERE id = :id"), {"id": plaid_row_id}
        ).fetchone()
    existing_cursor = cursor_row.plaid_cursor if cursor_row and cursor_row.plaid_cursor else None

    try:
        req_kwargs = {"access_token": raw_token}
        if existing_cursor:
            req_kwargs["cursor"] = existing_cursor
        resp = PLAID_CLIENT.transactions_sync(TransactionsSyncRequest(**req_kwargs))
        added = resp["added"]
    except Exception as e:
        return pd.DataFrame(), f"Sync failed: {e}"

    all_expense_cats = list(categories["expense"].keys())
    all_income_cats = categories["income"]
    candidates = []
    for txn in added:
        amount = float(txn["amount"])  # Plaid convention: positive = money out (expense), negative = money in (income)
        is_expense = amount > 0
        pfc = (txn.get("personal_finance_category") or {})
        plaid_cat = pfc.get("primary", "") if pfc else (txn.get("category", [""])[0] if txn.get("category") else "")
        if is_expense:
            guess = next((c for c in all_expense_cats if plaid_cat.split("_")[0].lower() in c.lower()), None)
            category = guess or (all_expense_cats[0] if all_expense_cats else "Uncategorized")
            group = categories["expense"].get(category, "N/A")
            txn_type = "Expense"
        else:
            category = all_income_cats[0] if all_income_cats else "Uncategorized"
            group = "N/A"
            txn_type = "Income"
        candidates.append({
            "Date": str(txn["date"]), "Description": txn.get("name", "Bank Transaction"),
            "Type": txn_type, "Amount": abs(amount), "Group": group, "Category": category,
            "plaid_id": txn["transaction_id"],
        })

    new_ids = filter_new_plaid_txn_ids(user_id, [c["plaid_id"] for c in candidates])
    kept = [c for c in candidates if c["plaid_id"] in new_ids]
    imported_ids = [c.pop("plaid_id") for c in kept]
    if imported_ids:
        mark_plaid_txn_ids_imported(user_id, imported_ids)

    with ENGINE.begin() as conn:
        conn.execute(
            sa.text("UPDATE plaid_items SET last_synced_at = :t, plaid_cursor = :c WHERE id = :id"),
            {"t": str(datetime.utcnow()), "c": resp.get("next_cursor", ""), "id": plaid_row_id},
        )
    return pd.DataFrame(kept), None

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# PLAID LINK CALLBACK — captures the public_token after a successful bank
# link (Plaid Link redirects the browser with it as a query param, since
# Streamlit has no native way to receive a JS callback directly).
# ---------------------------------------------------------------------------
_plaid_public_token = st.query_params.get("plaid_public_token")
if _plaid_public_token:
    _access_token, _item_id = exchange_public_token(_plaid_public_token)
    _inst_name = st.query_params.get("plaid_institution", "Linked Bank")
    if _access_token:
        save_plaid_item(USER_ID, MODE, _access_token, _item_id, _inst_name)
        st.query_params.clear()
        st.success(f"✅ {_inst_name} connected! You can sync transactions from the Transactions tab.")
    else:
        st.query_params.clear()
        st.error("Couldn't complete the bank connection — please try again.")

# ---------------------------------------------------------------------------
# HEADER + MODE SWITCHER
# ---------------------------------------------------------------------------
mode_badge = f'<span class="mode-badge">{MODE_CFG["icon"]} {MODE} Mode</span>'
st.markdown(
    f"""<div class="app-header">
        <h2 style="color:white;margin:0;">💰 {t('app_title')} {mode_badge}</h2>
        <p style="margin:4px 0 0 0;opacity:0.85;">
            {t('welcome_back', username=USERNAME)} &nbsp;·&nbsp; {t('budget_year')} {budget_year} &nbsp;·&nbsp; {t('payday')}: {settings['payday']}
        </p>
    </div>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# FIRST-LOGIN WELCOME (shown once per person, not once per book — dismissible)
# ---------------------------------------------------------------------------
_seen_welcome = load_kv(LOGGED_IN_USER_ID, "seen_welcome", False)
if not _seen_welcome:
    with st.container(border=True):
        st.markdown("### 👋 Welcome — quick orientation before you dive in")
        st.markdown(
            "- Everything you see right now is **sample data** — head to the **Transactions Log** "
            "tab and start replacing it with your own whenever you're ready.\n"
            "- Switch between **Personal** and **Business** tracking anytime with the toggle just below.\n"
            "- Visit **Setup & Account** to set your currency, starting balance, and — optionally — "
            "an AI key to unlock smart category suggestions and insights.\n"
            "- A one-page Quick Start guide came with your purchase and covers all of this in under "
            "two minutes if you'd rather read it there."
        )
        if st.button("Got it — don't show this again", use_container_width=True):
            save_kv(LOGGED_IN_USER_ID, "seen_welcome", True)
            st.rerun()

mode_col1, mode_col2 = st.columns([1, 3])
with mode_col1:
    if VIEWING_OWN_BOOKS:
        chosen = st.radio(
            "Book", [t("book_personal"), t("book_business")],
            index=0 if MODE == "Personal" else 1,
            horizontal=True, label_visibility="collapsed",
        )
        new_mode = "Personal" if chosen == t("book_personal") else "Business"
        if new_mode != MODE:
            st.session_state["active_mode"] = new_mode
            save_kv(USER_ID, "active_mode", new_mode)
            st.rerun()
    else:
        st.info(f"🤝 Shared book: **{MODE}** (owned by {USERNAME})")

with st.sidebar:
    st.markdown("### 💰 Smart Budget Tracker")
    st.caption(f"Logged in as **{LOGGED_IN_USERNAME}**" + (" (Admin)" if IS_ADMIN else ""))
    storage_label = "Postgres (persistent, multi-user safe)" if USING_POSTGRES else "Local SQLite (single-user only)"
    st.caption(f"Storage: **{storage_label}**")

    if ACCEPTED_COLLABS:
        st.divider()
        work_options = {"own": "📗 My Own Books"}
        for c in ACCEPTED_COLLABS:
            work_options[f"collab_{c.id}"] = f"🤝 {c.owner_username} — {c.track} ({c.role})"
        current_key = st.session_state["working_as"] if st.session_state["working_as"] in work_options else "own"
        chosen_key = st.selectbox(
            "Working In", list(work_options.keys()), index=list(work_options.keys()).index(current_key),
            format_func=lambda k: work_options[k],
        )
        if chosen_key != st.session_state["working_as"]:
            st.session_state["working_as"] = chosen_key
            st.rerun()
        if not VIEWING_OWN_BOOKS:
            st.caption(f"👁️ Viewing **{USERNAME}'s {MODE}** book as **{ROLE}**" + (" — read-only" if ROLE == "Viewer" else ""))

    _pending = list_pending_invites(LOGGED_IN_USERNAME)
    if _pending:
        st.divider()
        st.warning(f"📬 {len(_pending)} pending invitation(s) — see Setup & Account.")

    st.divider()
    st.metric(t("current_balance"), fmt(starting_balance + df_txn.loc[df_txn['Type'] == 'Income', 'Amount'].sum()
                                         - df_txn.loc[df_txn['Type'] == 'Expense', 'Amount'].sum()))
    if AI_CLIENT:
        st.markdown('<span class="ai-badge">✨ AI Features Active</span>', unsafe_allow_html=True)
    else:
        st.caption("✨ AI features available — add your API key in Setup to enable.")
    st.divider()
    language_picker("sidebar")
    st.divider()
    if st.button(t("logout_button"), use_container_width=True):
        for k in ("user_id", "username", "active_mode", "working_as"):
            st.session_state.pop(k, None)
        st.rerun()

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_labels = [t("tab_dashboard"), t("tab_transactions"), t("tab_budget"),
              "🔁 Recurring", "🎯 Goals",
              t("tab_debt"), t("tab_networth"), t("tab_setup")]
if IS_ADMIN:
    tab_labels.append(t("tab_admin"))

_tabs = st.tabs(tab_labels)
tab_dash, tab_txn, tab_budget, tab_recurring, tab_goals, tab_debt, tab_nw, tab_setup = _tabs[:8]
tab_admin = _tabs[8] if IS_ADMIN else None

# ---------------------------------------------------------------------------
# TAB 1: DASHBOARD
# ---------------------------------------------------------------------------
with tab_dash:
    total_income = df_txn.loc[df_txn["Type"] == "Income", "Amount"].sum()
    total_expenses = df_txn.loc[df_txn["Type"] == "Expense", "Amount"].sum()
    net_cashflow = starting_balance + total_income - total_expenses

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("starting_balance"), fmt(starting_balance))
    c2.metric(t("total_income"), fmt(total_income))
    c3.metric(t("total_expenses"), fmt(total_expenses))
    c4.metric(MODE_CFG["cashflow_label"], fmt(net_cashflow), delta=fmt(total_income - total_expenses))

    st.markdown("---")
    st.subheader(f"🎯 {MODE_CFG['breakdown_title']}")

    safe_income = total_income if total_income > 0 else 0.0
    rows = []
    for g in MODE_CFG["groups"]:
        actual = df_txn.loc[df_txn["Group"] == g["name"], "Amount"].sum()
        target_amt = safe_income * g["pct"]
        variance = (actual - target_amt) if g["type"] == "reserve" else (target_amt - actual)
        rows.append({
            "Group": g["name"], "Target %": f"{int(g['pct']*100)}%",
            "Target Amount": target_amt, "Actual Spent": actual, "Variance": variance,
        })
    breakdown_df = pd.DataFrame(rows)

    col_table, col_chart = st.columns([3, 2])
    with col_table:
        def _style_variance(v):
            return f"color: {PALETTE['green']};" if v >= 0 else f"color: {PALETTE['red']};"

        styled = breakdown_df.style.format(
            {"Target Amount": lambda v: fmt(v), "Actual Spent": lambda v: fmt(v), "Variance": lambda v: fmt(v)}
        ).map(_style_variance, subset=["Variance"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        if total_income == 0:
            st.caption("⚠️ No income logged yet — targets will populate once income transactions are added.")

    with col_chart:
        if breakdown_df["Actual Spent"].sum() > 0:
            fig = px.pie(breakdown_df, values="Actual Spent", names="Group",
                         title="Actual Spending Distribution", hole=0.45,
                         color_discrete_sequence=[PALETTE["blue"], "#F9AB00", PALETTE["green"]])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add expense transactions to see your spending distribution.")

    st.markdown("---")
    st.subheader(f"📈 {MODE_CFG['cashflow_label']} Trend")
    if not df_txn.empty:
        trend_df = df_txn.copy()
        trend_df["Date"] = pd.to_datetime(trend_df["Date"], errors="coerce")
        trend_df = trend_df.dropna(subset=["Date"]).sort_values("Date")
        trend_df["Signed"] = trend_df.apply(
            lambda r: r["Amount"] if r["Type"] == "Income" else -r["Amount"], axis=1
        )
        trend_df["Running Balance"] = starting_balance + trend_df["Signed"].cumsum()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=trend_df["Date"], y=trend_df["Running Balance"],
                                   mode="lines+markers", line=dict(color=PALETTE["blue"])))
        fig2.update_layout(margin=dict(t=10, b=10), yaxis_title=f"Balance ({currency})")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No transactions yet.")

    st.markdown("---")
    st.subheader("📉 Spending Forecast")
    st.caption("Based on your average monthly spend per category over the last 6 months — a plain trend projection, not a black-box prediction.")
    forecast_months = st.slider("Project how many months ahead?", 1, 6, 1)
    forecast_df = compute_spending_forecast(df_txn, forecast_months)
    if not forecast_df.empty:
        st.dataframe(
            forecast_df.style.format({"Avg Monthly": lambda v: fmt(v), f"Projected (+{forecast_months}mo)": lambda v: fmt(v)}),
            use_container_width=True, hide_index=True,
        )
        st.caption(f"Total projected spend over the next {forecast_months} month(s): "
                    f"**{fmt(forecast_df[f'Projected (+{forecast_months}mo)'].sum())}**")
    else:
        st.info("Not enough transaction history yet to forecast — add a few weeks of data first.")

    st.markdown("---")
    st.subheader("🚨 Unusual Transactions")
    anomalies = detect_spending_anomalies(df_txn)
    if anomalies:
        for a in anomalies:
            st.warning(
                f"**{a['Description']}** ({a['Category']}) on {a['Date']}: {fmt(a['Amount'])} — "
                f"about {a['Amount']/a['Usual Average']:.1f}x your usual {fmt(a['Usual Average'])} for this category."
            )
    else:
        st.caption("Nothing unusual detected — your spending has been consistent with its own history.")

    st.markdown("---")
    st.subheader("✨ AI Insights (Optional)")
    if AI_CLIENT:
        if st.button("Generate AI Insights", use_container_width=True):
            with st.spinner("Analyzing your budget..."):
                summary = (
                    f"Mode: {MODE}. Currency: {currency}. Total income: {fmt(total_income)}. "
                    f"Total expenses: {fmt(total_expenses)}. {MODE_CFG['cashflow_label']}: {fmt(net_cashflow)}. "
                    f"Breakdown: {breakdown_df[['Group','Target Amount','Actual Spent']].to_dict('records')}"
                )
                insight = ai_generate_insights(AI_CLIENT, summary)
            if insight:
                st.info(insight)
            else:
                st.warning("Couldn't generate insights right now — check your API key in Setup.")

        st.markdown("**💬 Ask a question about your finances**")
        nl_question = st.text_input(
            "e.g. \"How much did I spend on dining last month?\" or \"Am I on track with my Rent budget?\"",
            key="nl_question",
        )
        if st.button("Ask", use_container_width=True) and nl_question.strip():
            with st.spinner("Thinking..."):
                nl_context = (
                    f"Mode: {MODE}. Currency: {currency}. All transactions (Date, Description, Type, "
                    f"Amount, Category, Group): {df_txn.to_dict('records')}. "
                    f"Category targets: {df_targets.to_dict('records')}."
                )
                answer = ai_answer_question(AI_CLIENT, nl_question, nl_context)
            if answer:
                st.info(answer)
            else:
                st.warning("Couldn't get an answer right now — check your API key in Setup.")
    else:
        st.caption("Add your Anthropic API key in **Setup & Account** to unlock AI-generated insights and natural-language questions about your finances.")

# ---------------------------------------------------------------------------
# TAB 2: TRANSACTIONS LOG
# ---------------------------------------------------------------------------
with tab_txn:
    st.subheader(f"🏦 Bank Accounts — {MODE}")
    if not PLAID_SDK_AVAILABLE:
        st.caption("Bank connectivity requires the `plaid-python` package — add it to requirements.txt to enable this.")
    elif not PLAID_CLIENT:
        st.caption(
            "Bank connectivity isn't configured yet. Add `PLAID_CLIENT_ID`, `PLAID_SECRET`, and "
            "`PLAID_ENV` in Streamlit secrets to enable it (see README)."
        )
    else:
        linked = get_plaid_items(USER_ID, MODE)
        if linked:
            for _lrow in linked:
                with st.container(border=True):
                    lc1, lc2, lc3 = st.columns([3, 1, 1])
                    last_sync = _lrow.last_synced_at or "never"
                    lc1.markdown(f"**{_lrow.institution_name}** — last synced: {last_sync}")
                    if lc2.button("🔄 Sync Now", key=f"sync_{_lrow.id}", use_container_width=True, disabled=(ROLE == "Viewer")):
                        with st.spinner("Pulling new transactions..."):
                            new_df, err = sync_plaid_transactions(_lrow.id, USER_ID, _lrow.access_token, categories)
                        if err:
                            st.error(err)
                        elif new_df.empty:
                            st.info("No new transactions since last sync.")
                        else:
                            df_txn = pd.concat([df_txn, new_df], ignore_index=True)
                            save_table(df_txn, "transactions", USER_ID, MODE)
                            st.success(f"Imported {len(new_df)} new transaction(s).")
                            st.rerun()
                    if lc3.button("🗑️ Disconnect", key=f"disconnect_{_lrow.id}", use_container_width=True, disabled=(ROLE != "Owner")):
                        remove_plaid_item(_lrow.id, _lrow.access_token)
                        st.success(f"{_lrow.institution_name} disconnected.")
                        st.rerun()
        else:
            st.caption("No bank accounts linked to this book yet.")

        if st.button("➕ Connect a Bank Account", use_container_width=True, disabled=(ROLE != "Owner")):
            st.session_state["show_plaid_link"] = True

        if st.session_state.get("show_plaid_link"):
            link_token = create_plaid_link_token(USER_ID)
            if not link_token:
                st.error("Couldn't start the connection — check your Plaid credentials in Secrets.")
            else:
                components.html(
                    f"""
                    <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
                    <div style="text-align:center;padding:20px;font-family:sans-serif;">
                        <p>Opening your bank's secure login...</p>
                    </div>
                    <script>
                        var handler = Plaid.create({{
                            token: '{link_token}',
                            onSuccess: function(public_token, metadata) {{
                                var inst = metadata.institution ? metadata.institution.name : 'Linked Bank';
                                var url = window.top.location.href.split('?')[0];
                                window.top.location.href = url + '?plaid_public_token=' + public_token
                                    + '&plaid_institution=' + encodeURIComponent(inst);
                            }},
                            onExit: function(err, metadata) {{
                                var url = window.top.location.href.split('?')[0];
                                window.top.location.href = url;
                            }}
                        }});
                        handler.open();
                    </script>
                    """,
                    height=100,
                )
            st.session_state["show_plaid_link"] = False

    st.markdown("---")
    st.subheader("➕ Add New Transaction")

    if AI_CLIENT:
        with st.container(border=True):
            st.caption("✨ Optional: describe the transaction and let AI suggest a category before you fill in the form below.")
            ai_col1, ai_col2 = st.columns([3, 1])
            quick_desc = ai_col1.text_input("Quick description", key="ai_quick_desc", label_visibility="collapsed",
                                             placeholder="e.g. Uber ride to airport")
            if ai_col2.button("✨ Suggest Category", use_container_width=True):
                all_options = list(categories["expense"].keys()) + categories["income"]
                suggestion = ai_suggest_category(AI_CLIENT, quick_desc, all_options)
                if suggestion:
                    st.session_state["ai_suggested_category"] = suggestion
                    st.session_state["ai_suggested_desc"] = quick_desc
                    st.success(f"Suggested category: **{suggestion}** — pre-filled below.")
                else:
                    st.warning("Couldn't get a confident suggestion — pick manually below.")

    with st.form("add_txn_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        txn_date = col1.date_input("Date", datetime.now())
        txn_type = col2.selectbox("Type", ["Expense", "Income"])
        default_desc = st.session_state.pop("ai_suggested_desc", "")
        txn_desc = col3.text_input("Description", value=default_desc)
        txn_amount = col4.number_input("Amount", min_value=0.01, step=10.00)

        suggested_cat = st.session_state.pop("ai_suggested_category", None)

        if txn_type == "Expense":
            expense_cats = list(categories["expense"].keys()) or ["Uncategorized"]
            idx = expense_cats.index(suggested_cat) if suggested_cat in expense_cats else 0
            cat = st.selectbox("Category", expense_cats, index=idx)
            group = categories["expense"].get(cat, "N/A")
        else:
            income_cats = categories["income"] or ["Uncategorized"]
            idx = income_cats.index(suggested_cat) if suggested_cat in income_cats else 0
            cat = st.selectbox("Category", income_cats, index=idx)
            group = "N/A"

        submitted = st.form_submit_button("Save Transaction", use_container_width=True, disabled=(ROLE == "Viewer"))
        if submitted:
            if not txn_desc.strip():
                st.warning("Please enter a description before saving.")
            else:
                new_row = pd.DataFrame([{
                    "Date": str(txn_date), "Description": txn_desc, "Type": txn_type,
                    "Amount": txn_amount, "Group": group, "Category": cat,
                }])
                df_txn = pd.concat([df_txn, new_row], ignore_index=True)
                save_table(df_txn, "transactions", USER_ID, MODE)
                st.success("Transaction saved.")
                st.rerun()

    st.markdown("---")
    st.subheader("📒 Transaction Ledger")
    st.caption("Edit any cell directly, or use the trash icon on a row to delete it. Changes save automatically.")

    edited_txn = st.data_editor(
        df_txn, use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "Amount": st.column_config.NumberColumn(format="%.2f"),
            "Type": st.column_config.SelectboxColumn(options=["Income", "Expense"]),
        },
        key="txn_editor", disabled=(ROLE == "Viewer"),
    )
    if not edited_txn.equals(df_txn):
        save_table(edited_txn, "transactions", USER_ID, MODE)
        df_txn = edited_txn
        st.rerun()

    csv_buf = io.StringIO()
    df_txn.to_csv(csv_buf, index=False)
    st.download_button("⬇️ Export Transactions CSV", csv_buf.getvalue(),
                        file_name=f"{MODE.lower()}_transactions_export.csv", mime="text/csv")

# ---------------------------------------------------------------------------
# TAB 3: MONTHLY BUDGET
# ---------------------------------------------------------------------------
with tab_budget:
    st.subheader(f"📅 {budget_year} Monthly Expense Aggregation — {MODE}")

    df_exp = df_txn[df_txn["Type"] == "Expense"].copy()
    if not df_exp.empty:
        df_exp["Date"] = pd.to_datetime(df_exp["Date"], errors="coerce")
        df_exp = df_exp.dropna(subset=["Date"])
        df_exp = df_exp[df_exp["Date"].dt.year == budget_year]

    if not df_exp.empty:
        df_exp["Month"] = df_exp["Date"].dt.strftime("%b")
        pivot = df_exp.pivot_table(index=["Category", "Group"], columns="Month",
                                    values="Amount", aggfunc="sum", fill_value=0)
        for m in MONTH_ORDER:
            if m not in pivot.columns:
                pivot[m] = 0.0
        pivot = pivot[MONTH_ORDER]
        pivot["Annual Total"] = pivot.sum(axis=1)
        pivot = pivot.reset_index()

        targets_map = dict(zip(df_targets["Category"], df_targets["Annual Target"]))
        pivot["Annual Target"] = pivot["Category"].map(targets_map).fillna(0.0)
        pivot["Remaining"] = pivot["Annual Target"] - pivot["Annual Total"]

        fmt_cols = MONTH_ORDER + ["Annual Total", "Annual Target", "Remaining"]
        st.dataframe(
            pivot.style.format({c: (lambda v: fmt(v)) for c in fmt_cols}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info(f"No expense transactions logged for {budget_year} in {MODE} mode yet.")

    st.markdown("---")
    st.subheader("🎯 Annual Category Targets")
    st.caption("Set an annual spending target per category — used above to track Remaining budget.")
    edited_targets = st.data_editor(
        df_targets, use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={"Annual Target": st.column_config.NumberColumn(format="%.2f")},
        key="targets_editor", disabled=(ROLE == "Viewer"),
    )
    if not edited_targets.equals(df_targets):
        save_table(edited_targets, "targets", USER_ID, MODE)
        st.rerun()

# ---------------------------------------------------------------------------
# TAB: RECURRING TRANSACTIONS
# ---------------------------------------------------------------------------
with tab_recurring:
    st.subheader(f"🔁 Recurring Transactions — {MODE}")
    st.caption(
        "Set up rent, payroll, subscriptions, or any regular income/expense once — "
        "it posts to your Transactions Log automatically on schedule, and 'Next Date' "
        "rolls forward each time it fires. No more re-entering the same thing every month."
    )

    with st.form("add_recurring_form", clear_on_submit=True):
        rcol1, rcol2, rcol3, rcol4 = st.columns(4)
        rec_desc = rcol1.text_input("Description")
        rec_type = rcol2.selectbox("Type", ["Expense", "Income"], key="rec_type")
        rec_amount = rcol3.number_input("Amount", min_value=0.01, step=10.00, key="rec_amount")
        rec_freq = rcol4.selectbox("Frequency", ["Weekly", "Monthly", "Yearly"])

        if rec_type == "Expense":
            rec_cats = list(categories["expense"].keys()) or ["Uncategorized"]
            rec_cat = st.selectbox("Category", rec_cats, key="rec_cat")
            rec_group = categories["expense"].get(rec_cat, "N/A")
        else:
            rec_cats = categories["income"] or ["Uncategorized"]
            rec_cat = st.selectbox("Category", rec_cats, key="rec_cat")
            rec_group = "N/A"

        rec_start = st.date_input("First / Next Occurrence", datetime.now())

        if st.form_submit_button("Add Recurring Item", use_container_width=True, disabled=(ROLE == "Viewer")):
            if not rec_desc.strip():
                st.warning("Please enter a description.")
            else:
                new_rec = pd.DataFrame([{
                    "Description": rec_desc, "Type": rec_type, "Amount": rec_amount,
                    "Category": rec_cat, "Group": rec_group, "Frequency": rec_freq,
                    "Next Date": str(rec_start), "Active": True,
                }])
                df_recurring = pd.concat([df_recurring, new_rec], ignore_index=True)
                save_table(df_recurring, "recurring_transactions", USER_ID, MODE)
                st.success("Recurring item added — it will post automatically on its date.")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Scheduled Items")
    if not df_recurring.empty:
        edited_rec = st.data_editor(
            df_recurring, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={
                "Amount": st.column_config.NumberColumn(format="%.2f"),
                "Type": st.column_config.SelectboxColumn(options=["Income", "Expense"]),
                "Frequency": st.column_config.SelectboxColumn(options=["Weekly", "Monthly", "Yearly"]),
                "Active": st.column_config.CheckboxColumn(),
            },
            key="recurring_editor", disabled=(ROLE == "Viewer"),
        )
        if not edited_rec.equals(df_recurring):
            save_table(edited_rec, "recurring_transactions", USER_ID, MODE)
            st.rerun()
    else:
        st.info("No recurring items yet — add your rent, payroll, or a subscription above.")

# ---------------------------------------------------------------------------
# TAB: FINANCIAL GOALS
# ---------------------------------------------------------------------------
with tab_goals:
    st.subheader(f"🎯 Financial Goals — {MODE}")
    st.caption("Track progress toward a savings target — a down payment, an emergency fund, a piece of equipment.")

    with st.form("add_goal_form", clear_on_submit=True):
        gcol1, gcol2, gcol3 = st.columns(3)
        goal_name = gcol1.text_input("Goal Name")
        goal_target = gcol2.number_input("Target Amount", min_value=0.01, step=100.0)
        goal_date = gcol3.date_input("Target Date", datetime.now() + timedelta(days=365))
        if st.form_submit_button("Add Goal", use_container_width=True, disabled=(ROLE == "Viewer")):
            if not goal_name.strip():
                st.warning("Please name your goal.")
            else:
                new_goal = pd.DataFrame([{
                    "Goal Name": goal_name, "Target Amount": goal_target, "Saved So Far": 0.0,
                    "Target Date": str(goal_date), "Achieved": False,
                }])
                df_goals = pd.concat([df_goals, new_goal], ignore_index=True)
                save_table(df_goals, "goals", USER_ID, MODE)
                st.success("Goal added.")
                st.rerun()

    st.markdown("---")
    if not df_goals.empty:
        for _gidx, _grow in df_goals.iterrows():
            target = float(_grow["Target Amount"]) if _grow["Target Amount"] else 0.0
            saved = float(_grow["Saved So Far"]) if _grow["Saved So Far"] else 0.0
            pct = min(saved / target, 1.0) if target > 0 else 0.0
            with st.container(border=True):
                gc1, gc2 = st.columns([3, 1])
                gc1.markdown(f"**{_grow['Goal Name']}** — target {fmt(target)} by {_grow['Target Date']}")
                gc2.markdown(f"**{fmt(saved)}** / {fmt(target)}")
                st.progress(pct, text=f"{pct*100:.0f}% there")
                add_col1, add_col2 = st.columns([3, 1])
                contribution = add_col1.number_input(
                    "Add contribution", min_value=0.0, step=10.0, key=f"contrib_{_gidx}", label_visibility="collapsed"
                )
                if add_col2.button("Add", key=f"contrib_btn_{_gidx}", use_container_width=True, disabled=(ROLE == "Viewer")):
                    if contribution > 0:
                        df_goals.at[_gidx, "Saved So Far"] = saved + contribution
                        if saved + contribution >= target:
                            df_goals.at[_gidx, "Achieved"] = True
                        save_table(df_goals, "goals", USER_ID, MODE)
                        st.rerun()
        st.markdown("---")
        st.caption("Edit or delete goals directly:")
        edited_goals = st.data_editor(
            df_goals, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={
                "Target Amount": st.column_config.NumberColumn(format="%.2f"),
                "Saved So Far": st.column_config.NumberColumn(format="%.2f"),
                "Achieved": st.column_config.CheckboxColumn(),
            },
            key="goals_editor", disabled=(ROLE == "Viewer"),
        )
        if not edited_goals.equals(df_goals):
            save_table(edited_goals, "goals", USER_ID, MODE)
            st.rerun()
    else:
        st.info("No goals yet — add one above.")

# ---------------------------------------------------------------------------
# TAB 4: DEBT CALCULATOR
# ---------------------------------------------------------------------------
with tab_debt:
    st.subheader(f"🧊 Debt Payoff Estimator — {MODE}")
    strategy = st.radio(
        "Payoff Strategy", ["Avalanche (Highest APR First)", "Snowball (Lowest Balance First)"],
        horizontal=True,
    )

    st.caption("Edit balances, APR, or minimum payments below — deletions and additions save automatically.")
    edited_debts = st.data_editor(
        df_debts, use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "Balance": st.column_config.NumberColumn(format="%.2f"),
            "APR (%)": st.column_config.NumberColumn(format="%.2f"),
            "Min Payment": st.column_config.NumberColumn(format="%.2f"),
        },
        key="debt_editor", disabled=(ROLE == "Viewer"),
    )
    if not edited_debts.equals(df_debts):
        save_table(edited_debts, "debts", USER_ID, MODE)
        df_debts = edited_debts
        st.rerun()

    def calculate_payoff(row):
        balance, apr, pmt = row["Balance"], row["APR (%)"] / 100, row["Min Payment"]
        monthly_rate = apr / 12
        if balance <= 0:
            return 0.0, 0.0
        if pmt <= balance * monthly_rate:
            return "Payment Too Low", "N/A"
        months = balance / (pmt - (balance * monthly_rate))
        total_paid = months * pmt
        total_interest = total_paid - balance
        return round(months, 1), round(total_interest, 2)

    if not df_debts.empty:
        results = df_debts.apply(calculate_payoff, axis=1, result_type="expand")
        results.columns = ["Est. Payoff (Months)", "Total Interest"]
        df_debt_view = pd.concat([df_debts, results], axis=1)

        if strategy.startswith("Avalanche"):
            df_debt_view = df_debt_view.sort_values("APR (%)", ascending=False)
        else:
            df_debt_view = df_debt_view.sort_values("Balance", ascending=True)
        df_debt_view.insert(0, "Priority", range(1, len(df_debt_view) + 1))

        st.markdown("---")
        st.subheader("📋 Payoff Priority Order")
        st.dataframe(
            df_debt_view.style.format({
                "Balance": lambda v: fmt(v), "Min Payment": lambda v: fmt(v),
                "APR (%)": "{:.2f}%",
                "Total Interest": lambda v: fmt(v) if isinstance(v, (int, float)) else v,
            }),
            use_container_width=True, hide_index=True,
        )

        total_balance = df_debts["Balance"].sum()
        total_min_pmt = df_debts["Min Payment"].sum()
        numeric_interest = pd.to_numeric(df_debt_view["Total Interest"], errors="coerce")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Debt Balance", fmt(total_balance))
        c2.metric("Total Minimum Payments", fmt(total_min_pmt))
        c3.metric("Est. Total Interest (at minimums)", fmt(numeric_interest.sum(skipna=True)))
    else:
        st.info("No debts logged. Add one in the table above.")

# ---------------------------------------------------------------------------
# TAB 5: NET WORTH TRACKER
# ---------------------------------------------------------------------------
with tab_nw:
    st.subheader(f"📈 Net Worth Overview — {MODE}")

    col_a, col_l = st.columns(2)
    with col_a:
        st.markdown("**Assets (What You Own)**")
        edited_assets = st.data_editor(
            df_assets, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
            key="asset_editor", disabled=(ROLE == "Viewer"),
        )
        if not edited_assets.equals(df_assets):
            save_table(edited_assets, "assets", USER_ID, MODE)
            df_assets = edited_assets
            st.rerun()

    with col_l:
        st.markdown("**Liabilities (What You Owe)**")
        edited_liab = st.data_editor(
            df_liab, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
            key="liab_editor", disabled=(ROLE == "Viewer"),
        )
        if not edited_liab.equals(df_liab):
            save_table(edited_liab, "liabilities", USER_ID, MODE)
            df_liab = edited_liab
            st.rerun()

    tot_assets = df_assets["Value"].sum()
    tot_liab = df_liab["Value"].sum()
    net_worth = tot_assets - tot_liab

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Assets", fmt(tot_assets))
    c2.metric("Total Liabilities", fmt(tot_liab))
    c3.metric("Current Net Worth", fmt(net_worth))

    if st.button("📌 Save Snapshot to History", use_container_width=True, disabled=(ROLE == "Viewer")):
        snap = pd.DataFrame([{
            "Date": str(date.today()), "Total Assets": tot_assets,
            "Total Liabilities": tot_liab, "Net Worth": net_worth,
        }])
        df_nw_hist = pd.concat([df_nw_hist, snap], ignore_index=True)
        save_table(df_nw_hist, "networth_history", USER_ID, MODE)
        st.success("Snapshot saved.")
        st.rerun()

    if not df_nw_hist.empty:
        st.markdown("---")
        st.subheader("Net Worth Trend")
        hist = df_nw_hist.copy()
        hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce")
        hist = hist.dropna(subset=["Date"]).sort_values("Date")
        fig3 = px.line(hist, x="Date", y="Net Worth", markers=True)
        fig3.update_traces(line_color=PALETTE["blue"])
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(
            df_nw_hist.style.format({
                "Total Assets": lambda v: fmt(v), "Total Liabilities": lambda v: fmt(v),
                "Net Worth": lambda v: fmt(v),
            }),
            use_container_width=True, hide_index=True,
        )

# ---------------------------------------------------------------------------
# TAB 6: SETUP & ACCOUNT
# ---------------------------------------------------------------------------
with tab_setup:
    if VIEWING_OWN_BOOKS:
        st.subheader(f"⚙️ {MODE} Book Settings")
        with st.form("settings_form"):
            col1, col2 = st.columns(2)
            currency_options = ["$", "€", "£", "CA$", "A$", "¥", "CHF", "₹", "₱", "R$", "MX$", "IDR"]
            new_currency = col1.selectbox(
                "Currency Symbol", currency_options,
                index=currency_options.index(settings["currency"]) if settings["currency"] in currency_options else 0,
            )
            new_balance = col2.number_input("Starting Balance", value=float(settings["starting_balance"]), step=100.0)
            col3, col4 = st.columns(2)
            payday_options = ["1st of the Month", "15th of the Month",
                               "Every 2 Weeks (Bi-Weekly)", "Last Day of Month"]
            new_payday = col3.selectbox(
                "Payday / Revenue Cycle", payday_options,
                index=payday_options.index(settings["payday"]) if settings["payday"] in payday_options else 0,
            )
            new_year = col4.number_input("Active Budget Year", value=int(settings["budget_year"]), step=1, format="%d")

            if st.form_submit_button(f"💾 Save {MODE} Settings", use_container_width=True):
                settings.update({
                    "currency": new_currency, "starting_balance": new_balance,
                    "payday": new_payday, "budget_year": int(new_year),
                })
                save_kv(USER_ID, f"settings:{MODE}", settings)
                st.success("Settings saved.")
                st.rerun()

        st.markdown("---")
        st.subheader(f"🏷️ {MODE} Income Categories")
        income_text = st.text_area("One category per line", value="\n".join(categories["income"]), height=120)
        st.markdown("---")
        valid_groups = {g["name"] for g in MODE_CFG["groups"]}
        st.subheader(f"🏷️ {MODE} Expense Categories & Group")
        st.caption(f"Format: `Category Name | Group` — Group must be one of: {', '.join(valid_groups)}")
        expense_lines = "\n".join(f"{k} | {v}" for k, v in categories["expense"].items())
        expense_text = st.text_area("Expense categories", value=expense_lines, height=220)

        if st.button("💾 Save Categories", use_container_width=True):
            new_income = [line.strip() for line in income_text.splitlines() if line.strip()]
            new_expense = {}
            malformed = []
            for line in expense_text.splitlines():
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) == 2 and parts[1] in valid_groups:
                    new_expense[parts[0]] = parts[1]
                else:
                    malformed.append(line)
            if malformed:
                st.error("These lines couldn't be saved (check the `Name | Group` format and group spelling): "
                          + "; ".join(malformed))
            else:
                categories["income"] = new_income
                categories["expense"] = new_expense
                save_kv(USER_ID, f"categories:{MODE}", categories)
                st.success("Categories saved.")
                st.rerun()

        st.markdown("---")
    else:
        st.info(f"Book-wide settings and categories can only be changed by the book's owner. "
                f"You have **{ROLE}** access to this shared book.")

    st.subheader("🌐 Language")
    language_picker("setup")

    st.markdown("---")
    st.subheader("✨ AI Features (Optional)")
    if VIEWING_OWN_BOOKS:
        st.caption(
            "Add your own Anthropic API key to unlock AI category suggestions and spending "
            "insights. This is entirely optional — the app is fully functional without it. "
            "Get a key at console.anthropic.com."
        )
        new_ai_key = st.text_input("Anthropic API Key", value=ai_api_key, type="password")
        if st.button("💾 Save API Key", use_container_width=True):
            save_kv(USER_ID, "ai_api_key", new_ai_key.strip())
            st.success("API key saved.")
            st.rerun()
    else:
        st.caption("AI features (if enabled) work automatically using the book owner's key — only the owner can view or change it.")

    st.markdown("---")
    st.subheader("🔐 Account")
    with st.form("password_form"):
        st.caption("Change your password")
        old_pw = st.text_input("Current password", type="password")
        new_pw = st.text_input("New password", type="password")
        new_pw2 = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Update Password", use_container_width=True):
            row = get_user_by_username(LOGGED_IN_USERNAME)
            if not row or not verify_password(old_pw, row.password_hash):
                st.error("Current password is incorrect.")
            elif len(new_pw) < 6:
                st.error("New password must be at least 6 characters.")
            elif new_pw != new_pw2:
                st.error("New passwords don't match.")
            else:
                change_password(LOGGED_IN_USER_ID, new_pw)
                st.success("Password updated.")

    st.markdown("---")
    st.subheader("🔐🔑 Two-Factor Authentication")
    if not PYOTP_AVAILABLE:
        st.caption("2FA requires the `pyotp` and `qrcode` packages — add them to requirements.txt to enable this.")
    else:
        totp_status = get_totp_status(LOGGED_IN_USER_ID)
        if totp_status and totp_status.totp_enabled:
            st.success("Two-factor authentication is **enabled** on your account.")
            if st.button("Disable 2FA", use_container_width=True):
                disable_totp(LOGGED_IN_USER_ID)
                st.success("2FA disabled.")
                st.rerun()
        else:
            st.caption("Add an extra layer of security — after your password, you'll also need a code from an authenticator app (Google Authenticator, Authy, etc.) to log in.")
            if "pending_totp_secret" not in st.session_state:
                st.session_state["pending_totp_secret"] = pyotp.random_base32()
            pending_secret = st.session_state["pending_totp_secret"]
            provisioning_uri = pyotp.TOTP(pending_secret).provisioning_uri(
                name=LOGGED_IN_USERNAME, issuer_name="Annual Smart Budget Tracker"
            )
            try:
                qr_img = qrcode.make(provisioning_uri)
                buf = _io_qr.BytesIO()
                qr_img.save(buf, format="PNG")
                st.image(buf.getvalue(), width=200, caption="Scan with your authenticator app")
            except Exception:
                st.caption(f"Manual entry key: `{pending_secret}`")
            confirm_code = st.text_input("Enter the 6-digit code from your app to confirm setup")
            if st.button("Enable 2FA", use_container_width=True):
                if pyotp.TOTP(pending_secret).verify(confirm_code.strip(), valid_window=1):
                    enable_totp(LOGGED_IN_USER_ID, pending_secret)
                    st.session_state.pop("pending_totp_secret", None)
                    st.success("2FA enabled — you'll need a code at every login from now on.")
                    st.rerun()
                else:
                    st.error("Code didn't match — try again.")

    st.markdown("---")
    st.subheader("⚠️ Delete Account")
    st.error(
        "This permanently deletes your account and ALL data — both Personal and Business "
        "books, every transaction, goal, and setting. This cannot be undone."
    )
    del_confirm_text = st.text_input(f"Type your username (\"{LOGGED_IN_USERNAME}\") to confirm deletion")
    if st.button("🗑️ Permanently Delete My Account", use_container_width=True):
        if del_confirm_text.strip() == LOGGED_IN_USERNAME:
            delete_user_and_all_data(LOGGED_IN_USER_ID)
            for k in list(st.session_state.keys()):
                st.session_state.pop(k, None)
            st.success("Account deleted.")
            st.rerun()
        else:
            st.error("Username didn't match — deletion cancelled.")

    st.markdown("---")
    st.subheader("🗄️ Data Management")
    col1, col2 = st.columns(2)
    with col1:
        st.caption(
            "Storage: **Postgres** (persists across restarts, safe for multiple simultaneous users)."
            if USING_POSTGRES else
            "Storage: **Local SQLite**. Fine for one person testing locally — not safe for multiple "
            "simultaneous users, and won't persist on ephemeral hosts. See README to switch to Postgres."
        )
        all_buf = io.StringIO()
        df_txn.to_csv(all_buf, index=False)
        st.download_button("⬇️ Download Transactions Backup (CSV)", all_buf.getvalue(),
                            file_name=f"{MODE.lower()}_transactions_backup_{date.today()}.csv", mime="text/csv")

        st.markdown("**📄 Accountant-Ready Report**")
        if not FPDF_AVAILABLE:
            st.caption("PDF export requires the `fpdf2` package — add it to requirements.txt to enable this.")
        else:
            _nw_summary = {"assets": tot_assets, "liabilities": tot_liab, "net_worth": net_worth}
            if st.button("Generate PDF Report", use_container_width=True):
                with st.spinner("Building your report..."):
                    pdf_bytes = generate_pdf_report(
                        MODE, USERNAME, currency, df_txn, breakdown_df, _nw_summary, budget_year
                    )
                if pdf_bytes:
                    st.download_button(
                        "⬇️ Download PDF Report", pdf_bytes,
                        file_name=f"{MODE.lower()}_financial_report_{date.today()}.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.error("Couldn't generate the PDF — check that fpdf2 is installed.")
    with col2:
        st.warning(f"Resetting clears all {MODE} transactions, debts, assets, and liabilities. This cannot be undone.")
        confirm = st.checkbox("I understand this will erase all data in this book")
        if st.button(f"🗑️ Reset {MODE} Data", disabled=(not confirm or ROLE != "Owner"), use_container_width=True):
            save_table(default_transactions(MODE), "transactions", USER_ID, MODE)
            save_table(default_debts(MODE), "debts", USER_ID, MODE)
            save_table(default_assets(MODE), "assets", USER_ID, MODE)
            save_table(default_liabilities(MODE), "liabilities", USER_ID, MODE)
            save_table(default_nw_history(), "networth_history", USER_ID, MODE)
            st.success(f"{MODE} data reset to defaults.")
            st.rerun()
        if ROLE != "Owner":
            st.caption("Only the book's owner can reset its data.")

    st.markdown("---")
    st.subheader("🤝 Sharing & Collaborators")
    st.caption(
        "Invite a bookkeeper, accountant, or business partner to this specific book. "
        "Viewers can see everything but can't add or edit. Editors can do everything "
        "except change book-wide settings, categories, or delete/reset data."
    )

    if VIEWING_OWN_BOOKS:
        with st.form("invite_form"):
            icol1, icol2, icol3 = st.columns([2, 1, 1])
            invite_username = icol1.text_input("Username to invite")
            invite_role = icol2.selectbox("Role", ["Viewer", "Editor"])
            invite_clicked = icol3.form_submit_button("Send Invite", use_container_width=True)
            if invite_clicked:
                msg = invite_collaborator(USER_ID, USERNAME, MODE, invite_username, invite_role)
                st.info(msg)

        existing_collabs = list_book_collaborators(USER_ID, MODE)
        if existing_collabs:
            st.markdown(f"**People with access to your {MODE} book:**")
            for _crow in existing_collabs:
                cc1, cc2, cc3 = st.columns([2, 1, 1])
                status = "✅ Accepted" if _crow.accepted else "⏳ Pending"
                cc1.markdown(f"{_crow.collaborator_username} — {_crow.role} ({status})")
                if cc3.button("Remove", key=f"remove_collab_{_crow.id}", use_container_width=True):
                    revoke_collaborator(_crow.id)
                    st.rerun()
        else:
            st.caption("No one else has access to this book yet.")
    else:
        st.caption(f"You're viewing {USERNAME}'s book as a collaborator — only the owner can manage sharing for it.")

    _my_pending = list_pending_invites(LOGGED_IN_USERNAME)
    if _my_pending:
        st.markdown("---")
        st.markdown("**📬 Invitations Waiting for You:**")
        for _prow in _my_pending:
            pc1, pc2, pc3 = st.columns([3, 1, 1])
            pc1.markdown(f"**{_prow.owner_username}** invited you to their **{_prow.track}** book as **{_prow.role}**")
            if pc2.button("Accept", key=f"accept_{_prow.id}", use_container_width=True):
                respond_to_invite(_prow.id, accept=True)
                st.rerun()
            if pc3.button("Decline", key=f"decline_{_prow.id}", use_container_width=True):
                respond_to_invite(_prow.id, accept=False)
                st.rerun()

# ---------------------------------------------------------------------------
# TAB 7: ADMIN (only rendered for usernames listed in ADMIN_USERNAMES secret)
# ---------------------------------------------------------------------------
if IS_ADMIN and tab_admin is not None:
    with tab_admin:
        st.subheader("🛡️ Admin — License Keys, Users & Suspensions")
        st.caption(
            "Generate license keys per sales source, hand them to buyers however that "
            "platform delivers purchases, and they redeem the key once at signup. "
            "Gumroad sales are handled fully automatically if you've deployed the "
            "companion webhook_receiver.py — see README."
        )

        st.markdown("### Generate License Keys")
        with st.form("gen_keys_form"):
            gcol1, gcol2, gcol3 = st.columns(3)
            n_keys = gcol1.number_input("How many keys?", min_value=1, max_value=500, value=10, step=1)
            tier = gcol2.selectbox("Tier", ["standard", "premium"])
            source = gcol3.selectbox("Sales Source", ["Gumroad", "Etsy", "Facebook", "X (Twitter)", "Instagram", "TikTok", "Direct", "Other"])
            notes = st.text_input("Notes (optional — e.g. campaign name)")
            if st.form_submit_button("Generate Keys", use_container_width=True):
                new_keys = create_license_keys(int(n_keys), tier, source, notes)
                st.success(f"Generated {len(new_keys)} key(s).")
                st.code("\n".join(new_keys))
                keys_csv = "license_key\n" + "\n".join(new_keys)
                st.download_button("⬇️ Download as CSV", keys_csv,
                                    file_name=f"license_keys_{source}_{date.today()}.csv", mime="text/csv")

        st.markdown("---")
        st.markdown("### All License Keys")
        with ENGINE.connect() as conn:
            keys_df = pd.read_sql(sa.text(
                "SELECT license_key, tier, source, created_at, redeemed_by_username, "
                "redeemed_at, revoked, external_sale_id, notes FROM license_keys ORDER BY created_at DESC"
            ), conn)
        status_filter = st.radio("Filter", ["All", "Unused", "Used", "Revoked"], horizontal=True)
        view_df = keys_df.copy()
        if not view_df.empty:
            revoked_bool = view_df["revoked"].astype(bool)
            if status_filter == "Unused":
                view_df = view_df[view_df["redeemed_by_username"].isna() & (~revoked_bool)]
            elif status_filter == "Used":
                view_df = view_df[view_df["redeemed_by_username"].notna()]
            elif status_filter == "Revoked":
                view_df = view_df[revoked_bool]
        st.dataframe(view_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### Revoke a Key")
        st.caption(
            "Use this for refunds or chargebacks on manually-issued keys (Etsy, Facebook, etc.). "
            "Gumroad refunds handled via the webhook do this automatically — no action needed here for those."
        )
        revoke_col1, revoke_col2 = st.columns([3, 1])
        revoke_input = revoke_col1.text_input("License key to revoke", label_visibility="collapsed",
                                               placeholder="XXXX-XXXX-XXXX-XXXX")
        cascade_suspend = st.checkbox(
            "Also suspend the user who redeemed this key (recommended — closes access immediately)",
            value=True,
        )
        if revoke_col2.button("Revoke", use_container_width=True):
            result_msg = revoke_key_and_maybe_suspend(revoke_input, cascade_suspend)
            st.success(result_msg)
            st.rerun()

        st.markdown("---")
        st.markdown("### Suspend / Reactivate a User Directly")
        st.caption("For any case not covered by a key revocation — e.g. abuse, a manual refund you processed elsewhere.")
        susp_col1, susp_col2, susp_col3 = st.columns([2, 1, 1])
        target_username = susp_col1.text_input("Username", label_visibility="collapsed", placeholder="username")
        if susp_col2.button("Suspend", use_container_width=True):
            if target_username.strip():
                set_user_active(target_username, False)
                st.success(f"'{target_username.strip()}' suspended.")
                st.rerun()
        if susp_col3.button("Reactivate", use_container_width=True):
            if target_username.strip():
                set_user_active(target_username, True)
                st.success(f"'{target_username.strip()}' reactivated.")
                st.rerun()

        st.markdown("---")
        st.markdown("### Users")
        with ENGINE.connect() as conn:
            users_df = pd.read_sql(sa.text(
                "SELECT id, username, email, is_active, created_at FROM users ORDER BY created_at DESC"
            ), conn)
        active_count = int(users_df["is_active"].fillna(1).astype(int).sum()) if not users_df.empty else 0
        ucol1, ucol2 = st.columns(2)
        ucol1.metric("Total Users", len(users_df))
        ucol2.metric("Active Users", active_count)
        st.dataframe(users_df, use_container_width=True, hide_index=True)
