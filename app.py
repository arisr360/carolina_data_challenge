"""
NC HS Non-Completion Dashboard
Run with: streamlit run app.py
Requires data/merged_districts.geojson (built by prep_data.py)
"""

import json

import geopandas as gpd
import plotly.express as px
import streamlit as st

st.set_page_config(layout="wide", page_title="NC HS Non-Completion Dashboard")

# ---- Config: your top 5 drivers, human labels, and directionality ----
# higher_is_worse = True  -> a HIGH value is the bad direction (e.g. poverty)
# higher_is_worse = False -> a LOW value is the bad direction (e.g. broadband access)
# higher_is_worse = None  -> demographic context only, not a policy lever
VARS = {
    "access_to_broadband_internet": ("Broadband internet access", False),
    "lead_exposure_risk": ("Lead exposure risk", True),
    "low_birth_weight": ("Low birth weight rate", True),
    "poverty": ("Poverty rate", True),
    "some_other_race_alone": ("Some other race alone (%)", None),  # context only
}
POLICY_LEVERS = [k for k, (_, worse) in VARS.items() if worse is not None]


@st.cache_data
def load_data():
    return gpd.read_file("data/merged_districts.geojson")


gdf = load_data()
district_list = sorted(gdf["school_district"].unique())

st.title("NC High School Non-Completion Dashboard")
st.markdown(
    "**HS non-completion isn't evenly distributed across NC districts. "
    "Why? What policies can policymakers focus on, and which districts "
    "need it the most?**"
)
st.caption(
    "Darker districts have a higher percentage of adults (25+) who did not "
    "complete high school. Click a district on the map, or use the dropdown."
)

# ---- Remember the selected district across reruns ----
if "selected_district" not in st.session_state:
    st.session_state.selected_district = district_list[0]

# ---- Layout: map on the left, details on the right ----
map_col, detail_col = st.columns([2, 1])

with map_col:
    geojson = json.loads(gdf.to_json())

    fig = px.choropleth(
        gdf,
        geojson=geojson,
        locations=gdf.index,
        color="less_than_hs",
        color_continuous_scale="Reds",
        hover_name="school_district",
        hover_data={"less_than_hs": ":.1f"},
        labels={"less_than_hs": "Less than HS (%)"},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=600)

    # on_select="rerun" makes clicks trigger a rerun with the clicked point
    # available in the returned event object. Requires Streamlit >= 1.35.
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="district_map",
    )

    # If the user clicked a district, update the selection
    if event and event.get("selection", {}).get("points"):
        clicked_idx = event["selection"]["points"][0]["point_index"]
        st.session_state.selected_district = gdf.iloc[clicked_idx]["school_district"]

with detail_col:
    # dropdown stays as a fallback / accessible alternative to clicking,
    # kept in sync with whatever was last clicked
    selected = st.selectbox(
        "Or pick a district here",
        district_list,
        index=district_list.index(st.session_state.selected_district),
    )
    if selected != st.session_state.selected_district:
        st.session_state.selected_district = selected

    row = gdf[gdf["school_district"] == st.session_state.selected_district].iloc[0]

    st.subheader(st.session_state.selected_district)

    st.metric("Adults without a HS diploma", f"{row['less_than_hs']:.1f}%")
    st.write("**How this district compares to the state average:**")
    for var, (label, _) in VARS.items():
        z_val = row[f"{var}_z"]
        st.write(f"- {label}: `{z_val:+.2f}` std devs from state average")

    st.divider()

    def badness(var):
        # returns a positive number the WORSE this district is on this variable
        z_val = row[f"{var}_z"]
        _, higher_is_worse = VARS[var]
        return z_val if higher_is_worse else -z_val

    ranked = sorted(POLICY_LEVERS, key=badness, reverse=True)
    worst, second = ranked[0], ranked[1]
    worst_score, second_score = badness(worst), badness(second)

    st.write("**Recommendation**")
    if worst_score > 0.5:
        st.warning(
            f"Policymakers should focus on policies regarding "
            f"**{VARS[worst][0]}** ({worst_score:+.1f} std devs worse "
            f"than the state average)."
        )
        if second_score > 0.5:
            st.info(
                f"Secondary focus: **{VARS[second][0]}** "
                f"({second_score:+.1f} std devs worse than the state average)."
            )
    else:
        st.success(
            "This district is at or better than the state average on all "
            "tracked drivers."
        )
    st.caption(
        "Recommendations are based on the district's 4 policy-actionable "
        "drivers (broadband access, lead exposure, low birth weight, "
        "poverty). Race/ethnicity is shown for context above but is not "
        "used to generate recommendations, since it is not itself a "
        "policy lever."
    )

