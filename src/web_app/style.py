from datetime import date

import streamlit as st

CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 15% 20%, rgba(40, 26, 22, 0.85), transparent 55%),
        radial-gradient(ellipse at 85% 10%, rgba(232, 214, 206, 0.55), transparent 50%),
        radial-gradient(ellipse at 80% 90%, rgba(226, 200, 189, 0.75), transparent 55%),
        radial-gradient(ellipse at 10% 95%, rgba(150, 120, 110, 0.9), transparent 60%),
        #7A635C;
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.5rem; max-width: 560px; }

h1, h2, h3, h4 { font-weight: 300 !important; letter-spacing: 0.02em; }
.brand {
    text-align: center; font-size: 0.75rem; letter-spacing: 0.35em;
    text-transform: uppercase; color: rgba(255,255,255,0.75); margin-bottom: 1.2rem;
}

[data-testid="stTabs"] [role="tablist"] { justify-content: center; gap: 2rem; }
[data-testid="stTab"] p { color: rgba(255,255,255,0.65); }
[data-testid="stTab"][aria-selected="true"] p { color: #FFFFFF; }
[data-testid="stTab"] .react-aria-SelectionIndicator { background: #FFFFFF !important; }
[data-testid="stTab"] p {
    font-size: 0.78rem; letter-spacing: 0.2em; text-transform: uppercase;
}

[data-testid="stForm"], .st-key-enroll-card, .st-key-admin-card, .st-key-page-card, .st-key-account-card {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.45) !important;
    backdrop-filter: blur(6px);
    padding: 2rem 2.4rem 2.2rem 2.4rem;
}
.st-key-login-card [data-testid="stForm"],
.st-key-session-card [data-testid="stForm"] { padding-top: 4.2rem; }
.st-key-session-card p { text-align: center; }
.session-label {
    font-size: 0.72rem; letter-spacing: 0.25em; text-transform: uppercase;
    color: rgba(255,255,255,0.7); margin-bottom: 0.2rem;
}
.session-email { font-size: 1.15rem; color: #FFFFFF; margin-bottom: 0.2rem; }

.avatar {
    width: 104px; height: 104px; border-radius: 50%; margin: 1.2rem auto -52px auto;
    background: rgba(255, 255, 255, 0.28); position: relative; z-index: 2;
    display: flex; align-items: flex-end; justify-content: center; overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.35);
}

[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
[data-testid="stNumberInputContainer"], [data-testid="stDateInputField"],
[data-testid="stSelectbox"] [role="group"] {
    background: transparent !important;
    border-width: 0 0 1px 0 !important;
    border-style: solid !important;
    border-color: rgba(255, 255, 255, 0.75) !important;
    box-shadow: none !important;
}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within, [data-testid="stDateInputField"]:focus-within {
    border-color: #FFFFFF !important; border-bottom-width: 2px !important;
}
[data-testid="stTextInputField"], [data-testid="stNumberInputField"], textarea {
    background: transparent !important; color: #FFFFFF !important;
}
[data-testid="stTextInputField"]::placeholder, textarea::placeholder { color: rgba(255,255,255,0.75) !important; }
[data-testid="stTextInputIcon"] { color: rgba(255,255,255,0.85); }

[data-testid="stWidgetLabel"] p { font-size: 0.8rem; color: rgba(255,255,255,0.8); }

[data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button {
    background: #2B1913; border: none; color: #FFFFFF;
    letter-spacing: 0.25em; text-transform: uppercase; font-size: 0.78rem;
    padding: 0.75rem 0; margin-top: 0.8rem;
}
[data-testid="stFormSubmitButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
    background: #3D251C; color: #FFFFFF;
}

.section-title {
    font-size: 0.72rem; letter-spacing: 0.25em; text-transform: uppercase;
    color: #FFFFFF; margin: 1.6rem 0 0.1rem 0;
}
.section-title:first-child { margin-top: 0; }
.section-note { font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-bottom: 0.4rem; }
.hero-title {
    text-align: center; font-size: 2.6rem !important; font-weight: 300 !important;
    color: #FFFFFF; margin: 2.5rem 0 0.6rem 0;
}
.hero-lead {
    text-align: center; color: rgba(255,255,255,0.8); max-width: 440px;
    margin: 0 auto 2.5rem auto; line-height: 1.6;
}
.st-key-features { border-top: 1px solid rgba(255,255,255,0.35); padding-top: 1.4rem; margin-bottom: 1.6rem; }
.st-key-cta button {
    background: #2B1913; border: none; color: #FFFFFF;
    letter-spacing: 0.25em; text-transform: uppercase; font-size: 0.78rem; padding: 0.75rem 0;
}
.st-key-cta button:hover { background: #3D251C; color: #FFFFFF; }
.kv {
    display: flex; justify-content: space-between; gap: 1rem;
    padding: 0.45rem 0; border-bottom: 1px solid rgba(255,255,255,0.18); font-size: 0.92rem;
}
.kv span:first-child { color: rgba(255,255,255,0.65); }
.kv span:last-child { color: #FFFFFF; text-align: right; word-break: break-word; }
.footer {
    text-align: center; color: rgba(255,255,255,0.6); font-size: 0.72rem;
    letter-spacing: 0.08em; margin-top: 2.5rem;
}
</style>
"""

AVATAR = """
<div class="avatar">
  <svg width="78" height="84" viewBox="0 0 78 84" fill="rgba(255,255,255,0.55)">
    <circle cx="39" cy="28" r="18"/>
    <path d="M3 84c0-22 16-34 36-34s36 12 36 34z"/>
  </svg>
</div>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def avatar() -> None:
    st.markdown(AVATAR, unsafe_allow_html=True)


def section(title: str, note: str) -> None:
    st.markdown(
        f"<p class='section-title'>{title}</p><p class='section-note'>{note}</p>",
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        f"<p class='footer'>© {date.today().year} Nuu · Todos los derechos reservados</p>",
        unsafe_allow_html=True,
    )
