import json
import psycopg2

# cargar archivo geojson
with open("/home/edgardo/Documentos/visor2/static/gis/radios-censales.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

conn = psycopg2.connect(
    dbname="visualizador",
    user="visualizador",
    password="Estadisticas24",
    host="visoreducativochaco.com.ar",
    port="5432"
)

cur = conn.cursor()

for feat in data["features"]:
    props = feat["properties"]
    geom = json.dumps(feat["geometry"])

    cur.execute("""
        INSERT INTO public.radios_censales (
            nomprov, prov, nomdepto, depto,
            frac, radio, tipo, link, obs2020, geom
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,
            ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)
        )
    """, (
        props.get("NOMPROV"),
        props.get("PROV"),
        props.get("NOMDEPTO"),
        props.get("DEPTO"),
        props.get("FRAC"),
        props.get("RADIO"),
        props.get("TIPO"),
        props.get("LINK"),
        props.get("OBS2020"),
        geom
    ))

conn.commit()
cur.close()
conn.close()

print("IMPORTACIÓN COMPLETA ✔️")