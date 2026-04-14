import geopandas as gpd
import os

path = "/home/edgardo/Documentos/visor2/radios2022_v1.0.shp"

if not os.path.exists(path):
    print("❌ No se encontró el shapefile:", path)
    exit()

gdf = gpd.read_file(path)

gdf = gdf.to_crs(epsg=4326)
gdf.to_file("radios2022.geojson", driver="GeoJSON")

print("✅ GeoJSON generado correctamente")