# ================== Visualizations (scroll down) ==================
st.divider()
st.header("Analysis & Visualizations")

# Each block below is one visualization: a title, a short description,
# and a spot for an image. Fill in the title/description text and swap
# in your actual image path for each one.

st.subheader("Highest & Lowest HS Non-Completion Districts")
st.write("The 10 NC school districts with the highest and 10 with the lowest rates of adults (25+) without a high school diploma. The gap between the top and bottom groups shows how unevenly HS non-completion is distributed across the state, this is the starting evidence that led us to ask why.")
st.image("pics/highest_and_lowest_hs_noncompletion_by_district.png", width=800)

st.divider()

st.subheader("Deviation from State Average — Top 5 Drivers by District")
st.write("For the 10 NC school districts with the highest and 10 with the lowest rates of adults (25+) without a high school diploma, this heatmap shows how far each one sits from the state average (in standard deviations) on our five key drivers: broadband access, lead exposure risk, some other race alone, low birth weight, and poverty. Red cells mark where a district is worse than average, this is what powers the per-district recommendations in the dashboard above.")
st.image("pics/deviation_from_state_avg.png", width=700)

st.divider()

st.subheader("NC HS Non-Completion by District")
st.write("A geographic view of HS non-completion rates across all NC school districts, using official NCES district boundaries. Darker red indicates a higher percentage of adults without a diploma, making regional patterns and clusters of disadvantage visible at a glance.")
st.image("pics/hs_noncompletion_rate_heatmap.png", width=700)

st.divider()

st.subheader("Full Correlation Screen: All ODIS Variables vs. HS Non-Completion")
st.write("Correlation of every numeric ODIS variable against HS non-completion rate, ranked to show the full landscape before narrowing to our final 5 drivers. This is also where we identified and excluded the circular variables, Composite Score, Economic, Health, and their percentile-rank versions all correlate strongly here, but only because HS non-completion is mathematically one of their own inputs, not because they're independent predictors.")
st.image("pics/correlations_barh.png", )

st.divider()

st.subheader("Gini Index vs. HS Non-Completion")
st.write("Relationship between income inequality (Gini Index) and HS non-completion across NC districts, with a linear trend line (red) overlaid on the underlying data pattern. The weak, roughly flat trend shows income inequality alone is a much weaker predictor of non-completion than variables like poverty or broadband access, a useful negative result that helped narrow down our final driver list.")
st.image("pics/linear_regression.png", width=700)

st.divider()

st.header("Random Forest Decision Tree Findings")
st.write("To validate our regression-based findings, we also trained a random forest model on the same predictors. The model confirms broadband access as the single strongest predictor of HS non-completion, consistent with our correlation and regression analyses, while also surfacing housing and economic-domain variables as secondary contributors")
st.subheader("Panel 1 — Variable Importance (Top 10)")
st.write("Mean decrease in Gini impurity for each predictor, a measure of how much each variable contributes to the model's splitting decisions. Broadband access dominates by a wide margin, roughly 3x the importance of the next-closest variable, reinforcing it as our primary driver across every method we tried.")
st.image("pics/top_10_var.png", width=700)
st.subheader("Panel 2 — Tree Size Distribution")
st.write("Distribution of the number of nodes across all 500 trees in the random forest, showing the model consistently built moderately-sized trees (mostly 30–45 nodes), a sanity check confirming the model wasn't over- or under-fitting to individual splits.")
st.image("pics/num_of_nodes.png", width=700)
st.subheader("Out-of-Bag Error by Number of Trees")
st.write("Model error rate as more trees are added to the forest. Error drops sharply in the first ~100 trees and then stabilizes around 0.09–0.10, showing the model converged well before reaching the full 500 trees, confirming the forest size was more than sufficient.")
st.image("pics/out_of_bag_error.png", width=700)

