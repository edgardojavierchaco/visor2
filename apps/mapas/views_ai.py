import json
import spacy
import re
import numpy as np
from django.shortcuts import render
from django.db import connection
from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import CountVectorizer
from .models import Interaccion
import nltk
nltk.download('punkt')
from nltk.stem import SnowballStemmer
import unicodedata


nlp = spacy.load("es_core_news_sm")
stemmer = SnowballStemmer("spanish")

vectorizer = CountVectorizer()
model = SGDClassifier(loss="log_loss")

X_train = []
y_train = []

palabras_clave = {
    "departamento": ["departamento", "departamentos", "en el departamento", "del departamento", 
        "depto", "depto.", "en depto", "departamento de", "zona"],
    "localidad": ["localidad", "localidades", "localidad de", "localidad en", "localidad en la"],
    "calle": ["calle", "avenida", "av", "en la calle", "sobre la calle", "ubicado en la calle", 
        "domicilio", "dirección", "direccion", "direccion escolar", "nombre de la calle"],
    "region": ["región", "regional", "subregional", "subreg", "sub"],
    "sector": ["sector", "sectores", "en el sector", "del sector", "sector educativo", 
        "sector de gestión", "tipo de gestión"],
    "ambito": ["ámbito", "ambito", "ámbitos", "ambitos", "en el ámbito", "en el ambito", 
        "ámbito educativo", "tipo de ámbito", "ambito de gestión"],
    "etiqueta": ["etiqueta", "denominación"],
    "oferta": ["primaria", "primarias", "secundaria", "secundarias", "inicial", "snu", "adulto","adultos", "especial", "servicio complementario", "servicios complementarios","Formación Profesional", "FP", "terciario", "superior", "profesorado", "media", "polimodal",
               "Fromacion Profesional", "formacion profesional", "educación especial", "educacion especial", "educacion de adultos", "educacion para adultos", "educacion de jovenes y adultos", "educacion para jovenes y adultos","jardín", "jardin", "jardin maternal", "jardin de infantes", "jardin maternal", "educación integral", "educacion integral", "cursos", "talleres", "integración", "integracion"],
    "cui_loc": ["cui_loc", "cuiloc", "cuiloc", "cui"],
    "cueanexo": ["cueanexo", "cue"],
    "nom_est": ["nombre", "nombre de la escuela", "nombre de la institución", 
        "nombre de la institucion", "nombre de la institución educativa", 
        "nombre de la institucion educativa", "escuela", "nombre oficial", 
        "nombre completo", "establecimiento", "nombre del establecimiento"],
}

lista_localidades = [
    "Avia Terai", "Barranqueras", "Basail", "Campo Largo", "Capitan Solari", "Charadai", "Charata", "Chorotis",
    "Ciervo Petiso", "Colonia Aborigen", "Napalpi", "Colonia Baranda", "Colonia Benitez", "Colonia Elisa",
    "Colonia Popular", "Colonias Unidas", "Concepcion del Bermejo", "Coronel Du Graty", "Corzuela", "Cote Lai",
    "El Espinillo", "El Sauzalito", "Enrique Urien", "Fontana", "Fuerte Esperanza", "Gancedo", "General Capdevila",
    "General San Martin", "General Jose de San Martin", "San Martin", "General Pinedo", "General Vedia",
    "Hermoso Campo", "Isla del Cerrito", "Juan Jose Castelli", "La Clotilde", "La Eduvigis", "La Escondida",
    "La Leonesa", "La Tigra", "La Verde", "Laguna Blanca", "Laguna Limpia", "Lapachito", "Las Breñas",
    "Las Garcitas", "Las Palmas", "Los Frentones", "Machagai", "Makallé", "Margarita Belén", "Miraflores",
    "Napenay", "Nueva Pompeya", "Pampa Almirón", "Pampa del Indio", "Pampa del Infierno", "Presidencia de la Plaza",
    "Presidencia Roca", "Presidencia Roque Sáenz Peña", "Sáenz Peña", "Puerto Bermejo", "Puerto Bermejo Nuevo",
    "Puerto Bermejo Viejo", "Puerto Eva Perón", "Puerto Tirol", "Puerto Vilelas", "Quitilipi", "Resistencia",
    "Río Muerto", "Samuhú", "San Bernardo", "Santa Sylvina", "Taco Pozo", "Tres Isletas", "Villa Ángela",
    "Villa Berthet", "Villa Rio Bermejito",
]

