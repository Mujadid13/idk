import os
import json
import geopandas as gpd
from shapely.geometry import Point
from fastapi import FastAPI, HTTPException

# Initialize FastAPI app
app = FastAPI()

# Paths to your SHP files (Make sure these exist inside Render)
DIVISIONS_SHP_PATH = "data/Divisions_RYK_Area.shp"
NETWORK_SHP_PATH = "data/Irrigation_Network_RYK_Area.shp"


def check_user_inside_divisions(user_lon, user_lat):
    """Check if the user is inside any division polygon."""
    if not os.path.exists(DIVISIONS_SHP_PATH):
        raise HTTPException(status_code=500, detail=f"{DIVISIONS_SHP_PATH} not found")

    gdf_div = gpd.read_file(DIVISIONS_SHP_PATH)

    # Ensure CRS is EPSG:4326 (lat/lon)
    if gdf_div.crs != "EPSG:4326":
        gdf_div = gdf_div.to_crs(epsg=4326)

    user_point = Point(user_lon, user_lat)

    # Check if user is inside any division
    gdf_div["user_inside"] = gdf_div.geometry.contains(user_point)
    user_in_any_polygon = gdf_div["user_inside"].any()

    return user_in_any_polygon


def find_nearest_canals(user_lon, user_lat, k=3):
    """Find the k nearest canals to the user's location."""
    if not os.path.exists(NETWORK_SHP_PATH):
        raise HTTPException(status_code=500, detail=f"{NETWORK_SHP_PATH} not found")

    gdf_net = gpd.read_file(NETWORK_SHP_PATH)

    # Ensure CRS is EPSG:4326
    if gdf_net.crs != "EPSG:4326":
        gdf_net = gdf_net.to_crs(epsg=4326)

    # Remove empty geometries
    gdf_net = gdf_net.dropna(subset=["geometry"]).copy()

    user_point = Point(user_lon, user_lat)

    # Calculate distances and find nearest canals
    gdf_net["dist_to_user"] = gdf_net.geometry.distance(user_point)
    nearest_canals = gdf_net.nsmallest(k, "dist_to_user")["CHANNEL_NA"].tolist()

    return nearest_canals


@app.get("/")
def home():
    return {"message": "FastAPI is running on Render!"}


@app.get("/check-location")
def check_location(lat: float, lon: float):
    """API Endpoint to check user location and return nearest canals."""
    try:
        user_inside = check_user_inside_divisions(lon, lat)

        if user_inside:
            nearest_canals = find_nearest_canals(lon, lat, k=3)
            return {"nearest_canals": nearest_canals}
        else:
            return {"message": "You are not in the division"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
