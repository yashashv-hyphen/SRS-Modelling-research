"""
Interactive SRS yield forecaster. Three tabs:
  • "Your yield forecast" — the full story for the one profile you set: a wealth-over-time
    forecast (median path plus unlucky→lucky band), why it moves the way it does (the tax rate
    you face, by age), then contribution/drawdown/after-window/early-exit detail.
  • "Compare incomes, returns & taxes" — how the SRS advantage moves across INCOME, MARKET
    RETURN, and the TAX FUTURE (the comparison the whole project is about), all shown at once.
  • "Withdrawal strategy lab" — every withdrawal rule played out on the identical simulated
    market path, so the only thing that changes is the rule itself.

Run with:  streamlit run srs_dashboard.py
All maths lives in srs_simulation.py / srs_model.py; this file only shows it. Results are cached
so moving a slider and re-running is fast after the first time. This is a simulated projection
under the assumptions you choose — not a guarantee, and not financial advice.
"""
import altair as alt
import pandas as pd
import streamlit as st

import srs_model as m
import srs_simulation as sim

st.set_page_config(page_title="Will SRS pay off for you?", page_icon=":material/savings:",
                   layout="wide")


# ---- theme-aware palette (emphasis form: one hue + gray; status green/red) ------------------
# Dark ink is invisible on a dark background, so detect the viewer's active theme and pick text
# and gridline colours that stay legible in both light and dark mode.
def _is_dark_theme():
    try:
        theme = st.context.theme
        if theme is not None and getattr(theme, "type", None):
            return theme.type == "dark"
    except Exception:
        pass
    return st.get_option("theme.base") == "dark"


DARK = _is_dark_theme()
BLUE = "#4c9be8" if DARK else "#2a78d6"   # the subject / highlighted line or bar
GRAY = "#5c5b57" if DARK else "#b7b6b0"   # context / "without SRS" bars and bands
GREEN = "#3ecf4a" if DARK else "#0ca30c"  # good verdict
RED = "#e8635f" if DARK else "#d03b3b"    # bad verdict
INK = "#e8e7e2" if DARK else "#33322f"    # label + title text
MUTED = "#a9a8a3" if DARK else "#52514e"  # secondary caption text
GRID = "#3a3a37" if DARK else "#e1e0d9"   # chart gridlines
# A red/green-free qualitative set for multi-strategy line charts, so "which strategy" is never
# confused with the good/bad status colours used elsewhere.
LINE_PALETTE = (["#4c9be8", "#e0a34c", "#b48ce0", "#5cd6c0"] if DARK else
                ["#2a78d6", "#c9791a", "#7a54b8", "#128a76"])

STRATEGY_LABELS = {
    "mpc": "Smart plan (MPC, re-planned yearly)",
    "static_level": "Fixed level (planned once, never revised)",
    "rule40": "$40k/yr rule of thumb",
    "fixed": "Your custom fixed amount",
}


# ---- formatting ---------------------------------------------------------------------------
def friendly(x):
    """Child-readable magnitude: $1.5M, $150k, $950."""
    ax = abs(x)
    sign = "-" if x < 0 else ""
    if ax >= 1_000_000:
        return f"{sign}${ax / 1_000_000:.2f}M"
    if ax >= 1_000:
        return f"{sign}${ax / 1_000:.0f}k"
    return f"{sign}${ax:,.0f}"


def esc(s):
    """Escape $ so Streamlit markdown doesn't read paired $…$ as LaTeX math."""
    return s.replace("$", "\\$")


def build_custom_brackets(edited_df, top_rate_pct):
    """Turn the sidebar's editable band table + top-rate box into an m.BRACKETS-shaped list,
    tolerating half-edited rows (dropped) and duplicate thresholds (last one typed wins)."""
    rows = []
    for _, row in edited_df.iterrows():
        try:
            upper = float(row["Up to income ($)"])
            rate = float(row["Rate (%)"]) / 100.0
        except (TypeError, ValueError):
            continue
        if upper > 0 and rate >= 0:
            rows.append((upper, max(0.0, min(1.0, rate))))
    rows.sort(key=lambda t: t[0])
    deduped, seen = [], set()
    for upper, rate in reversed(rows):          # keep the LAST typed rate for a repeated threshold
        if upper in seen:
            continue
        seen.add(upper)
        deduped.append((upper, rate))
    deduped.reverse()
    top = max(0.0, min(1.0, top_rate_pct / 100.0))
    if not deduped:
        return list(m.BRACKETS)
    return deduped + [(float("inf"), top)]


# ---- chart builders ------------------------------------------------------------------------
def hbar(df, title, highlight_value="__none__", height_per=52):
    """Horizontal bars: thin rounded marks, value printed at each end, one bar blue (the
    subject) and the rest gray, optional p10–p90 range whisker from 'lo'/'hi' columns."""
    df = df.copy()
    df["is_hi"] = df["label"] == highlight_value
    order = list(df["label"])
    ax_x = alt.X("value:Q", title=None, axis=alt.Axis(grid=True, gridColor=GRID,
                 domain=False, ticks=False, labels=False))
    bar = (alt.Chart(df).mark_bar(cornerRadiusEnd=4, height=28)
           .encode(y=alt.Y("label:N", sort=order, title=None,
                           axis=alt.Axis(labelLimit=360, labelFontSize=13, labelColor=INK)),
                   x=ax_x,
                   color=alt.condition("datum.is_hi", alt.value(BLUE), alt.value(GRAY)),
                   tooltip=[alt.Tooltip("label:N", title="Option"),
                            alt.Tooltip("value:Q", title="Value", format="$,.0f")]))
    layers = [bar]
    if "lo" in df.columns:
        layers.append(alt.Chart(df).mark_rule(color=INK, strokeWidth=1.5, opacity=0.5)
                      .encode(y=alt.Y("label:N", sort=order), x="lo:Q", x2="hi:Q"))
    layers.append(alt.Chart(df).mark_text(align="left", dx=6, fontSize=13, fontWeight="bold",
                  color=INK).encode(y=alt.Y("label:N", sort=order), x="value:Q", text="valuetext:N"))
    return (alt.layer(*layers)
            .properties(title=title, height=len(df) * height_per + 10, width="container")
            .configure_view(strokeWidth=0)
            .configure_title(fontSize=15, color=INK, anchor="start", offset=10))


