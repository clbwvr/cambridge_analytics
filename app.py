import streamlit as st
import folium
import json
import csv
import pandas as pd
from streamlit_folium import st_folium
import branca.colormap as cm

# File paths
GEOJSON_FILE = "data/BOUNDARY_CDDNeighborhoods.geojson"
LOCALS_SAY_CSV = "data/locals_say.csv"
PRICES_CSV = "data/prices.csv"
PARKS_GEOJSON = "data/RECREATION_Playgrounds.geojson"  # GeoJSON file with parks

# Available metrics
METRIC_COLUMNS = [
    "It's dog friendly", "It's walkable to restaurants", "There are sidewalks", "Streets are well-lit",
    "It's walkable to grocery stores", "People would walk alone at night", "Kids play outside",
    "There's holiday spirit", "Neighbors are friendly", "Parking is easy", "They plan to stay for at least 5 years",
    "It's quiet", "There are community events", "There's wildlife", "Car is needed", "Yards are well-kept",
    "votes", "Median 2024 Home Price"
]

def load_data():
    """Load and merge neighborhood, opinion, and price data."""
    with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    locals_say_dict = {}
    with open(LOCALS_SAY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            locals_say_dict[row["Neighborhood"].strip()] = row

    prices_dict = {}
    with open(PRICES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prices_dict[row["Neighborhood"].strip().strip('"')] = row

    for feature in geojson_data["features"]:
        name = feature["properties"]["NAME"].strip()
        if name in locals_say_dict:
            for col, val in locals_say_dict[name].items():
                if col != "Neighborhood":
                    feature["properties"][col] = val
        if name in prices_dict:
            try:
                feature["properties"]["Median 2024 Home Price"] = float(prices_dict[name]["Median 2024 Home Price"])
            except:
                feature["properties"]["Median 2024 Home Price"] = 0

    return geojson_data

def load_parks():
    """Load Cambridge park locations from GeoJSON."""
    with open(PARKS_GEOJSON, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    st.title("Cambridge Neighborhoods - Home Prices & Parks")

    # Load data
    data = load_data()
    parks = load_parks()

    # User selections
    selected_metric = st.selectbox("Pick a metric to color the map", METRIC_COLUMNS, index=0)
    all_names = sorted([f["properties"]["NAME"] for f in data["features"]])
    excluded = st.multiselect("Exclude from color scale?", all_names, default=[])
    show_parks = st.checkbox("Show Parks on Map", value=True)  # Checkbox to toggle parks

    # Compute min/max for color scale
    included_vals = []
    for feat in data["features"]:
        name = feat["properties"]["NAME"]
        if name in excluded:
            continue
        try:
            v = float(feat["properties"].get(selected_metric, 0))
        except:
            v = 0
        included_vals.append(v)

    minval, maxval = (min(included_vals), max(included_vals)) if included_vals else (0, 1)

    # Create Folium map
    m = folium.Map(location=[42.3736, -71.1106], zoom_start=13)
    colormap = cm.LinearColormap(colors=["#f7fbff", "#08306b"], vmin=minval, vmax=maxval)
    colormap.caption = selected_metric

    def style_function(feature):
        name = feature["properties"]["NAME"]
        val = float(feature["properties"].get(selected_metric, 0))
        return {"fillColor": colormap(val) if name not in excluded else "lightgray",
                "fillOpacity": 0.8, "color": "black", "weight": 1}

    folium.GeoJson(
        data,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=["NAME", selected_metric, "votes"]),
    ).add_to(m)

    # Conditionally add parks
    if show_parks:
        for park in parks["features"]:
            park_name = park["properties"]["LOCATION"]
            lat, lon = park["geometry"]["coordinates"][1], park["geometry"]["coordinates"][0]

            folium.Marker(
                location=[lat, lon],
                popup=f"<b>{park_name}</b>",
                icon=folium.Icon(color="green", icon="tree")
            ).add_to(m)

    colormap.add_to(m)
    st_folium(m, width=800, height=600)

if __name__ == "__main__":
    main()