intenciones_comunes = {
    "buscar_escuelas": ["mostrar", "mostrame", "ver", "buscar", "buscame", "escuela", "escuelas", "quiero", "necesito", "consultar"],
    "ver_estadisticas": ["estadísticas", "gráficos", "informes", "ver"],
    "mostrar_mapa": ["mapa", "ubicación", "ver"],
    "consultar_region": ["región", "regional", "zona"],
}

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
    texto = texto.replace("n°", "nro").replace("nº", "nro").replace("numero", "nro").replace("°", "")
    texto = re.sub(r"[\.\,]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def normalizar_region(region_tokens):
    if not region_tokens:
        return None
    region_text = " ".join(region_tokens).upper()
    region_text = region_text.replace("REGION", "R.E.").replace("REGIONAL", "R.E.")
    region_text = region_text.replace("SUBREGIONAL", "SUB. R.E.").replace("SUB REG", "SUB. R.E.")
    region_text = region_text.replace("SUB.", "SUB. R.E.")

    parts = region_text.split()
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isalpha():
        return f"R.E. {parts[1]}-{parts[2]}"
    elif len(parts) == 2 and parts[1].isdigit():
        return f"R.E. {parts[1]}"
    return region_text


def extraer_criterios(consulta):
    criterios = {}
    palabras_usadas = set()
    doc = nlp(consulta.lower())

    EXCLUIR_ENTIDADES = ["escuela", "ees", "epa", "eet", "esja", "epja", "epg", "epgs", "epgc", "uegp", "n°", "nro", "número"]
    palabras_clave_institucionales = set(EXCLUIR_ENTIDADES)

    for ent in doc.ents:
        texto = ent.text.strip().lower()
        if ent.label_ in ["GPE", "LOC"]:
            criterios.setdefault("localidad", []).append(ent.text)
        elif ent.label_ == "ORG":
            if not any(p in texto for p in EXCLUIR_ENTIDADES):
                criterios.setdefault("etiqueta", []).append(ent.text)

    for palabra in ["privado", "pública", "publico", "privada", "publica", "social", "cooperativo", "social/cooperativo"]:
        if palabra in consulta and palabra not in palabras_usadas:
            criterios.setdefault("sector", []).append("privado" if "privad" in palabra else "público")
            palabras_usadas.add(palabra)

    for palabra in ["rural", "urbano"]:
        if palabra in consulta and palabra not in palabras_usadas:
            criterios.setdefault("ambito", []).append(palabra)
            palabras_usadas.add(palabra)

    region_match = re.search(r'(sub(?:\.?\s*r(?:\.?\s*e)?)?|subre)?\.?\s*reg(?:[ií]on|\.?)?(?:\s+educativa)?\.?\s*(\d{1,2})(-[a-zA-Z])?', consulta)
    if region_match:
        es_sub, numero, letra = region_match.group(1), region_match.group(2), region_match.group(3)
        letra = letra.upper() if letra else ""
        region_valor = f"SUB. R.E. {numero}{letra}" if es_sub else f"{numero}{letra}"
        criterios["region_loc"] = [region_valor]

    for localidad in lista_localidades:
        if re.search(rf'\b{re.escape(localidad.lower())}\b', consulta.lower()) and localidad.lower() not in palabras_clave_institucionales:
            criterios.setdefault("localidad", []).append(localidad)

    inverso_claves = {
        stemmer.stem(pal.lower()): clave
        for clave, palabras in palabras_clave.items()
        for pal in palabras
    }

    palabras = re.findall(r'\w+', consulta.lower())
    i = 0
    while i < len(palabras):
        palabra = palabras[i]
        palabra_stem = stemmer.stem(palabra)
        if palabra_stem in inverso_claves:
            categoria = inverso_claves[palabra_stem]
            valor = None
            if i + 1 < len(palabras):
                siguiente = palabras[i + 1]
                if stemmer.stem(siguiente) not in inverso_claves:
                    valor = siguiente
                    i += 1
            if valor:
                criterios.setdefault(categoria, []).append(valor)
        i += 1

    consulta_normalizada = normalizar_texto(consulta)
    OFERTA_KEYWORDS = {
        "Común - Jardín": ["inicial", "jardín", "jardin", "jardin maternal", "jardin de infantes", "jardin maternal"],
        "Común - primaria": ["primaria", "escuela primaria", "escuela de educación primaria", "educación primaria", "primarias"],
        "Común - secundaria": ["secundaria", "media", "polimodal", "secundarias", "escuela secundaria", "escuela de educación secundaria", "educación secundaria"],
        "Común - SNU": ["terciario", "superior", "profesorado","educación superior", "educacion superior", "educacion terciaria", "terciaria"],
        "especial": ["especial", "educación especial", "educacion especial", "educación integral", "educacion integral","cursos","talleres","integración","integracion"],
        "Adultos - Primaria": ["adultos primaria", "adulto primaria", "educación de adultos primaria", "educacion de adultos primaria", "educacion para adultos primaria", "educacion de jovenes y adultos primaria", "educacion para jovenes y adultos primaria"],
        "Adultos - Secundaria": ["adultos secundarias", "adulto secundaria", "educación de adultos secundaria", "educacion de adultos secundaria", "educacion para adultos secundaria", "educacion de jovenes y adultos secundaria", "educación para jovenes y adultos secundaria"],
        "Adultos - Formación Profesional": ["adultos formacion profesional", "adulto formacion profesional", "educación de adultos formacion profesional", "educacion de adultos formacion profesional", "educacion para adultos formacion profesional", "educacion de jovenes y adultos formacion profesional", "educación para jovenes y adultos formacion profesional", "formación profesional", "formacion profesional"],
        "Común - Servicios": ["Biblioteca", "biblioteca", "bibliotecas","servicios", "servicio" "servicio complementario", "servicios complementarios"],
        "Especial - Integración": ["integracion", "especial integración","especial integracion"],
        "Especial - Cursos":["cursos especial", "talleres especial", "especial cursos", "especial talleres"],
        "Especial - Domiciliaria": ["especial domiciliaria", "domiciliaria especial", "domiciliaria", "hospitalaria", "hospitalaria especial"],
        "Espacial - Jardín":["jardin especial", "jardin maternal especial", "jardin de infantes especial", "jardin maternal especial"],
        "Espacial - Primaria":["primaria especial", "escuela primaria especial", "escuela de educación primaria especial", "educación primaria especial"],
        "Especial - Taller":["talleres especial", "taller especial", "talleres de educación especial", "taller de educación especial"],
        "Especial - Educacion":["educacion integral", "especial educacion integral"],
    }   

    KEYWORD_TO_SQL = {
        palabra: nivel for nivel, palabras in OFERTA_KEYWORDS.items() for palabra in palabras
    }

    for palabra in consulta_normalizada.split():
        if palabra in KEYWORD_TO_SQL:
            criterios.setdefault("oferta", []).append(KEYWORD_TO_SQL[palabra])          
       
    return criterios


def operaciones_comunes(request, template_name='mapa/ofertasmark.html'):   
    consulta_texto = request.GET.get("query", "")
    print("Consulta ingresada:", consulta_texto)
    
    criterios = extraer_criterios(consulta_texto)
    print(criterios)
    cursor = connection.cursor()
    query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, cui_loc, cuof_loc, acronimo, etiqueta FROM v_capa_unica_ofertas_cui_cuof WHERE 1=1 "
    parameters = []
    
    # Lista de campos válidos en la tabla para prevenir errores
    CAMPOS_VALIDOS = {
        "cueanexo", "lat", "long", "nom_est", "oferta", "ambito", "sector",
        "region_loc", "calle", "numero", "localidad", "cui_loc", "cuof_loc",
        "acronimo", "etiqueta"
    }
    
    # Agregar condiciones según los criterios
    for campo, valor in criterios.items():
        if campo not in CAMPOS_VALIDOS or not valor or campo == "region_loc":
            continue  # ignorar campos inválidos o region_loc (se trata aparte)

        if campo == "cueanexo":  # Caso especial para cueanexo (convertir a texto)
            if isinstance(valor, list):
                query += f" AND ({' OR '.join([f'CAST(cueanexo AS TEXT) ILIKE %s' for _ in valor])})"
                parameters.extend([f"%{v}%" for v in valor])
            else:
                query += " AND CAST(cueanexo AS TEXT) ILIKE %s"
                parameters.append(f"%{valor}%")
        else:  # Para los demás campos
            if isinstance(valor, list):  # Si el valor es una lista
                query += f" AND ({' OR '.join([f'{campo} ILIKE %s' for _ in valor])})"
                parameters.extend([f"%{v}%" for v in valor])            
            else:  # Si es un solo valor
                query += f" AND {campo} ILIKE %s"
                parameters.append(f"%{valor}%")
    
    # Agregar condición para region_loc si existe
    if "region_loc" in criterios and criterios["region_loc"]:
        region_values = criterios["region_loc"]
        print("viendo valores:", region_values)
        # Separar las regiones si contienen "y"
        region_values_separadas = []
        for region in region_values:
            # Dividir por " y " y agregar cada parte separada a la lista
            region_values_separadas.extend([r.strip() for r in region.split(" y ")])
            
        # Verificar cómo se ven los valores después de la división
        print("Regiones separadas:", region_values_separadas)
        
        # Ahora, agregar cada región como una condición separada en la consulta
        query += f" AND ({' OR '.join([f'region_loc ILIKE %s' for _ in region_values_separadas])})"
        parameters.extend([f"%{v}%" for v in region_values_separadas])
    
    print("Consulta SQL generada:", query)
    print("Parámetros SQL:", parameters)
    
    # Ejecutar la consulta y obtener los resultados
    cursor.execute(query, parameters)
    rows = cursor.fetchall()
    
    # Filtrar resultados por latitudes y longitudes válidas
    filtered_rows = [
        (cueanexo, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, cui_loc, cuof_loc, acronimo, etiqueta) 
        for cueanexo, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, cui_loc, cuof_loc, acronimo, etiqueta in rows 
        if lat != 0 and lng != '' and lng != 0 and lat != ''
    ]
    
    column_names = [desc[0] for desc in cursor.description]  # Obtener nombres de columnas
    cursor.close()
    
    context = {
        'title': 'Mapa',
        'data_json': json.dumps(filtered_rows),
        'column_names_json': json.dumps(column_names)
    }
    print(context)
    return context
    

def entrenar_modelo():
    """
    Entrena el modelo con los datos disponibles en la base de datos de interacciones.
    """
    global X_train, y_train, model, vectorizer
    
    interacciones = Interaccion.objects.all()
    
    if interacciones.exists():
        X_train = [interaccion.query for interaccion in interacciones]
        y_train = [1 if interaccion.criterios_extraidos else 0 for interaccion in interacciones]

        if X_train:
            # Asegúrate de que el vectorizador esté ajustado antes de transformarlo
            X_vect = vectorizer.fit_transform(X_train)  # Ajusta el vectorizador con todos los datos
            model.partial_fit(X_vect, y_train, classes=np.array([0, 1]))


def guardar_interaccion_y_entrenar(user, query, criterios, data):
    """
    Guarda la consulta del usuario en la base de datos y reentrena el modelo en tiempo real.
    """
    global X_train, y_train, model, vectorizer
    
    interaccion = Interaccion(
        user=user if user.is_authenticated else None,
        query=query,
        resultado=json.dumps(data),
        criterios_extraidos=criterios
    )
    interaccion.save()

    # Agregar nueva interacción a los datos de entrenamiento
    X_train.append(query)
    y_train.append(1 if criterios else 0)
    
    # Si el vectorizador no ha sido ajustado, ajustarlo ahora
    if not hasattr(vectorizer, 'vocabulary_'):  # Comprobamos si ya está ajustado
        vectorizer.fit(X_train)  # Ajustamos el vectorizador con todas las interacciones
    
    # Vectorizar solo la nueva consulta (usando transform, no fit_transform)
    X_new_vect = vectorizer.transform([query])

    # Actualizar el modelo con la nueva consulta
    model.partial_fit(X_new_vect, [y_train[-1]], classes=np.array([0, 1]))


    
def filtrado(request):    
    # Renderizar el formulario de búsqueda
    return render(request, 'publico/busqueda.html')


def filter_data(request):
    context = operaciones_comunes(request, template_name='mapa/ofertasmark.html')
    
    query = request.GET.get('query', '')
    
    # Extraer criterios de la consulta utilizando spaCy (como ya tienes implementado)
    criterios = extraer_criterios(query)
    
        
    # Guardar la interacción y entrenar en tiempo real
    guardar_interaccion_y_entrenar(request.user, query, criterios, context)
    
        
    return render(request, 'mapa/ofertasmark.html', context)