def wealth_fan(df, title, vline_x, vline_label):
    """Two series ('With SRS' blue, 'Without SRS' gray), each a median line with a p10–p90
    band, over the full age axis; a dashed rule marks when the withdrawal window opens."""
    color_scale = alt.Scale(domain=["With SRS", "Without SRS"], range=[BLUE, GRAY])
    band = (alt.Chart(df).mark_area(opacity=0.18)
            .encode(x=alt.X("age:Q", title="Age"),
                    y=alt.Y("lo:Q", title=None, axis=alt.Axis(format="$,.0f", gridColor=GRID)),
                    y2="hi:Q", color=alt.Color("series:N", scale=color_scale, legend=None)))
    line = (alt.Chart(df).mark_line(strokeWidth=2.5)
            .encode(x="age:Q", y=alt.Y("median:Q", title=None),
                    color=alt.Color("series:N", scale=color_scale, title=None,
                                    legend=alt.Legend(orient="top", labelColor=INK, titleColor=INK)),
                    tooltip=[alt.Tooltip("age:Q", title="Age"), alt.Tooltip("series:N", title="Route"),
                             alt.Tooltip("median:Q", title="Median wealth", format="$,.0f"),
                             alt.Tooltip("lo:Q", title="Unlucky (p10)", format="$,.0f"),
                             alt.Tooltip("hi:Q", title="Lucky (p90)", format="$,.0f")]))
    rule = (alt.Chart(pd.DataFrame({"x": [vline_x]})).mark_rule(strokeDash=[4, 4], color=MUTED)
            .encode(x="x:Q"))
    rule_label = (alt.Chart(pd.DataFrame({"x": [vline_x], "y": [df["hi"].max()], "t": [vline_label]}))
                  .mark_text(align="left", dx=6, dy=-4, color=MUTED, fontSize=11)
                  .encode(x="x:Q", y="y:Q", text="t:N"))
    return (alt.layer(band, line, rule, rule_label)
            .properties(title=title, height=340, width="container")
            .configure_view(strokeWidth=0)
            .configure_title(fontSize=15, color=INK, anchor="start", offset=10)
            .configure_axis(labelColor=INK, titleColor=INK, gridColor=GRID))


def sweep_line(df, title, x_title, x_fmt="$,.0f"):
    """Continuous sweep: one median line with a p10–p90 band, plus a filled dot + label at the
    row flagged is_hi=True (the user's own current setting on the curve)."""
    ax_x = alt.X("x:Q", title=x_title, axis=alt.Axis(format=x_fmt, labelColor=INK, titleColor=INK))
    band = (alt.Chart(df).mark_area(color=BLUE, opacity=0.15)
            .encode(x=ax_x, y=alt.Y("lo:Q", title=None, axis=alt.Axis(format="$,.0f")), y2="hi:Q"))
    line = (alt.Chart(df).mark_line(color=BLUE, strokeWidth=2.5, point=True)
            .encode(x=ax_x, y=alt.Y("median:Q", title=None),
                    tooltip=[alt.Tooltip("x:Q", title=x_title, format=x_fmt),
                             alt.Tooltip("median:Q", title="Median advantage", format="$,.0f"),
                             alt.Tooltip("lo:Q", title="Unlucky (p10)", format="$,.0f"),
                             alt.Tooltip("hi:Q", title="Lucky (p90)", format="$,.0f")]))
    hi = df[df["is_hi"]]
    mark = (alt.Chart(hi).mark_point(color=BLUE, size=130, filled=True, stroke=INK, strokeWidth=1.5)
            .encode(x=ax_x, y="median:Q"))
    label = (alt.Chart(hi).mark_text(dy=-16, fontWeight="bold", fontSize=12, color=INK)
             .encode(x=ax_x, y="median:Q", text="valuetext:N"))
    return (alt.layer(band, line, mark, label)
            .properties(title=title, height=280, width="container")
            .configure_view(strokeWidth=0)
            .configure_title(fontSize=15, color=INK, anchor="start", offset=10)
            .configure_axis(labelColor=INK, titleColor=INK, gridColor=GRID))


