import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from backend.sheets_service import get_sheets_service, get_all_rows
from backend.llm_chat import answer_question
from frontend.styles import (
    get_css, CHART_COLORS,
    stat_card, slabel, hd,
    you_msg, foot, get_plotly_layout
)

st.set_page_config(
    page_title="Job Application Tracker",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.markdown(get_css(), unsafe_allow_html=True)

HEADERS = [
    'ID', 'Company', 'Role', 'Location',
    'Date Applied', 'Date Responded', 'Days Taken',
    'Status', 'Interview Round', 'Source',
    'Email Thread ID', 'Notes'
]

ALL_COLS = [
    'ID', 'Company', 'Role', 'Location',
    'Date Applied', 'Date Responded', 'Days Taken',
    'Status', 'Source', 'Notes'
]

DEFAULT_COLS = [
    'ID', 'Company', 'Role', 'Location',
    'Date Applied', 'Date Responded', 'Days Taken', 'Status', 'Source'
]


# ─── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    try:
        import os
        from backend.config import get_service_account_file
        sa = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'NOT_FOUND')
        st.write(f"DEBUG SA starts with: {sa[:20]!r}")
        path = get_service_account_file()
        st.write(f"DEBUG path returned: {path!r}")
        sheets = get_sheets_service()
        rows = get_all_rows(sheets)
        if not rows:
            return pd.DataFrame(columns=HEADERS)
        padded = [r + [''] * (len(HEADERS) - len(r)) for r in rows]
        df = pd.DataFrame(padded, columns=HEADERS)
        df['Date Applied']   = pd.to_datetime(df['Date Applied'],   errors='coerce')
        df['Date Responded'] = pd.to_datetime(df['Date Responded'], errors='coerce')
        df['Days Taken']     = pd.to_numeric(df['Days Taken'],      errors='coerce')
        return df
    except Exception as e:
        st.error(f"Failed to load: {e}")
        return pd.DataFrame(columns=HEADERS)


def df_to_chat(df: pd.DataFrame) -> list:
    out = []
    for _, r in df.iterrows():
        out.append({
            'id': r['ID'], 'company': r['Company'], 'role': r['Role'],
            'location': r['Location'],
            'date_applied':   str(r['Date Applied'].date())   if pd.notna(r['Date Applied'])   else '',
            'date_responded': str(r['Date Responded'].date()) if pd.notna(r['Date Responded']) else '',
            'days_taken': int(r['Days Taken']) if pd.notna(r['Days Taken']) else None,
            'status': r['Status'], 'source': r['Source'], 'notes': r['Notes']
        })
    return out


