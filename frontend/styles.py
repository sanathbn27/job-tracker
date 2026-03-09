# ─── Colors ───────────────────────────────────────────────────────────────────
CHART_COLORS = {
    'Applied':   '#38BDF8',
    'Rejected':  '#F87171',
    'Interview': '#FBBF24',
    'Offer':     '#34D399'
}

STAT_ACCENT_COLORS = {
    'total':     '#94A3B8',
    'pending':   '#38BDF8',
    'rejected':  '#F87171',
    'interview': '#FBBF24',
    'offer':     '#34D399',
    'rate':      '#C084FC',
}


def get_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500&family=Mulish:wght@400;500;600&display=swap');

:root {
    --bg:       #111f30;
    --card:     #172840;
    --deep:     #091525;
    --border:   #1B3050;
    --blight:   #254570;
    --t1:       #E2EEFF;
    --t2:       #7A9CBF;
    --t3:       #3A5A7A;
    --accent:   #38BDF8;
    --aglow:    rgba(56,189,248,0.10);
    --red:      #F87171;
    --amber:    #FBBF24;
    --green:    #34D399;
    --purple:   #C084FC;
}

html, body, [class*="css"] { font-family: 'Mulish', sans-serif !important; }

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main,
.main { background-color: var(--bg) !important; }

.block-container { padding: 2.5rem 3rem 4rem !important; max-width: 1440px !important; }
#MainMenu, footer, header { visibility: hidden; }

/* Title */
.page-title {
    font-family: 'Syne', sans-serif;
    font-size: 2rem; font-weight: 800;
    color: var(--t1); letter-spacing: -0.5px;
}
.page-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem; color: var(--t3);
    margin-top: 5px; letter-spacing: 1.5px;
}

/* Section labels */
.slabel {
    font-family: 'Syne', sans-serif;
    font-size: 0.78rem; font-weight: 700;
    letter-spacing: 2.5px; color: var(--t2);
    text-transform: uppercase;
    display: flex; align-items: center; gap: 10px;
    margin: 28px 0 14px;
}
.slabel::after {
    content: ''; flex: 1; height: 1px;
    background: var(--border);
}

/* Divider */
.hd { border: none; border-top: 1px solid var(--border); margin: 18px 0; }

/* Stat cards */
.stat-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-top: 3px solid var(--ac, var(--accent));
    border-radius: 12px;
    padding: 18px 20px;
}
.stat-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.63rem; color: var(--t3);
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 10px;
}
.stat-val {
    font-family: 'Syne', sans-serif;
    font-size: 2.1rem; font-weight: 700;
    color: var(--ac, var(--t1)); line-height: 1;
}

/* Chat container */
.chat-wrap {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 22px;
    margin-top: 8px;
}

/* Chat labels */
.you-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; letter-spacing: 1.5px;
    color: var(--accent); text-align: right;
    margin: 14px 0 4px;
}
.bot-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; letter-spacing: 1.5px;
    color: var(--t3);
    margin: 14px 0 4px;
}

/* Chat bubbles */
.you-bubble {
    background: #0F2A45;
    border: 1px solid #1E4A70;
    border-radius: 14px 14px 4px 14px;
    padding: 11px 16px;
    margin-left: 18%;
    color: #C8DEFF;
    font-size: 0.88rem;
    line-height: 1.55;
}
.bot-bubble {
    background: var(--deep);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 0 14px 14px 14px;
    padding: 12px 16px;
    margin-right: 10%;
    color: #B8D0E8;
    font-size: 0.88rem;
    line-height: 1.7;
}

/* Buttons */
.stButton > button {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--t2) !important;
    border-radius: 8px !important;
    font-family: 'Mulish', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    transition: all 0.15s !important;
    width: 100% !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--aglow) !important;
}

/* Input */
.stTextInput > div > div > input {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--t1) !important;
    font-family: 'Mulish', sans-serif !important;
    font-size: 0.875rem !important;
    padding: 12px 16px !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--aglow) !important;
}
.stTextInput > div > div > input::placeholder { color: var(--t3) !important; }

/* Table */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* Footer */
.foot {
    text-align: center; color: var(--t3);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem; letter-spacing: 2px;
    padding: 20px 0 6px;
}
</style>
"""


# ─── Components ───────────────────────────────────────────────────────────────

def stat_card(label: str, value, key: str) -> str:
    color = STAT_ACCENT_COLORS.get(key, '#38BDF8')
    return f'''<div class="stat-card" style="--ac:{color}">
        <div class="stat-lbl">{label}</div>
        <div class="stat-val">{value}</div>
    </div>'''

def slabel(text: str) -> str:
    return f'<div class="slabel">{text}</div>'

def hd() -> str:
    return '<hr class="hd">'

def you_msg(text: str) -> str:
    return f'<div class="you-lbl">YOU</div><div class="you-bubble">{text}</div>'

def bot_msg_open() -> str:
    return '<div class="bot-lbl">ASSISTANT</div><div class="bot-bubble">'

def bot_msg_close() -> str:
    return '</div>'

def foot() -> str:
    return '<div class="foot">JOB TRACKER &nbsp;·&nbsp; FASTAPI + GROQ + STREAMLIT</div>'

def get_plotly_layout(height: int = 300) -> dict:
    return dict(
        plot_bgcolor='#112236',
        paper_bgcolor='#112236',
        font=dict(family='IBM Plex Mono', color='#3A5A7A', size=11),
        margin=dict(l=10, r=10, t=16, b=10),
        height=height,
        xaxis=dict(gridcolor='#1B3050', showline=False, tickfont=dict(size=10)),
        yaxis=dict(gridcolor='#1B3050', showline=False, tickfont=dict(size=10)),
    )