def strategy_lines(df, title, highlight):
    """One line per withdrawal strategy over the drawdown years, same realised market path,
    the user's chosen strategy drawn thicker and fully opaque."""
    labels = list(df["strategy"].unique())
    palette = (LINE_PALETTE * ((len(labels) // len(LINE_PALETTE)) + 1))[:len(labels)]
    color_scale = alt.Scale(domain=labels, range=palette)
    df = df.copy()
    df["is_hi"] = df["strategy"] == highlight
    line = (alt.Chart(df).mark_line(point=True)
            .encode(x=alt.X("age:Q", title="Age"),
                    y=alt.Y("balance:Q", title=None, axis=alt.Axis(format="$,.0f", gridColor=GRID)),
                    color=alt.Color("strategy:N", scale=color_scale, title=None,
                                    legend=alt.Legend(orient="top", labelColor=INK, columns=2)),
                    strokeWidth=alt.condition("datum.is_hi", alt.value(3.5), alt.value(1.5)),
                    opacity=alt.condition("datum.is_hi", alt.value(1.0), alt.value(0.55)),
                    tooltip=[alt.Tooltip("age:Q", title="Age"), alt.Tooltip("strategy:N", title="Rule"),
                             alt.Tooltip("balance:Q", title="Still in SRS", format="$,.0f")]))
    return (line.properties(title=title, height=320, width="container")
            .configure_view(strokeWidth=0)
            .configure_title(fontSize=15, color=INK, anchor="start", offset=10)
            .configure_axis(labelColor=INK, titleColor=INK, gridColor=GRID))


def rate_line(df, title, vline_x):
    line = (alt.Chart(df).mark_line(color=BLUE, strokeWidth=2.5, point=True)
            .encode(x=alt.X("age:Q", title="Age"),
                    y=alt.Y("rate:Q", title=None, axis=alt.Axis(format=".0%", gridColor=GRID)),
                    tooltip=[alt.Tooltip("age:Q", title="Age"),
                             alt.Tooltip("rate:Q", title="Marginal rate", format=".1%")]))
    rule = (alt.Chart(pd.DataFrame({"x": [vline_x]})).mark_rule(strokeDash=[4, 4], color=MUTED)
            .encode(x="x:Q"))
    return (alt.layer(line, rule)
            .properties(title=title, height=220, width="container")
            .configure_view(strokeWidth=0)
            .configure_title(fontSize=15, color=INK, anchor="start", offset=10)
            .configure_axis(labelColor=INK, titleColor=INK, gridColor=GRID))


# ---- cached compute (so re-runs are instant) ----------------------------------------------
@st.cache_data(show_spinner=False)
def one_profile(chargeable, n_paths, seed, contribution, mean_return, vol, wage_growth,
                shock_prob, death_extra_years, base_brackets, drawdown_strategy,
                drawdown_fixed_amount, use_dp, return_mode, historical_block_size):
    return sim.simulate_portfolio(chargeable, n_paths=n_paths, seed=seed, contribution=contribution,
                                  mean_return=mean_return, vol=vol, wage_growth=wage_growth,
                                  shock_prob=shock_prob, death_extra_years=death_extra_years,
                                  base_brackets=base_brackets, drawdown_strategy=drawdown_strategy,
                                  drawdown_fixed_amount=drawdown_fixed_amount, use_dp=use_dp,
                                  return_mode=return_mode,
                                  historical_block_size=historical_block_size)


@st.cache_data(show_spinner=False)
def sweep_income(incomes, n_paths, seed, contribution, mean_return, vol, wage_growth, shock_prob,
                 dey, base_brackets, return_mode, historical_block_size):
    return sim.advantage_by_income(incomes=incomes, n_paths=n_paths, seed=seed,
                                   contribution=contribution, mean_return=mean_return, vol=vol,
                                   wage_growth=wage_growth, shock_prob=shock_prob,
                                   death_extra_years=dey, base_brackets=base_brackets,
                                   return_mode=return_mode,
                                   historical_block_size=historical_block_size)


@st.cache_data(show_spinner=False)
def sweep_return(return_grid, chargeable, n_paths, seed, contribution, vol, wage_growth,
                 shock_prob, dey, base_brackets):
    return sim.advantage_by_return(return_grid=return_grid, chargeable=chargeable, n_paths=n_paths,
                                   seed=seed, contribution=contribution, vol=vol,
                                   wage_growth=wage_growth, shock_prob=shock_prob,
                                   death_extra_years=dey, base_brackets=base_brackets)


@st.cache_data(show_spinner=False)
def sweep_tax(chargeable, wage_growth, shock_prob, n_paths, seed, contribution, mean_return, vol,
             dey, base_brackets, return_mode, historical_block_size):
    return sim.advantage_by_tax_regime(chargeable=chargeable, wage_growth=wage_growth,
                                       shock_prob=shock_prob, n_paths=n_paths, seed=seed,
                                       contribution=contribution, mean_return=mean_return,
                                       vol=vol, death_extra_years=dey, base_brackets=base_brackets,
                                       return_mode=return_mode,
                                       historical_block_size=historical_block_size)


def _residual_tax(balance, brackets):
    return m.tax(m.INCLUSION * balance, brackets) - m.tax(0.0, brackets)


# ---- sidebar: the inputs, in plain words --------------------------------------------------
with st.sidebar:
    st.header("Tell me about you")
    annual_income = st.number_input(
        "Your annual income (gross salary)", min_value=0, max_value=5_000_000,
        value=140_200, step=1_000, format="%d",
        help="Your gross pay before any reliefs — the number on your payslip, not your tax "
             "bill. CPF relief and the earned-income relief are worked out for you below.")
    chargeable = m.chargeable_from_gross(annual_income)
    st.caption(f"≈ **${chargeable:,.0f}** chargeable income, after an estimated "
              f"${annual_income - chargeable:,.0f} of CPF relief and the $1,000 earned-income "
              f"relief — this is the number your tax (and SRS relief) is actually computed on.")
    contribution_caps = {"$15,300 — Citizen / PR": m.CAP_CITIZEN, "$35,700 — Foreigner": m.CAP_FOREIGN}
    contribution_label = st.segmented_control(
        "How much can you pay in each year?", options=list(contribution_caps),
        default=next(iter(contribution_caps)))
    contribution = contribution_caps[contribution_label or next(iter(contribution_caps))]

    st.header("The market (nobody knows these)")
    market_mode = st.segmented_control(
        "Model the market using", options=["Your own assumptions", "Real market history"],
        default="Your own assumptions",
        help="'Your own assumptions' draws each year's return from a bell-curve-like "
             "distribution centred on the two sliders below. 'Real market history' instead "
             "replays actual years from a long real return series, in multi-year chunks, so "
             "real booms and crashes (and their clustering) show up instead of a smooth "
             "statistical approximation of them.")
    return_mode = "historical" if market_mode == "Real market history" else "parametric"
    if return_mode == "parametric":
        mean_return = st.slider("Average yearly return", 0.0, 12.0, 5.0, 0.5, format="%.1f%%",
                                help="What your investments grow by per year, on average.") / 100.0
        vol = st.slider("How bumpy the ride is", 0, 35, 15, 1, format="%d%%",
                        help="Bigger = wilder ups and downs each year. 0% = the same return "
                             "every year.") / 100.0
        historical_block_size = 5
    else:
        # Planning numbers (e.g. the forecast pot used for "is the next dollar worth it?")
        # still need a single mean_return/vol pair; use the dataset's own realised figures so
        # they're consistent with what's about to be replayed, not an unrelated guess.
        mean_return, vol = sim.HISTORICAL_MEAN, sim.HISTORICAL_VOL
        historical_block_size = st.slider(
            "Replay history in chunks of", 1, 15, 5, 1, format="%d years",
            help="A single real year at a time loses the clustering that makes bad luck bad — "
                 "a crash year tends to be followed by another rough one. Chunks keep a real "
                 "run of consecutive years intact; only where one chunk ends and an unrelated "
                 "one begins is there an artificial seam.")
        st.caption(esc(
            f"Replaying real S&P 500 total returns, 1928–2025 (98 years, average "
            f"{sim.HISTORICAL_MEAN*100:.1f}%/yr, ±{sim.HISTORICAL_VOL*100:.1f}%/yr) — source: "
            f"A. Damodaran, NYU Stern. A single-country (US) nominal equity series, not a "
            f"calibration to SRS-eligible instruments or the Singapore market specifically; "
            f"past returns are not a guide to future ones."))

    st.header("How you'd take it out")
    strategy_key = st.selectbox(
        "Withdrawal strategy for the 10-year window", options=list(STRATEGY_LABELS),
        format_func=lambda k: STRATEGY_LABELS[k],
        help="How much to withdraw each year once the window opens. Only 'Smart plan' reacts "
             "to that year's actual return and tax rates; the rest follow a fixed rule.")
    use_dp = False
    if strategy_key == "mpc":
        use_dp = st.checkbox("Solve the smart plan exactly (slower, more precise)", value=False,
                             help="Off uses a fast closed-form shortcut that's provably optimal "
                                  "for a flat forecast. On solves a full backward dynamic "
                                  "program instead — same answer, just slower.")
    fixed_amount = None
    if strategy_key == "fixed":
        fixed_amount = st.number_input("Your fixed amount per year ($)", min_value=1_000,
                                       max_value=1_000_000, value=60_000, step=5_000)

    st.header("Tax rates — change them yourself")
    with st.expander("✏️ Edit the tax brackets", expanded=False):
        st.caption("Change any threshold or rate to explore a different tax world (e.g. a "
                  "future rate hike). Add or delete rows freely — this replaces the IRAS "
                  "YA2026 schedule everywhere in the app.")
        if "bracket_version" not in st.session_state:
            st.session_state["bracket_version"] = 0
        if st.button("Reset to IRAS YA2026 rates"):
            st.session_state["bracket_version"] += 1
            st.rerun()
        default_bands = pd.DataFrame([{"Up to income ($)": u, "Rate (%)": r * 100}
                                      for u, r in m.BRACKETS[:-1]])
        edited_bands = st.data_editor(
            default_bands, num_rows="dynamic", width="stretch", hide_index=True,
            key=f"bracket_editor_{st.session_state['bracket_version']}",
            column_config={
                "Up to income ($)": st.column_config.NumberColumn(min_value=0, step=1000, format="%d"),
                "Rate (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.5,
                                                          format="%.2f"),
            })
        top_rate_pct = st.number_input(
            "Top rate (%) — for everything above the highest row above",
            min_value=0.0, max_value=100.0, value=m.BRACKETS[-1][1] * 100, step=0.5)
    custom_brackets = tuple(build_custom_brackets(edited_bands, top_rate_pct))

    st.header("Is your next dollar worth it?")
    # Same test as tab 1 section 2, but computed directly (no simulation) so it updates live
    # as you move sliders. Uses the project's standard 29-year contribution / 10-year drawdown
    # horizon (m.run()'s defaults) since the sidebar has no age input.
    _relief_rate = m.relief_value(chargeable, contribution, custom_brackets) / contribution
    _projected_pot = m.fv_annuity(contribution, mean_return, 29)
    _breakeven_tc = m.breakeven_tc(_projected_pot, mean_return, 10, brackets=custom_brackets)
    if _relief_rate > _breakeven_tc:
        st.success(f"Worth it — saves {_relief_rate*100:.0f}¢ now, costs {_breakeven_tc*100:.1f}¢ "
                   "later.", icon=":material/check_circle:")
    else:
        st.error(f"Not worth it — saves only {_relief_rate*100:.0f}¢ now, will cost "
                 f"{_breakeven_tc*100:.1f}¢ later.", icon=":material/error:")

    st.header("...and how they might drift over time")
    wage_growth = st.slider("Your pay rises by, per year", 0.0, 6.0, 2.0, 0.5, format="%.1f%%",
                            help="Tax bands don't move with inflation, so a rising salary drifts "
                                 "into higher bands over time.") / 100.0
    shock_prob = st.slider("Chance of a tax-rate change, each year", 0, 15, 3, 1,
                           format="%d%%") / 100.0

    st.header("Later life")
    death_age = st.slider("Plan up to age", 74, 100, sim.DEFAULT_DEATH_AGE)
    dey = max(0, death_age - (sim.RETIREMENT_AGE + 10))

    st.header("How careful a simulation")
    n_paths = st.slider("Number of possible futures to try", 50, 2000, 300, 50)
    seed = st.number_input("Luck seed (same number = same random futures)", value=42, step=1)

st.title("Will SRS pay off for you?")
st.caption(
    "A yield forecaster for Singapore's Supplementary Retirement Scheme: contribute, get a tax "
    "discount now, pay tax on only half of what you withdraw later. Set your income, your "
    "market outlook, your own tax-rate scenario and your withdrawal rule on the left; this tool "
    "plays out thousands of simulated futures — the market rising and falling, tax rates "
    "drifting or shocked — and reports the odds and size of the payoff.")
st.info("This is a simulated projection under the assumptions **you** choose on the left — not "
       "a guarantee, and not financial advice.", icon="ℹ️")

p = dict(
    chargeable=chargeable, n_paths=int(n_paths), seed=int(seed), contribution=contribution,
    mean_return=mean_return, vol=vol, wage_growth=wage_growth, shock_prob=shock_prob,
    dey=dey, death_age=death_age, base_brackets=custom_brackets,
    drawdown_strategy=strategy_key, drawdown_fixed_amount=fixed_amount, use_dp=use_dp,
    return_mode=return_mode, historical_block_size=historical_block_size)

tab_zoom, tab_compare, tab_strategy = st.tabs([
    ":material/trending_up: Your yield forecast",
    ":material/query_stats: Compare incomes, returns & taxes",
    ":material/tune: Withdrawal strategy lab"],
    on_change="rerun")

# ============================================================ TAB 1: ONE PROFILE ==============
if tab_zoom.open:
    with tab_zoom:
        with st.spinner("Playing out the futures for this profile…"):
            result = one_profile(p["chargeable"], p["n_paths"], p["seed"], p["contribution"],
                                 p["mean_return"], p["vol"], p["wage_growth"], p["shock_prob"],
                                 p["dey"], p["base_brackets"], p["drawdown_strategy"],
                                 p["drawdown_fixed_amount"], p["use_dp"], p["return_mode"],
                                 p["historical_block_size"])
        s = result["summary"]
        median = result["median_path"]
        death_age = p["death_age"]
        income = p["chargeable"]
        contrib_years = len(median["yearly_contributions"])
        draw_years = len(median["mpc_drawdown"]["withdrawals"])
        start_age = sim.RETIREMENT_AGE - contrib_years

        # --- bottom line
        adv = s["advantage"]
        good = adv["median"] > 0
        color = GREEN if good else RED
        verdict = "Worth it ✅" if good else "Not worth it ❌"
        st.markdown(f"""
            <div style="text-align:center; padding:14px 0 4px;">
              <div style="font-size:15px; color:{MUTED};">Using SRS makes you about</div>
              <div style="font-size:56px; font-weight:700; line-height:1.05; color:{color};">
                {friendly(adv['median']).replace('$', '&#36;')}</div>
              <div style="font-size:17px; color:{MUTED};">richer by the end &nbsp;·&nbsp; <b>{verdict}</b></div>
            </div>""", unsafe_allow_html=True)
        st.markdown(esc(f"For **${income:,.0f}** chargeable income. Depending on luck, between "
                        f"**{friendly(adv['p10'])}** (unlucky) and **{friendly(adv['p90'])}** (lucky), "
                        f"across {s['n_paths']} simulated lifetimes — SRS came out ahead in "
                        f"**{s['prob_srs_wins']*100:.0f}%** of them."))
        st.divider()

        # --- the journey: wealth over the whole plan
        st.subheader("The journey — your wealth over the whole plan")
        wp_with, wp_without = s["wealth_with_srs_path"], s["wealth_without_srs_path"]
        traj_rows = []
        for i in range(contrib_years + draw_years):
            age = start_age + i + 1
            traj_rows.append({"age": age, "series": "With SRS", "median": wp_with["median"][i],
                              "lo": wp_with["p10"][i], "hi": wp_with["p90"][i]})
            traj_rows.append({"age": age, "series": "Without SRS", "median": wp_without["median"][i],
                              "lo": wp_without["p10"][i], "hi": wp_without["p90"][i]})
        df_traj = pd.DataFrame(traj_rows)
        st.altair_chart(wealth_fan(df_traj, "Simulated wealth by age — median path, unlucky→lucky band",
                                  vline_x=start_age + contrib_years + 0.5,
                                  vline_label=f" age {start_age + contrib_years}: withdrawals start"),
                        width="stretch")
        st.caption(esc(
            f"Blue = with SRS; gray = investing the same out-of-pocket cash normally instead. The "
            f"solid line is the middle (median) outcome across all {s['n_paths']} simulated futures; "
            f"the shaded band is the unlucky-to-lucky (10th–90th percentile) range — hover a line for "
            f"exact numbers. The dashed marker is age {start_age + contrib_years}, when contributions "
            f"stop and the mandatory 10-year withdrawal window opens."))

        # --- why: the tax rate faced over time
        st.subheader("Why it moves the way it does — the tax rate you face, by age")
        rate_rows = [{"age": start_age + y["year"], "rate": y["top_marginal_rate"]}
                    for y in median["yearly_contributions"]]
        rate_rows += [{"age": start_age + contrib_years + i + 1, "rate": r}
                     for i, r in enumerate(median["mpc_drawdown"]["marginal_rate_path"])]
        df_rate = pd.DataFrame(rate_rows)
        st.altair_chart(rate_line(df_rate, "Marginal tax rate faced each year, this simulated path",
                                  vline_x=start_age + contrib_years + 0.5), width="stretch")
        st.caption(esc(
            "Left of the dashed line: the marginal rate on your ordinary income that year, as "
            "bracket creep and any policy shocks move it while you contribute. Right of the line: "
            "the marginal rate on the taxable half of that year's withdrawal. Flat stretches are "
            "real — Singapore's bands are wide plateaus, not a smooth curve. Set your own bracket "
            "edits and drift assumptions on the left to see this move."))

        # 1. head to head
        st.subheader("1 · With SRS vs. without — the final score")
        with st.container(border=True):
            st.caption(f"Money in hand at age {start_age + contrib_years + draw_years}. Taller wins; "
                      "thin line is the unlucky→lucky range.")
            ws, wo = s["wealth_with_srs"], s["wealth_without_srs"]
            hh = pd.DataFrame([
                {"label": "With SRS", "value": ws["median"], "lo": ws["p10"], "hi": ws["p90"],
                 "valuetext": friendly(ws["median"])},
                {"label": "Without SRS (invest normally)", "value": wo["median"], "lo": wo["p10"],
                 "hi": wo["p90"], "valuetext": friendly(wo["median"])}])
            st.altair_chart(hbar(hh, "Money at the end (middle outcome)", highlight_value="With SRS"),
                            width="stretch")

        # 2. keep adding?
        st.subheader("2 · Should you keep putting money in?")
        with st.container(border=True):
            first = median["yearly_contributions"][0]
            save_now, pay_later = first["relief_rate"], first["breakeven_tc"]
            c1, c2 = st.columns(2)
            c1.metric("The next dollar SAVES you now", f"{save_now*100:.0f}¢")
            c2.metric("…and will COST you later", f"{pay_later*100:.1f}¢")
            st.markdown(esc(f"Save {save_now*100:.0f}¢ now, pay {pay_later*100:.1f}¢ later → the next "
                            f"dollar is **{'worth it ✅' if save_now > pay_later else 'not worth it ❌'}**. "
                            f"Total discount over all years: **{friendly(s['total_relief_received']['median'])}**."))
            pot = s["srs_at_retirement"]["median"]
            stop_line = m.participation_crossover_pot(save_now, r=p["mean_return"],
                                                       brackets=p["base_brackets"])
            if stop_line is None:
                st.caption(esc(
                    f"At your {save_now*100:.0f}¢-now relief rate, the next dollar is worth it "
                    f"no matter how big the pot gets — there's no stop-adding line."))
            else:
                st.progress(min(1.0, pot / stop_line),
                            text=esc(f"{friendly(pot)} of the {friendly(stop_line)} 'stop adding' "
                                     f"line — the pot size at which your {save_now*100:.0f}¢-now "
                                     f"relief rate stops beating the eventual exit tax"))

        # 3. taking it out
        st.subheader("3 · Taking it out: how much tax the plan pays")
        with st.container(border=True):
            chosen_label = STRATEGY_LABELS[p["drawdown_strategy"]]
            if p["drawdown_strategy"] != "rule40":
                st.caption(f"Tax over the {draw_years}-year withdrawal, this profile's chosen strategy "
                          f"— **{chosen_label}** — versus the popular $40k/yr rule of thumb.")
                tax_df = pd.DataFrame([
                    {"label": chosen_label, "value": median["mpc_total_tax"],
                     "valuetext": friendly(median["mpc_total_tax"])},
                    {"label": "$40k/yr rule of thumb", "value": median["rule40_total_tax"],
                     "valuetext": friendly(median["rule40_total_tax"])}])
                st.altair_chart(hbar(tax_df, "Tax paid taking it out (shorter is better)",
                                     highlight_value=chosen_label), width="stretch")
            else:
                st.caption("You've selected the $40k/yr rule itself — see the **Withdrawal strategy "
                          "lab** tab to compare it against smarter alternatives.")

            st.markdown(f"**The plan it recommends — how much to take out each year ({chosen_label})**")
            dd = median["mpc_drawdown"]
            sched = pd.DataFrame([
                {"year": f"Yr {i + 1}", "amount": w, "tax": t, "valuetext": friendly(w)}
                for i, (w, t) in enumerate(zip(dd["withdrawals"], dd["taxes"]))])
            bars = (alt.Chart(sched).mark_bar(color=BLUE, cornerRadiusEnd=3)
                    .encode(x=alt.X("year:N", sort=None, title=None,
                                    axis=alt.Axis(labelColor=INK, labelAngle=0, labelFontSize=12,
                                                  domain=False, ticks=False)),
                            y=alt.Y("amount:Q", title=None,
                                    axis=alt.Axis(labels=False, ticks=False, domain=False, grid=False)),
                            tooltip=[alt.Tooltip("valuetext:N", title="Take out"),
                                     alt.Tooltip("tax:Q", title="Tax", format="$,.0f")]))
            labels = (alt.Chart(sched).mark_text(dy=-7, color=INK, fontSize=11)
                      .encode(x=alt.X("year:N", sort=None), y="amount:Q", text="valuetext:N"))
            st.altair_chart((bars + labels).properties(height=190, width="container")
                            .configure_view(strokeWidth=0), width="stretch")
            if p["drawdown_strategy"] == "mpc":
                explain = ("This is a Model Predictive Control (MPC) plan: it doesn't fix a schedule "
                          "up front. Each year it re-decides how much to withdraw using that year's "
                          "real market return and real tax rates.")
            elif p["drawdown_strategy"] == "static_level":
                explain = ("This is a fixed level plan: the amount was decided once, in the very "
                          "first year, and never revised — even though the real return each year "
                          "turned out differently from the forecast.")
            elif p["drawdown_strategy"] == "rule40":
                explain = "This follows the popular $40,000-a-year rule of thumb every year."
            else:
                explain = f"This withdraws your chosen ${p['drawdown_fixed_amount']:,.0f} every year."
            st.caption(esc(f"{explain} Paying {friendly(median['mpc_total_tax'])} of tax in total. See "
                          f"the **Withdrawal strategy lab** tab to compare every rule side by side on "
                          f"this exact same simulated path."))

        # 4. after the window
        st.subheader("4 · After it's all out: spend it, or leave it?")
        with st.container(border=True):
            aw = median["after_window"]
            spend_pct = st.slider(
                "How much of the 'spend it all' amount do you want to actually spend, each year?",
                0, 100, 50, 5, format="%d%%",
                help="0% = never touch it, so the whole thing (still growing) goes to family. "
                     "100% = draw it down evenly so there's exactly nothing left at the end. "
                     "Anything in between spends less now and leaves the rest to keep compounding "
                     "for family — it's a straight-line trade-off between the two.")
            chosen_annual = aw["spend_to_zero_annual"] * spend_pct / 100.0
            chosen_bequest = sim.bequest_after_spending(
                median["wealth_with_srs"], p["mean_return"], p["dey"], chosen_annual)
            c1, c2 = st.columns(2)
            c1.metric("You spend, each year", f"{friendly(chosen_annual)}/yr")
            c2.metric(f"Left for family at {death_age}", friendly(chosen_bequest))
            st.caption(esc(
                f"The two ends of this slider: spend nothing and leave "
                f"{friendly(aw['bequest_if_untouched'])} for family, or spend "
                f"{friendly(aw['spend_to_zero_annual'])}/yr and leave nothing."))

        # 5. break out early
        st.subheader("5 · Tempted to pull it out early?")
        mid = median["yearly_contributions"][len(median["yearly_contributions"]) // 2]
        hurdle = mid["early_exit_breakeven_return"]
        if hurdle is not None:
            with st.container(border=True):
                st.metric(f"An outside deal must beat this every year (if you break out in year "
                          f"{mid['year']})", f"{hurdle*100:.1f}% / year")
                bench = pd.DataFrame([
                    {"label": "Savings account", "value": 0.0005, "valuetext": "0.05%"},
                    {"label": "Fixed deposit / bonds", "value": 0.03, "valuetext": "~3%"},
                    {"label": "Stock market (long-run avg)", "value": 0.07, "valuetext": "~7%"},
                    {"label": "Break-even hurdle to leave early", "value": hurdle,
                     "valuetext": f"{hurdle*100:.1f}%"}])
                st.altair_chart(hbar(bench, "What you'd need to earn outside vs. what's realistic",
                                     highlight_value="Break-even hurdle to leave early"),
                                width="stretch")
            st.caption("Can't reliably beat the blue bar? Leaving it in SRS wins. The hurdle climbs "
                      "the closer you get to being allowed to withdraw normally.")

# ============================================================ TAB 2: COMPARE EVERYTHING =====
if tab_compare.open:
    with tab_compare:
        if p["base_brackets"] != tuple(m.BRACKETS):
            st.info("These comparisons use the tax brackets you edited in the sidebar, not the "
                   "IRAS default schedule.", icon="✏️")

        with st.spinner("Running the comparisons…"):
            # Put the user's own income/return on the grid (sorted, de-duped) so their point is
            # drawn and marked exactly, even off a preset comparison value.
            income_grid = tuple(sorted(set(
                [20_000, 40_000, 60_000, 80_000, 100_000, 120_000, 140_000, 160_000, 180_000,
                 200_000, 240_000, 280_000, 320_000, 400_000, 500_000]) | {p["chargeable"]}))
            inc_rows = sweep_income(income_grid, p["n_paths"], p["seed"], p["contribution"],
                                    p["mean_return"], p["vol"], p["wage_growth"], p["shock_prob"],
                                    p["dey"], p["base_brackets"], p["return_mode"],
                                    p["historical_block_size"])
            if p["return_mode"] == "parametric":
                return_grid = tuple(sorted(set(sim.DEFAULT_RETURN_GRID) | {round(p["mean_return"], 4)}))
                ret_rows = sweep_return(return_grid, p["chargeable"], p["n_paths"], p["seed"],
                                        p["contribution"], p["vol"], p["wage_growth"], p["shock_prob"],
                                        p["dey"], p["base_brackets"])
            else:
                ret_rows = None
            tax_rows = sweep_tax(p["chargeable"], p["wage_growth"], p["shock_prob"], p["n_paths"],
                                 p["seed"], p["contribution"], p["mean_return"], p["vol"], p["dey"],
                                 p["base_brackets"], p["return_mode"], p["historical_block_size"])

        # ---- across income
        st.subheader("A · Does your income change whether SRS is worth it?")
        df_inc = pd.DataFrame([{"x": r["income"], "median": r["advantage"]["median"],
                                "lo": r["advantage"]["p10"], "hi": r["advantage"]["p90"],
                                "valuetext": friendly(r["advantage"]["median"]),
                                "is_hi": r["income"] == p["chargeable"]} for r in inc_rows])
        st.altair_chart(sweep_line(df_inc, "How much richer SRS makes you — by income",
                                  "Taxable income"), width="stretch")
        st.caption(esc(
            "Each point on the curve is a full Monte-Carlo run at that income; the shaded band is "
            "the unlucky→lucky (10th–90th percentile) range; hover for exact numbers. The marked "
            "dot is **your** income. The SRS pot is identical at every income (same capped payment) "
            "— higher earners win more only because their tax discount going in is bigger."))

        # ---- across market return
        st.subheader("B · Does the market matter?")
        if ret_rows is not None:
            df_ret = pd.DataFrame([{"x": r["mean_return"] * 100, "median": r["advantage"]["median"],
                                    "lo": r["advantage"]["p10"], "hi": r["advantage"]["p90"],
                                    "valuetext": friendly(r["advantage"]["median"]),
                                    "is_hi": abs(r["mean_return"] - p["mean_return"]) < 1e-9}
                                  for r in ret_rows])
            st.altair_chart(sweep_line(df_ret, "How much richer SRS makes you — by average market return",
                                      "Average yearly return (%)", x_fmt=".0f"), width="stretch")
            pct_lo = ret_rows[0]["advantage_pct"]["median"] * 100     # lowest return on the grid
            pct_hi = ret_rows[-1]["advantage_pct"]["median"] * 100    # highest return on the grid
            st.caption(esc(f"The dollar head start grows with the market — but the *percentage* edge "
                           f"actually shrinks, from about {pct_lo:.0f}% at the low end to {pct_hi:.0f}% "
                           f"at the high end, because the tax-free half covers less of the (bigger) "
                           f"growth. The marked dot is your chosen return."))
        else:
            st.info("This comparison sweeps an *assumed* average return, which isn't meaningful "
                   "once you're replaying real history instead of assuming one — switch 'Model "
                   "the market using' back to 'Your own assumptions' to see this axis.",
                   icon=":material/info:")

        # ---- across tax future
        st.subheader("C · What if taxes change over the years?")
        df_tax = pd.DataFrame([{"label": r["regime"], "value": r["advantage"]["median"],
                                "lo": r["advantage"]["p10"], "hi": r["advantage"]["p90"],
                                "valuetext": friendly(r["advantage"]["median"])} for r in tax_rows])
        st.altair_chart(hbar(df_tax, "How much richer SRS makes you — by tax future",
                             highlight_value="Creep + rate-change shocks"), width="stretch")
        st.caption("Three tax futures over your contributing years: bands frozen forever; bands "
                  "frozen while your pay rises (so you drift into higher ones — 'bracket creep'); "
                  "and that plus random government rate changes. Creep actually *raises* the "
                  "advantage, because a bigger discount goes in.")

# ============================================================ TAB 3: STRATEGY LAB ============
if tab_strategy.open:
    with tab_strategy:
        result = one_profile(p["chargeable"], p["n_paths"], p["seed"], p["contribution"],
                             p["mean_return"], p["vol"], p["wage_growth"], p["shock_prob"], p["dey"],
                             p["base_brackets"], p["drawdown_strategy"], p["drawdown_fixed_amount"],
                             p["use_dp"], p["return_mode"], p["historical_block_size"])
        median = result["median_path"]
        contrib_years = len(median["yearly_contributions"])
        draw_years = len(median["mpc_drawdown"]["withdrawals"])
        start_age = sim.RETIREMENT_AGE - contrib_years

        st.caption(
            "Every rule below plays out on the exact same simulated market path — the one used as "
            "this profile's 'middle' story in the first tab — so the only thing that changes is the "
            "withdrawal rule itself.")

        lab = [(p["drawdown_strategy"], STRATEGY_LABELS[p["drawdown_strategy"]],
               median["mpc_drawdown"]["balance_path"], median["mpc_total_tax"])]
        if p["drawdown_strategy"] != "rule40":
            lab.append(("rule40", STRATEGY_LABELS["rule40"],
                       median["rule40_drawdown"]["balance_path"], median["rule40_total_tax"]))
        covered = {row[0] for row in lab}
        for key in ("mpc", "static_level"):
            if key in covered:
                continue
            dd = sim.mpc_drawdown(median["srs_at_retirement"], draw_years, median["draw_returns"],
                                  median["draw_brackets"], 0.0, p["mean_return"], strategy=key)
            total = dd["total_tax"] + _residual_tax(dd["residual"], median["draw_brackets"][-1])
            lab.append((key, STRATEGY_LABELS[key], dd["balance_path"], total))

        st.subheader("How each rule drains the same pot")
        line_rows = [{"age": start_age + contrib_years + i + 1, "strategy": label, "balance": bal}
                    for _, label, path, _ in lab for i, bal in enumerate(path)]
        df_lines = pd.DataFrame(line_rows)
        st.altair_chart(strategy_lines(df_lines, "Balance still inside SRS, by age",
                                       highlight=STRATEGY_LABELS[p["drawdown_strategy"]]),
                        width="stretch")
        st.caption(esc(
            "Your chosen strategy is drawn thicker and fully opaque. A line that reaches zero early "
            "paid everything out (and stopped compounding inside SRS) sooner; a line that stays "
            "high longer keeps more invested but risks a bigger deemed withdrawal if it hasn't "
            "reached zero by the end of the 10-year window. Hover any point for the exact balance."))

        st.subheader("Total tax paid, by rule")
        tax_rows2 = [{"label": label, "value": total, "valuetext": friendly(total)}
                    for _, label, _, total in lab]
        df_tax_cmp = pd.DataFrame(tax_rows2).sort_values("value").reset_index(drop=True)
        st.altair_chart(hbar(df_tax_cmp, "Lower is better — less tax means more ending wealth",
                            highlight_value=STRATEGY_LABELS[p["drawdown_strategy"]]),
                        width="stretch")
        st.caption(esc(
            "Money compounds at the same rate inside and outside SRS either way, so the only lever "
            "left is which year the tax bill lands in (docs/findings.md #9). Only 'Smart plan "
            "(MPC)' reacts to what the market and tax rates actually did each year — every other "
            "rule follows a fixed schedule regardless of what happens."))

st.divider()
st.caption(
    "Not modelled: dying at a random age (age is a fixed input), the life-annuity option, the "
    "foreigner withholding concession, other retirement income, and the $80,000 overall relief "
    "cap. The tax-change model is illustrative, not a forecast. Details in docs/open-tasks.md "
    "and srs_simulation.py. Research on stated assumptions, not financial advice.")
