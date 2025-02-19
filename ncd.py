import sys
import json
import geopandas as gpd
from shapely.geometry import Point

def check_user_inside_divisions(divisions_shp_path, user_lon, user_lat):
    """
    1) Loads Divisions_RYK_Area.shp (polygons),
    2) Checks if the user is inside each polygon,
    3) Returns a GeoDataFrame with a column 'user_inside'
       plus a boolean indicating if the user is in any division.
    """
    gdf_div = gpd.read_file(divisions_shp_path)
    
    # Ensure it's in EPSG:4326 if user coords are lon/lat
    if gdf_div.crs != "EPSG:4326":
        gdf_div = gdf_div.to_crs(epsg=4326)
    
    # Create a Shapely Point from the user's coordinates
    user_point = Point(user_lon, user_lat)
    
    # Check if user_point is inside each polygon
    gdf_div["user_inside"] = gdf_div.geometry.contains(user_point)
    
    # Flag to indicate if user is inside any polygon
    user_in_any_polygon = gdf_div["user_inside"].any()
    
    return gdf_div, user_in_any_polygon


def find_nearest_canals(network_shp_path, user_lon, user_lat, k=3):
    """
    Finds the k nearest canals to the user's location.
    Returns a list of canal names.
    """
    gdf_net = gpd.read_file(network_shp_path)

    # Ensure CRS is EPSG:4326
    if gdf_net.crs != "EPSG:4326":
        gdf_net = gdf_net.to_crs(epsg=4326)

    # Remove empty or invalid geometries
    gdf_net = gdf_net[~gdf_net.geometry.is_empty].copy()
    gdf_net = gdf_net.dropna(subset=["geometry"]).copy()

    user_point = Point(user_lon, user_lat)

    # Calculate distance and get nearest k canals
    gdf_net["dist_to_user"] = gdf_net.geometry.distance(user_point)
    nearest_canals = gdf_net.nsmallest(k, "dist_to_user")["CHANNEL_NA"].tolist()

    return nearest_canals


if __name__ == "__main__":
    try:
        # Read input arguments
        divisions_shp_path = sys.argv[1]
        network_shp_path = sys.argv[2]
        position_raw = sys.argv[3] 

        position = json.loads(position_raw)

        # ✅ Ensure position is a dictionary (not a list)
        if isinstance(position, list):
            position = {"lat": position[0], "lon": position[1]}

        user_lon = position["lon"]
        user_lat = position["lat"]
    

        # Check if user is inside any division
        _, user_in_any_division = check_user_inside_divisions(divisions_shp_path, user_lon, user_lat)

        if user_in_any_division:
            nearest_canals = find_nearest_canals(network_shp_path, user_lon, user_lat, k=3)
            result = nearest_canals
        else:
            result = {"message": "You are not in the division"}

        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

