import streamlit as st
import folium
import json
import csv
from streamlit_folium import st_folium
import branca.colormap as cm

GEOJSON_FILE = "data/BOUNDARY_CDDNeighborhoods.geojson"
LOCALS_SAY_CSV = "data/locals_say.csv"  # Original CSV with dog-friendly metrics
PRICES_CSV = "data/prices.csv"  # New CSV with 'Median 2024 Home Price'

# Available metric columns (locals_say.csv + Median 2024 Home Price from prices.csv)
METRIC_COLUMNS = [
    "It's dog friendly", "It's walkable to restaurants", "There are sidewalks", "Streets are well-lit",
    "It's walkable to grocery stores", "People would walk alone at night", "Kids play outside",
    "There's holiday spirit", "Neighbors are friendly", "Parking is easy", "They plan to stay for at least 5 years",
    "It's quiet", "There are community events", "There's wildlife", "Car is needed", "Yards are well-kept",
    "Median 2024 Home Price",  # From prices.csv
    "votes",  # From locals_say.csv
]


def load_data():
    """
    1) Read the GeoJSON.
    2) Load both CSVs.
    3) Merge columns from both CSVs into each Feature in the GeoJSON,
       keyed by 'NAME' in GeoJSON vs. 'Neighborhood' in CSVs.
    """
    # --- 1) Load GeoJSON ---
    with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    # --- 2) Load 'locals_say.csv' into a dict keyed by neighborhood name ---
    locals_say_dict = {}
    with open(LOCALS_SAY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nhood = row["Neighborhood"].strip()
            locals_say_dict[nhood] = row

    # --- 3) Load 'prices.csv' into a dict keyed by neighborhood name ---
    prices_dict = {}
    with open(PRICES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nhood = row["Neighborhood"].strip().strip('"')  # Remove quotes if any
            prices_dict[nhood] = row

    # --- 4) Merge data into GeoJSON features ---
    for feature in geojson_data["features"]:
        name = feature["properties"]["NAME"].strip()

        # Merge 'locals_say.csv' columns
        if name in locals_say_dict:
            for col, val in locals_say_dict[name].items():
                if col != "Neighborhood":
                    feature["properties"][col] = val

        # Merge 'prices.csv' columns
        if name in prices_dict:
            price_str = prices_dict[name].get("Median 2024 Home Price", "0")
            try:
                price_val = float(price_str)
            except:
                price_val = 0
            feature["properties"]["Median 2024 Home Price"] = price_val

    return geojson_data


def main():
    st.title("Cambridge Neighborhoods - Home Prices & Local Opinions")

    # 1) Load & merge data
    data = load_data()

    # 2) User selects a metric to visualize
    selected_metric = st.selectbox("Pick a metric to color the map", METRIC_COLUMNS, index=0)

    # 3) User selects neighborhoods to exclude from the color scale
    all_names = sorted([f["properties"]["NAME"] for f in data["features"]])
    excluded = st.multiselect("Exclude from color scale?", all_names, default=[])

    # 4) Compute min & max ignoring excluded neighborhoods
    included_vals = []
    for feat in data["features"]:
        name = feat["properties"]["NAME"]
        if name in excluded:
            continue  # Skip excluded neighborhoods from color scale
        s = feat["properties"].get(selected_metric, "0")
        try:
            v = float(s)
        except:
            v = 0
        included_vals.append(v)

    if len(included_vals) == 0:
        # If all are excluded, fall back to default range
        minval, maxval = 0, 1
    else:
        minval, maxval = min(included_vals), max(included_vals)

    # 5) Create Folium map
    m = folium.Map(location=[42.3736, -71.1106], zoom_start=13)

    # Improved **Color Gradient** for better distinction (from blue to dark blue)
    colormap = cm.LinearColormap(colors=["#f7fbff", "#08306b"], vmin=minval, vmax=maxval)
    colormap.caption = selected_metric

    def style_function(feature):
        name = feature["properties"]["NAME"]
        val_str = feature["properties"].get(selected_metric, "0")
        try:
            val = float(val_str)
        except:
            val = 0

        if name in excluded:
            # Color excluded neighborhoods light gray
            return {
                "fillColor": "lightgray",
                "fillOpacity": 0.5,
                "color": "black",
                "weight": 1,
            }
        else:
            return {
                "fillColor": colormap(val),
                "fillOpacity": 0.8,
                "color": "black",
                "weight": 1,
            }

    # Tooltip includes "Votes" count and selected metric
    folium.GeoJson(
        data,
        style_function=style_function,
        name="Neighborhoods",
        tooltip=folium.GeoJsonTooltip(fields=["NAME", selected_metric, "votes"]),
    ).add_to(m)

    colormap.add_to(m)

    # 6) Display in Streamlit
    st_folium(m, width=800, height=600)


if __name__ == "__main__":
    main()