def label(text: str) -> None:
    """Renders a small filter label above a widget."""
    st.markdown(
        f'<p style="color:#7A9CBF; font-size:0.73rem; font-family:IBM Plex Mono,monospace; '
        f'letter-spacing:1px; margin-bottom:4px; margin-top:2px;">{text}</p>',
        unsafe_allow_html=True
    )


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if 'chat_history'  not in st.session_state: st.session_state.chat_history  = []
    if 'last_q'        not in st.session_state: st.session_state.last_q        = ''
    if 'pending_q'     not in st.session_state: st.session_state.pending_q     = ''
    if 'visible_cols'  not in st.session_state: st.session_state.visible_cols  = DEFAULT_COLS.copy()
    if 'input_key'     not in st.session_state: st.session_state.input_key     = 0

    df = load_data()

    # ── Header ────────────────────────────────────────────────────────────────
    c_title, _, c_refresh = st.columns([5, 1, 1])
    with c_title:
        st.markdown('<div class="page-title">💼 Job Tracker</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="page-sub">LAST SYNCED · {datetime.now().strftime("%d %b %Y, %H:%M")}</div>',
            unsafe_allow_html=True
        )
    with c_refresh:
        st.markdown('<br>', unsafe_allow_html=True)
        if st.button("↻ Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown(hd(), unsafe_allow_html=True)

    # ── Chat ──────────────────────────────────────────────────────────────────
    st.markdown(slabel("🤖 &nbsp; Job Search Assistant"), unsafe_allow_html=True)

    st.markdown(
        '<p style="color:#3A5A7A; font-size:0.75rem; font-family:IBM Plex Mono,monospace; '
        'letter-spacing:1px; margin-bottom:8px;">⚡ QUICK QUESTIONS</p>',
        unsafe_allow_html=True
    )

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("📊 Last 7 days", use_container_width=True):
            st.session_state.pending_q = "Give me a summary of my job applications in the last 7 days"
            st.rerun()
    with b2:
        if st.button("❌ All rejections", use_container_width=True):
            st.session_state.pending_q = "Which companies rejected me? List them with dates"
            st.rerun()
    with b3:
        if st.button("⏱ Avg response time", use_container_width=True):
            st.session_state.pending_q = "What is my average response time from application to rejection or interview?"
            st.rerun()
    with b4:
        if st.button("🎯 Interview rate", use_container_width=True):
            st.session_state.pending_q = "What percentage of my applications led to interviews?"
            st.rerun()

    st.markdown(
        '<p style="color:#3A5A7A; font-size:0.75rem; font-family:IBM Plex Mono,monospace; '
        'letter-spacing:1px; margin-top:12px; margin-bottom:4px;">✏️ OR TYPE YOUR OWN</p>',
        unsafe_allow_html=True
    )

    user_input = st.text_input(
        "Ask anything",
        value=st.session_state.pending_q,
        placeholder="e.g. How many software engineer roles did I apply to this month?",
        label_visibility="collapsed",
        key=f"chat_input_{st.session_state.input_key}"
    )

    if st.session_state.pending_q:
        st.session_state.pending_q = ''

    if user_input and user_input != st.session_state.last_q:
        st.session_state.last_q = user_input
        st.session_state.input_key += 1  # forces input to reset/clear
        with st.spinner("Thinking..."):
            answer = answer_question(user_input, df_to_chat(df))
        st.session_state.chat_history.append({"q": user_input, "a": answer})
        st.rerun()

    # Chat history
    if st.session_state.chat_history:
        for chat in reversed(st.session_state.chat_history[-5:]):
            st.markdown(you_msg(chat['q']), unsafe_allow_html=True)
            st.markdown(f"""
            <div style="
                background: #1C3050;
                border: 1px solid #254570;
                border-left: 3px solid #38BDF8;
                border-radius: 0 12px 12px 12px;
                padding: 14px 18px;
                margin: 6px 10% 10px 0;
                color: #CBD5E1;
                font-size: 0.88rem;
                line-height: 1.7;
            ">
            <span style="font-family:IBM Plex Mono,monospace; font-size:0.6rem;
                letter-spacing:1.5px; color:#38BDF8; display:block; margin-bottom:8px;">
                🤖 ASSISTANT
            </span>
            {chat['a'].replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)

        col_clr, _ = st.columns([1, 5])
        with col_clr:
            if st.button("🗑 Clear chat", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.last_q = ''
                st.session_state.pending_q = ''
                st.rerun()

    st.markdown(hd(), unsafe_allow_html=True)

    # ── Stats ─────────────────────────────────────────────────────────────────
    st.markdown(slabel("📊 &nbsp; Overview"), unsafe_allow_html=True)

    if df.empty:
        st.info("No applications tracked yet!")
        return

    total      = len(df)
    pending    = len(df[df['Status'] == 'Applied'])
    rejected   = len(df[df['Status'] == 'Rejected'])
    interviews = len(df[df['Status'] == 'Interview'])
    offers     = len(df[df['Status'] == 'Offer'])
    responded  = rejected + interviews + offers
    rate       = f"{round(responded/total*100,1)}%" if total > 0 else "0%"

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: st.markdown(stat_card("Total",         total,      'total'),     unsafe_allow_html=True)
    with c2: st.markdown(stat_card("Pending",       pending,    'pending'),   unsafe_allow_html=True)
    with c3: st.markdown(stat_card("Rejected",      rejected,   'rejected'),  unsafe_allow_html=True)
    with c4: st.markdown(stat_card("Interviews",    interviews, 'interview'), unsafe_allow_html=True)
    with c5: st.markdown(stat_card("Offers",        offers,     'offer'),     unsafe_allow_html=True)
    with c6: st.markdown(stat_card("Response Rate", rate,       'rate'),      unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    cl, cr = st.columns(2)

    with cl:
        st.markdown(slabel("📈 &nbsp; Applications Per Day (Last 30 Days)"), unsafe_allow_html=True)
        cutoff = datetime.now() - timedelta(days=30)
        recent = df[df['Date Applied'] >= cutoff].copy()

        if not recent.empty:
            recent['Day'] = recent['Date Applied'].dt.strftime('%Y-%m-%d')
            counts = recent.groupby('Day').size().reset_index(name='Applications')
            counts['Day'] = pd.to_datetime(counts['Day'])
            counts = counts.sort_values('Day')

            fig = px.bar(counts, x='Day', y='Applications',
                         color_discrete_sequence=['#38BDF8'])
            layout = get_plotly_layout()
            layout['bargap'] = 0.35
            layout['xaxis'].update({
                'tickformat': '%d %b',
                'tickmode': 'array',
                'tickvals': counts['Day'].tolist(),
                'ticktext': counts['Day'].dt.strftime('%d %b').tolist(),
            })
            layout['yaxis'].update({'tickformat': 'd', 'dtick': 1})
            fig.update_layout(**layout)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No applications in the last 30 days")

    with cr:
        st.markdown(slabel("🥧 &nbsp; Status Breakdown"), unsafe_allow_html=True)
        sc = df['Status'].value_counts().reset_index()
        sc.columns = ['Status', 'Count']

        fig2 = px.pie(
            sc, values='Count', names='Status',
            color='Status', color_discrete_map=CHART_COLORS, hole=0.55
        )
        layout2 = get_plotly_layout()
        layout2['legend'] = dict(
            bgcolor='rgba(23,40,64,0.8)', bordercolor='#1B3050', borderwidth=1,
            font=dict(color='#7A9CBF', size=11),
            orientation='h', x=0.5, xanchor='center', y=-0.08, yanchor='top'
        )
        layout2['annotations'] = [dict(
            text=f'<b>{total}</b><br><span style="font-size:11px">apps</span>',
            x=0.5, y=0.5,
            font=dict(size=20, color='#E2EEFF', family='Syne'),
            showarrow=False
        )]
        layout2['margin'] = dict(l=10, r=10, t=16, b=50)
        fig2.update_layout(**layout2)
        fig2.update_traces(
            textfont_color='white', textfont_size=12,
            marker=dict(line=dict(color='#111f30', width=3))
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(hd(), unsafe_allow_html=True)

    # ── Table ─────────────────────────────────────────────────────────────────
    st.markdown(slabel("📋 &nbsp; Recent Applications"), unsafe_allow_html=True)

    # ── Column selector popover ───────────────────────────────────────────────
    with st.popover("⚙️ Choose Columns"):
        st.markdown(
            '<p style="color:#7A9CBF; font-size:0.73rem; font-family:IBM Plex Mono,monospace; '
            'margin-bottom:10px;">CHECK TO SHOW · UNCHECK TO HIDE</p>',
            unsafe_allow_html=True
        )
        new_vis = []
        # Two columns of checkboxes for compact layout
        cc1, cc2 = st.columns(2)
        for i, col in enumerate(ALL_COLS):
            checked = col in st.session_state.visible_cols
            target = cc1 if i % 2 == 0 else cc2
            with target:
                if st.checkbox(col, value=checked, key=f"col_chk_{col}"):
                    new_vis.append(col)
        # Always keep at least Company visible
        st.session_state.visible_cols = new_vis if new_vis else ['Company']

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([2, 2, 2])

    with f1:
        label("FILTER BY STATUS")
        status_filter = st.multiselect(
            "Status",
            options=["Applied", "Rejected", "Interview", "Offer"],
            default=[],
            placeholder="All statuses",
            label_visibility="collapsed"
        )

    with f2:
        label("DATE APPLIED — FROM (OPTIONAL)")
        date_applied_filter = st.date_input(
            "Date Applied",
            value=None,
            format="DD/MM/YYYY",
            label_visibility="collapsed",
            key="da_filter"
        )

    with f3:
        label("DATE RESPONDED — FROM (OPTIONAL)")
        date_responded_filter = st.date_input(
            "Date Responded",
            value=None,
            format="DD/MM/YYYY",
            label_visibility="collapsed",
            key="dr_filter"
        )

    # ── Row count ─────────────────────────────────────────────────────────────
    rc1, rc2, _ = st.columns([1, 1, 4])
    with rc1:
        label("SHOW ROWS")
        preset = st.selectbox(
            "Show rows",
            options=["10", "25", "50", "100", "All", "Custom"],
            index=0,
            label_visibility="collapsed"
        )
    with rc2:
        if preset == "Custom":
            label("ENTER NUMBER")
            custom_n = st.text_input("Custom", value="10", label_visibility="collapsed")
            try:
                num_rows = max(1, int(custom_n))
            except ValueError:
                num_rows = 10
        else:
            num_rows = None if preset == "All" else int(preset)

    # ── Prepare data ──────────────────────────────────────────────────────────
    # Always fetch all cols for filtering, show only selected at the end
    disp = df[[
        'ID', 'Company', 'Role', 'Location',
        'Date Applied', 'Date Responded', 'Days Taken',
        'Status', 'Source', 'Notes'
    ]].copy()

    # Remove rows with no company (truly empty rows)
    disp = disp[disp['Company'].str.strip() != '']

    # Status filter
    if status_filter:
        disp = disp[disp['Status'].isin(status_filter)]

    # Date Applied filter — only filter rows that HAVE a date applied
    if date_applied_filter is not None:
        ts = pd.Timestamp(date_applied_filter)
        # Only apply to rows where Date Applied exists
        has_date = disp['Date Applied'].notna()
        disp = disp[~has_date | (disp['Date Applied'] >= ts)]

    # Date Responded filter — only filter rows that HAVE a date responded
    if date_responded_filter is not None:
        ts = pd.Timestamp(date_responded_filter)
        # Only apply to rows where Date Responded exists
        has_date = disp['Date Responded'].notna()
        disp = disp[~has_date | (disp['Date Responded'] >= ts)]

    # Sort: most recent Date Applied first, NaT at bottom
    disp = disp.sort_values('Date Applied', ascending=False, na_position='last')

    total_filtered = len(disp)

    # Apply row limit
    if num_rows:
        disp = disp.head(num_rows)

    # Format display columns
    disp['Date Applied']   = disp['Date Applied'].dt.strftime('%d %b %Y')
    disp['Date Responded'] = disp['Date Responded'].dt.strftime('%d %b %Y')
    disp['Days Taken'] = disp['Days Taken'].apply(
        lambda x: f"{int(x)}d" if pd.notna(x) and str(x) not in ('', 'nan') else ''
    )
    disp = disp.fillna('').replace('NaT', '')

    # Apply column visibility
    vis = [c for c in st.session_state.visible_cols if c in disp.columns]
    if not vis:
        vis = DEFAULT_COLS
    disp = disp[vis]

    # Status coloring
    def color_status(val):
        return {
            'Applied':   'background-color:rgba(56,189,248,0.10);  color:#38BDF8; font-weight:600',
            'Rejected':  'background-color:rgba(248,113,113,0.10); color:#F87171; font-weight:600',
            'Interview': 'background-color:rgba(251,191,36,0.10);  color:#FBBF24; font-weight:600',
            'Offer':     'background-color:rgba(52,211,153,0.10);  color:#34D399; font-weight:600',
        }.get(val, '')

    styled = disp.style.applymap(color_status, subset=['Status']) \
        if 'Status' in vis else disp.style

    col_config = {}
    if 'Status' in vis:
        col_config['Status'] = st.column_config.SelectboxColumn(
            options=["Applied","Rejected","Interview","Offer"], width="small")
    if 'ID' in vis:
        col_config['ID'] = st.column_config.TextColumn(width="small")
    if 'Days Taken' in vis:
        col_config['Days Taken'] = st.column_config.TextColumn(width="small")
    if 'Date Applied' in vis:
        col_config['Date Applied'] = st.column_config.TextColumn(width="medium")
    if 'Date Responded' in vis:
        col_config['Date Responded'] = st.column_config.TextColumn(width="medium")
    if 'Notes' in vis:
        col_config['Notes'] = st.column_config.TextColumn(width="large")

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=min(500, max(100, (len(disp) + 1) * 35 + 38)),
        column_config=col_config
    )

    st.markdown(
        f'<p style="color:#3A5A7A; font-size:0.72rem; font-family:IBM Plex Mono,monospace; margin-top:6px;">'
        f'Showing {len(disp)} of {total_filtered} filtered · {len(df)} total · Most recent first</p>',
        unsafe_allow_html=True
    )

    st.markdown(foot(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()