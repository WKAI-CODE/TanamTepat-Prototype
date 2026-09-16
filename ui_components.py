"""
ui_components.py
-----------------
Shared, reusable interface components for TanamTepat.

Owned by: Prototype Member 1 (Farmer Module and Front-End)

This is the ONE place the visual design (colours, cards, hero header,
confirmation panel) lives. Every page/screen in the app should import
from here instead of redefining its own CSS, so the whole prototype
looks consistent — Coordinator Dashboard, Logistics Capacity, Weekly
Schedule, Emergency Recovery, etc. can all reuse these.

Other members: please don't copy-paste this CSS into your own pages.
Import the functions below instead. If you need a new shared component
(e.g. a warning banner for Emergency Recovery Mode), add it HERE and
tell the team, rather than styling it locally in your page file.
"""

import streamlit as st


def inject_global_css() -> None:
    """Injects the shared green agricultural theme. Call once per page,
    near the top, right after st.set_page_config()."""
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(180deg, #f4faf3 0%, #ffffff 250px);
        }

        .hero {
            background: linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%);
            padding: 2rem 2rem 1.6rem 2rem;
            border-radius: 18px;
            color: white;
            margin-bottom: 1.8rem;
            box-shadow: 0 8px 24px rgba(46, 125, 50, 0.25);
        }
        .hero h1 { color: white; margin-bottom: 0.2rem; font-size: 2rem; }
        .hero p { color: #eafaea; margin: 0; font-size: 0.98rem; }

        .section-card {
            background: white;
            border: 1px solid #e6efe6;
            border-radius: 14px;
            padding: 1.4rem 1.5rem 1rem 1.5rem;
            margin-bottom: 1.4rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }
        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #2e7d32;
            margin-bottom: 0.9rem;
        }

        div.stButton > button, div.stFormSubmitButton > button {
            background: linear-gradient(135deg, #2e7d32 0%, #43a047 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.65rem 1.4rem;
            font-weight: 600;
            width: 100%;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            box-shadow: 0 4px 12px rgba(46, 125, 50, 0.25);
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(46, 125, 50, 0.35);
        }

        .confirm-card {
            background: #f6fbf6;
            border: 1px solid #cfe8cf;
            border-radius: 14px;
            padding: 1.4rem 1.6rem;
            margin-top: 1rem;
        }
        .confirm-row {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px dashed #d8ecd8;
            font-size: 0.95rem;
        }
        .confirm-row:last-child { border-bottom: none; }
        .confirm-label { color: #558b58; font-weight: 600; }
        .confirm-value { color: #1b1b1b; font-weight: 500; text-align: right; }

        .status-pill {
            display: inline-block;
            background: #fff3cd;
            color: #8a6d00;
            padding: 0.2rem 0.75rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
        }

        section[data-testid="stSidebar"] {
            background-color: #f4faf3;
        }

        .feature-card {
            background: white;
            border: 1px solid #e6efe6;
            border-radius: 14px;
            padding: 1.3rem 1.1rem;
            text-align: center;
            height: 100%;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .feature-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(46, 125, 50, 0.12);
        }
        .feature-icon { font-size: 1.8rem; margin-bottom: 0.4rem; }
        .feature-title { font-weight: 700; color: #2e7d32; margin-bottom: 0.4rem; font-size: 1rem; }
        .feature-desc { color: #555; font-size: 0.85rem; line-height: 1.4; }
        .feature-tag {
            display: inline-block;
            margin-top: 0.7rem;
            background: #eafaea;
            color: #2e7d32;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.15rem 0.6rem;
            border-radius: 999px;
        }

        .stat-pill {
            background: #f6fbf6;
            border: 1px solid #cfe8cf;
            border-radius: 12px;
            padding: 0.9rem 0.5rem;
            text-align: center;
        }
        .stat-value { font-size: 1.4rem; font-weight: 800; color: #2e7d32; }
        .stat-label { font-size: 0.75rem; color: #558b58; margin-top: 0.15rem; }

        /* Call-to-action page links (role choices on the main page).
           Only links placed inside a .cta-farmer / .cta-coord marker are
           restyled, so the sidebar's automatic page navigation is untouched. */
        .cta-farmer + div a[data-testid="stPageLink-NavLink"],
        .cta-coord  + div a[data-testid="stPageLink-NavLink"] {
            display: flex;
            justify-content: center;
            border-radius: 10px;
            padding: 0.7rem 1.2rem;
            font-weight: 700;
            color: #ffffff !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.18);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .cta-farmer + div a[data-testid="stPageLink-NavLink"] {
            background: linear-gradient(135deg, #173F35 0%, #4F8A5B 100%);
        }
        .cta-coord + div a[data-testid="stPageLink-NavLink"] {
            background: linear-gradient(135deg, #2f6db5 0%, #3B82F6 100%);
        }
        .cta-farmer + div a[data-testid="stPageLink-NavLink"] p,
        .cta-coord  + div a[data-testid="stPageLink-NavLink"] p {
            color: #ffffff !important;
            font-weight: 700;
        }
        .cta-farmer + div a[data-testid="stPageLink-NavLink"]:hover,
        .cta-coord  + div a[data-testid="stPageLink-NavLink"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.28);
        }
    </style>
    """, unsafe_allow_html=True)


def hero_header(title: str, subtitle: str) -> None:
    """Renders the green gradient hero banner used at the top of every page."""
    st.markdown(f"""
    <div class="hero">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def feature_card(icon: str, title: str, description: str, tag: str | None = None) -> None:
    """Renders a compact feature/workflow-step card. Meant to be placed
    inside an st.columns() cell. tag (optional) shows a small badge like
    'Available now' or 'Coming soon'."""
    tag_html = f'<div class="feature-tag">{tag}</div>' if tag else ""
    st.markdown(f"""
    <div class="feature-card">
        <div class="feature-icon">{icon}</div>
        <div class="feature-title">{title}</div>
        <div class="feature-desc">{description}</div>
        {tag_html}
    </div>
    """, unsafe_allow_html=True)


def stat_pill(value: str, label: str) -> None:
    """Renders a single big-number stat, meant for an st.columns() row."""
    st.markdown(f"""
    <div class="stat-pill">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def section_card_open(title: str) -> None:
    """Opens a white card container with a section title.
    Must be paired with section_card_close().

    Note: the outer card div is opened AND the title is rendered in
    ONE st.markdown() call on purpose (the outer div is intentionally
    left unclosed here — section_card_close() closes it later).
    Streamlit wraps every individual st.markdown() call in its own
    spaced container, so splitting the div-open and the title into two
    separate calls creates a visible double gap before the card's
    first input. Keeping them in one call removes that extra gap."""
    st.markdown(
        f'<div class="section-card"><div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )


def section_card_close() -> None:
    """Closes a card container opened with section_card_open()."""
    st.markdown('</div>', unsafe_allow_html=True)


def confirmation_card(title: str, rows: list[tuple[str, str]], status: str | None = None) -> None:
    """Renders a label/value confirmation panel.

    rows: list of (label, value) pairs to display, in order.
    status: optional value shown as a highlighted pill on its own row.
    """
    rows_html = "".join(
        f'<div class="confirm-row"><span class="confirm-label">{label}</span>'
        f'<span class="confirm-value">{value}</span></div>'
        for label, value in rows
    )
    if status:
        rows_html += (
            '<div class="confirm-row"><span class="confirm-label">Status</span>'
            f'<span class="confirm-value"><span class="status-pill">{status}</span></span></div>'
        )
    st.markdown(f"""
    <div class="confirm-card">
        <div class="section-title">{title}</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Stage 2C additions: consistent status labels and page intros.
# These are presentation-only helpers so every page communicates status the
# same way. Status is NEVER communicated by colour alone — the emoji is always
# paired with words.
# --------------------------------------------------------------------------

# The four agreed status styles (emoji + text). Colour is decorative only;
# the text carries the meaning.
STATUS_STYLES = {
    "no_change":   "🟢 No change required",
    "review":      "🟡 Review and approval required",
    "cannot":      "🔴 Cannot schedule",
    "info":        "🔵 Information only",
}


def status_label(kind: str, extra_text: str = "") -> str:
    """
    Return a consistent status string (emoji + words) for one of the four
    agreed status kinds: "no_change", "review", "cannot", "info".

    Colour is never used alone — the returned string always includes words.
    An optional extra_text is appended after the standard label.
    """
    base = STATUS_STYLES.get(kind, STATUS_STYLES["info"])
    if extra_text:
        return f"{base} — {extra_text}"
    return base


def schedule_status_label(recommendation_status: str) -> str:
    """
    Map an engine recommendation_status to a friendly status label.

    Kept Original -> no change; Rescheduled -> review/approval;
    Unscheduled -> cannot schedule; anything else -> information only.
    This only relabels for DISPLAY; it does not change any stored value.
    """
    mapping = {
        "Kept Original": "no_change",
        "Rescheduled":   "review",
        "Unscheduled":   "cannot",
    }
    return status_label(mapping.get(str(recommendation_status), "info"))


def page_intro(title: str, one_sentence: str) -> None:
    """
    Render the shared page header plus a single-sentence explanation beneath
    the title. Use this at the top of every page for a consistent look.
    """
    hero_header(title, one_sentence)


# --------------------------------------------------------------------------
# Stage 2D additions: guided workflow strip and simple bordered cards.
# Presentation-only. No fake clickable HTML — these render static, styled
# blocks. Every status still pairs an icon with words elsewhere on the pages.
# --------------------------------------------------------------------------

# Malaysian agriculture palette (kept here so pages can reuse it).
COLOR_DARK_GREEN = "#173F35"
COLOR_LEAF_GREEN = "#4F8A5B"
COLOR_CREAM      = "#F7F4EA"
COLOR_AMBER      = "#E6A23C"
COLOR_RED        = "#D9534F"
COLOR_BLUE       = "#3B82F6"


def esc(value) -> str:
    """
    HTML-escape a dynamic value (farm name, crop, id, reason, etc.) before it
    is inserted into the trusted HTML templates used by info_card/change_card.
    Intentional formatting tags in the templates (<b>, <br>) are added by our
    own code AFTER escaping, so they are preserved; user text cannot inject markup.
    """
    import html
    return html.escape("" if value is None else str(value))


def workflow_steps(steps, current_index=-1, completed_indexes=None) -> None:
    """
    Render a small horizontal workflow guide. Each item in `steps` is a short
    label. This is a static visual guide, not clickable.

    Highlighting:
      - current_index: an int (single active step) OR a list/tuple/set of ints
        (several active steps). Use -1 or an empty list for no active step.
      - completed_indexes: optional iterable of steps to mark as completed
        (pale green with a check icon).

    Visual states (never colour alone — words/numbers/icons are always shown):
      - Active/current: solid green, white text, bold.
      - Completed: pale green, dark text, leading check icon.
      - Upcoming: white background, dark text.
    """
    # Normalise current_index to a set so one or many active steps both work.
    if isinstance(current_index, (list, tuple, set)):
        active = {int(i) for i in current_index}
    elif current_index is None or current_index < 0:
        active = set()
    else:
        active = {int(current_index)}

    completed = {int(i) for i in (completed_indexes or [])} - active

    cells = []
    for i, label in enumerate(steps):
        if i in active:
            bg, fg, border, weight, prefix = (
                COLOR_LEAF_GREEN, "#ffffff", COLOR_LEAF_GREEN, "700", ""
            )
        elif i in completed:
            bg, fg, border, weight, prefix = (
                "#e7f2e8", COLOR_DARK_GREEN, "#cfe8cf", "600", "✓ "
            )
        else:
            bg, fg, border, weight, prefix = (
                "#ffffff", COLOR_DARK_GREEN, "#e6efe6", "600", ""
            )
        cells.append(
            f'<div style="flex:1;min-width:120px;background:{bg};color:{fg};'
            f'border:1px solid {border};border-radius:12px;padding:0.6rem 0.7rem;'
            f'text-align:center;font-weight:{weight};font-size:0.88rem;">'
            f'{prefix}{i + 1}. {label}</div>'
        )
    arrow = ('<div style="display:flex;align-items:center;color:#9bbfa2;'
             'font-weight:700;padding:0 0.15rem;">→</div>')
    strip = arrow.join(cells)
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem;align-items:stretch;'
        f'margin:0.3rem 0 1rem 0;">{strip}</div>',
        unsafe_allow_html=True,
    )


def info_card(title: str, body_html: str, accent: str = COLOR_LEAF_GREEN) -> None:
    """
    Render a simple white bordered card with a left accent stripe. `body_html`
    is trusted, template-built HTML (never raw user input). Presentation only.
    """
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e6efe6;'
        f'border-left:5px solid {accent};border-radius:12px;padding:1rem 1.1rem;'
        f'margin-bottom:0.8rem;box-shadow:0 2px 8px rgba(0,0,0,0.04);">'
        f'<div style="font-weight:700;color:{COLOR_DARK_GREEN};margin-bottom:0.35rem;'
        f'font-size:1rem;">{title}</div>'
        f'<div style="color:#333;font-size:0.92rem;line-height:1.5;">{body_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def change_card(
    heading: str,
    original_text: str,
    recommended_text: str,
    reason_html: str,
    status_line: str,
    accent: str = COLOR_AMBER,
) -> None:
    """
    Render one collection-change as a bordered card with a clear
    'original → recommended' line. Used by the AI Schedule and Emergency
    Recovery pages so a single change is easy to notice. Presentation only.
    """
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e6efe6;'
        f'border-left:5px solid {accent};border-radius:12px;padding:1rem 1.1rem;'
        f'margin-bottom:0.8rem;box-shadow:0 2px 8px rgba(0,0,0,0.04);">'
        f'<div style="font-weight:700;color:{COLOR_DARK_GREEN};font-size:1rem;'
        f'margin-bottom:0.45rem;">{heading}</div>'
        f'<div style="font-size:0.95rem;color:#222;margin-bottom:0.35rem;">'
        f'<span style="color:#666;">{original_text}</span>'
        f'<span style="color:{COLOR_LEAF_GREEN};font-weight:700;padding:0 0.5rem;">→</span>'
        f'<span style="font-weight:700;">{recommended_text}</span></div>'
        f'<div style="color:#444;font-size:0.88rem;margin-bottom:0.4rem;">{reason_html}</div>'
        f'<div style="font-size:0.9rem;font-weight:600;">{status_line}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def role_card_header(icon: str, heading: str, text: str, kind: str) -> None:
    """
    Render a large role card (icon + heading + text) followed by a hidden CTA
    marker. The page MUST place a native st.page_link() immediately after this
    call — the marker's CSS turns that adjacent page link into a solid,
    obvious call-to-action button.

    kind: "farmer" (green accent) or "coord" (blue accent). The marker class
    (.cta-farmer / .cta-coord) selects the button colour via inject_global_css.
    Static values only (no user input), but kept simple and safe.
    """
    accent = COLOR_LEAF_GREEN if kind == "farmer" else COLOR_BLUE
    marker_class = "cta-farmer" if kind == "farmer" else "cta-coord"
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e6efe6;'
        f'border-top:6px solid {accent};border-radius:14px;'
        f'padding:1.3rem 1.2rem 0.6rem 1.2rem;margin-bottom:0.2rem;'
        f'box-shadow:0 3px 12px rgba(0,0,0,0.06);min-height:150px;">'
        f'<div style="font-size:2.4rem;line-height:1;margin-bottom:0.5rem;">{icon}</div>'
        f'<div style="font-weight:800;color:{COLOR_DARK_GREEN};font-size:1.2rem;'
        f'margin-bottom:0.3rem;">{heading}</div>'
        f'<div style="color:#444;font-size:0.95rem;line-height:1.5;">{text}</div>'
        f'</div>'
        f'<div class="{marker_class}"></div>',
        unsafe_allow_html=True,
    )
