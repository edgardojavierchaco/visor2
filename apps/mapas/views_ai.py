import json
import spacy
import re
import numpy as np
from django.shortcuts import render
from django.db import connection
from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import CountVectorizer
from .models import Interaccion


# Carga el modelo de spaCy una vez
nlp = spacy.load("es_core_news_sm")

# Inicializar vectorizador y clasificador de aprendizaje incremental
vectorizer = CountVectorizer()
model = SGDClassifier(loss="log_loss")  # Clasificación binaria con regresión logística

# Datos de entrenamiento iniciales
X_train = []
y_train = []


def normalizar_region(region_tokens):
    """
    Convierte una entrada de región en el formato estándar R.E. X-Y
    """
    if not region_tokens:
        return None
    
    region_text = " ".join(region_tokens).upper()
    region_text = region_text.replace("REGION", "R.E.")
    region_text = region_text.replace("REGIONAL", "R.E.")
    region_text = region_text.replace("SUBREGIONAL", "SUB.R.E.")
    region_text = region_text.replace("SUB REG", "SUB. R.E.")
    region_text = region_text.replace("SUB.", "SUB. R.E.")
    
    parts = region_text.split()
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isalpha():
        return f"R.E. {parts[1]}-{parts[2]}"
    elif len(parts) == 2 and parts[1].isdigit():
        return f"R.E. {parts[1]}"
    
    return region_text

def extraer_criterios(consulta):
    if not consulta:
        return {}  # Retorna un diccionario vacío si no hay consulta
    
    doc = nlp(consulta.lower())
    print("Entidades detectadas:", [(ent.text, ent.label_) for ent in doc.ents]) 
    print("Tokens detectados:", [token.text for token in doc])
    
    
    criterios = {
        "cueanexo": None, "ambito": None, "sector": None, "region_loc": None,
        "departamento": None, "localidad": None, "oferta": None, "calle": None,
        "cui": None, "etiqueta": None, "acronimo": None
    }
    
    palabras_clave = {
        "oferta": ["oferta", "ofertas"],
        "localidad": ["localidad", "localidades", "localidad de"],
        "sector": ["sector", "sectores"],
        "ambito": ["ambito", "ámbito", "ambitos", "ámbitos", "en el ambito"],
        "calle": ["calle","en la calle", "sobre la calle"],
        "etiqueta": ["nombre", "escuela"],
        "region_loc": ["región", "region", "en la regional", "en region", "en la region","regional", "Subregional", "subregional", "Sub.", "sub.", "sub", "Sub", "Sub. reg", "sub. reg", "Sub reg"],
        "departamento": ["departamento", "departamentos"],
        "cueanexo":["cueanexo", "cueanexos", "cue"],
        "acronimo":["buscar", "buscame", "encontrame", "encontrar","mostrar", "mostrame", "mostrame en el mapa"]
    }
    

    palabras = [token.text.lower() for token in doc]
    print("Palabras clave encontradas:", palabras)
    
    i = 0
    while i < len(palabras):
        palabra = palabras[i]
        
        if palabra in palabras_clave["region_loc"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "region_loc"):
                valor.append(palabras[i])
                i += 1
                
            # normalización de la región    
            region_normalizada = normalizar_region(valor)
            print("Valor antes de normalizar:", valor)  # Para verificar qué estás obteniendo en 'valor'
            print("Región normalizada:", region_normalizada) 
            
            if region_normalizada:  # Aseguramos que no es None
                # Verificamos si hay un "y" y lo usamos para dividir correctamente
                region_normalizada = region_normalizada.lower()
                regiones = [reg.strip() for reg in region_normalizada.split(" y ")]
                
                # Si hay más de una región, se agregan todas las regiones
                if len(regiones) > 1:
                    criterios["region_loc"] = regiones
                else:
                    criterios["region_loc"] = [region_normalizada.strip()]  # Si no, solo una región
                
                print(f"Regional encontrada: {criterios['region_loc']}")
        
                print(f"palabras_clave['region_loc']: {palabras_clave['region_loc']}")
            elif 'subregional' in palabras_clave["region_loc"]:
                print("Entrando en la parte de subregional...")
                valor = []
                i += 1
                while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != 'region_loc'):
                    valor.append(palabras[i])
                    i += 1
                
                    if valor:
                        if re.match(r'^\d+-\d+$', valor[0]):  # Rango como 5-6
                            region_param = f"SUB. R.E. {valor[0]}"
                            criterios["region_loc"] = [region_param]
                            print(f"Subregional con rango encontrada: {criterios['region_loc']}")
                        elif re.match(r'^\d+[-]?[A-Za-z]$', valor[0]):  # Como 1-A, 1-B
                            region_param = f"SUB. R.E. {valor[0]}"
                            criterios["region_loc"] = [region_param]
                            print(f"Subregional con formato correcto: {criterios['region_loc']}")
                        elif valor[0].isdigit():  # Caso simple: Solo un número
                            region_param = f"SUB. R.E. {valor[0]}"
                            criterios["region_loc"] = [region_param]
                            print(f"Subregional simple encontrada: {criterios['region_loc']}")
                        else:
                            print("Formato de subregional no válido.")
        
        elif palabra in palabras_clave["oferta"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "oferta"):
                valor.append(palabras[i])
                i += 1

            oferta_raw = " ".join(valor).strip()

            # Normalización y asignación de la oferta
            if "primaria" in oferta_raw:
                if "adultos" in oferta_raw:
                    criterios["oferta"] = ["Adultos - Primaria"]
                elif "especial" in oferta_raw:
                    criterios["oferta"] = ["Especial - Primaria"]
                else:
                    criterios["oferta"] = ["Común - Primaria"]
            elif "snu" in oferta_raw:
                criterios["oferta"] = ["Común - SNU"]
            elif "inicial" in oferta_raw:            
                if "especial" in oferta_raw:
                    criterios["oferta"] = ["Especial - Jardín"] 
                else:
                    criterios["oferta"] = ["Común - Jardín"]
            elif "especial" in oferta_raw:
                if "cursos" in oferta_raw:
                    criterios["oferta"] = ["Especial - Cursos/Talleres de la Escuela Especial"]
                elif "domiciliaria" in oferta_raw:
                    criterios["oferta"] = ["Especial - Domiciliaria-hospitalaria"]
                elif "hospitalaria" in oferta_raw:
                    criterios["oferta"] = ["Especial - Domiciliaria-hospitalaria"]
                elif "integral" in oferta_raw:
                    criterios["oferta"] = ["Especial - Educación Integral para Adolescentes y Jóvenes"]
                elif "integracion" in oferta_raw:
                    criterios["oferta"] = ["Especial - Integración"]
                else:
                    criterios["oferta"] = ["Especial - Taller de"]
            elif "secundaria" in oferta_raw:
                if "adultos" in oferta_raw:
                    criterios["oferta"] = ["Adultos - Secundaria Completa"]
                else:
                    criterios["oferta"] = ["Común - Secundaria"]
            else:
                criterios["oferta"] = [ofer.strip() for ofer in oferta_raw.split(" y ")]

            print(f"Oferta encontrada: {criterios['oferta']}")

        
        elif palabra in palabras_clave["localidad"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "localidad"):
                valor.append(palabras[i])
                i += 1
            criterios["localidad"] = [loc.strip() for loc in " ".join(valor).split(" y ")]
            print(f"Localidad encontrada: {criterios['localidad']}")
        
        elif palabra in palabras_clave["calle"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "calle"):
                valor.append(palabras[i])
                i += 1
            criterios["calle"] = " ".join(valor).strip()
            print(f"Calle encontrada: {criterios['calle']}")
        
        elif palabra in palabras_clave["ambito"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "ambito"):
                valor.append(palabras[i])
                i += 1
            criterios["ambito"] = " ".join(valor).strip()
            print(f"Ámbito encontrado: {criterios['ambito']}")
        
        elif palabra in palabras_clave["sector"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "sector"):
                valor.append(palabras[i])
                i += 1

            sector_raw = " ".join(valor).strip()

            # Normalización y asignación de sector
            if "gestion" in sector_raw:
                if "social" in sector_raw or "comunitaria" in sector_raw:
                    criterios["sector"] = ["Gestión Social/Cooperativa"]
                else:
                    criterios["sector"] = ["Privado"]
            else:
                # Corrección en la variable que se usa dentro del bucle
                criterios["sector"] = [sect.strip() for sect in sector_raw.split(" y ")]  # Cambié "ofer" por "sect"

            print(f"Sector encontrado: {criterios['sector']}")

        
        elif palabra in palabras_clave["etiqueta"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "etiqueta"):
                valor.append(palabras[i])
                i += 1
            criterios["etiqueta"] = " ".join(valor).strip()
            print(f"Etiqueta encontrada: {criterios['etiqueta']}")
        
        elif palabra in palabras_clave["departamento"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "departamento"):
                valor.append(palabras[i])
                i += 1
            criterios["departamento"] = [loc.strip() for loc in " ".join(valor).split(" y ")]
            print(f"Departamento encontrado: {criterios['departamento']}")
        
        elif palabra in palabras_clave["cueanexo"]:
            valor = []
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "cueanexo"):
                valor.append(palabras[i])
                i += 1
            criterios["cueanexo"] = [loc.strip() for loc in " ".join(valor).split(" y ")]
            print(f"Cueanexos encontrados: {criterios['cueanexo']}")
        
        elif palabra in palabras_clave["acronimo"]:     
            valor = []  # Asegurémonos de que valor esté bien definido, tal vez falte esta línea al principio.
            i += 1
            while i < len(palabras) and not any(palabras[i] in palabras_clave[key] for key in palabras_clave if key != "acronimo"):
                valor.append(palabras[i])
                i += 1

            acron_raw = " ".join(valor).strip()
            print("acron",acron_raw)
            # Normalización y asignación de acrónimo
            if "biblioteca" in acron_raw or "bibliotecas" in acron_raw:              
                criterios["acronimo"] = ["BI%"]
            elif "escuela bilingue" in acron_raw or "escuela bilingüe" in acron_raw:
                criterios["acronimo"] = ["EPGCBII%"]
            elif "artistica" in acron_raw or "artisticas" in acron_raw:
                criterios["acronimo"] = ["ARTISTICA"]
            elif "escuela tecnica" in acron_raw or "escuelas tecnicas" in acron_raw:
                criterios["acronimo"] = ["EET"]
            elif "escuela aeronautica" in acron_raw:
                criterios["acronimo"] = ["EET-A"]
            elif "cef" in acron_raw:
                criterios["acronimo"] = ["CEF"]
            elif "proyecto" in acron_raw or "proyectos" in acron_raw:
                criterios["acronimo"] = ["PE"]
            elif "escuela especial" in acron_raw or "escuelas especiales" in acron_raw:
                criterios["acronimo"] = ["EEE"]
            elif "formacion profesional" in acron_raw or "formaciones profesionales" in acron_raw:
                criterios["acronimo"] = ["EFP"]
            elif "escuela adulto primaria" in acron_raw or "escuelas adulto primaria" in acron_raw:
                criterios["acronimo"] = ["EPA%"]
            elif "escuela adulto secundaria" in acron_raw or "escuelas adulto secundaria" in acron_raw:
                criterios["acronimo"] = ["ESJA%"]
            elif "escuela gestion social" in acron_raw or "escuelas gestion social" in acron_raw:
                criterios["acronimo"] = ["EPGS"]    
            elif "escuelas secundarias comunes" in acron_raw or "escuelas secundarias comunes" in acron_raw:
                criterios["acronimo"] = ["EES"]
            elif "escuelas hospitalarias" in acron_raw or "escuelas hospitalarias" in acron_raw:
                criterios["acronimo"] = ["HOSPITALARIA"]
            elif "jardin de infantes" in acron_raw or "jardines de infantes" in acron_raw:
                criterios["acronimo"] = ["JI%"]
            elif "jardin maternal" in acron_raw or "jardines maternales" in acron_raw:
                criterios["acronimo"] = ["JM"]
            elif "snu" in acron_raw or "institutos superiores" in acron_raw:
                criterios["acronimo"] = ["SNU"]
            elif "escuela primaria comun" in acron_raw or "escuelas primarias comunes" in acron_raw:
                criterios["acronimo"] = ["EEP"]
            elif "taller" in acron_raw or "talleres" in acron_raw:
                criterios["acronimo"] = ["TALLERES"]
            elif "unne" in acron_raw or "universidad" in acron_raw:
                criterios["acronimo"] = ["UNNE"]
            else:
                # Corrección en la variable que se usa dentro del bucle
                criterios["acronimo"] = [acr.strip() for acr in acron_raw.split(" y ")]

            print(f"Acrónimo encontrado: {criterios['acronimo']}")
        else:
            i+=1
    
    return criterios


def operaciones_comunes(request, template_name='mapa/ofertasmark.html'):   
    consulta_texto = request.GET.get("query", "")
    print("Consulta ingresada:", consulta_texto)
    
    criterios = extraer_criterios(consulta_texto)
    print(criterios)
    cursor = connection.cursor()
    query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, cui_loc, cuof_loc, acronimo, etiqueta FROM v_capa_unica_ofertas_cui_cuof WHERE 1=1 "
    parameters = []
    
    # Agregar condiciones según los criterios
    for campo, valor in criterios.items():
        if valor and campo != "region_loc":  # Excluimos region_loc aquí:
            if campo == "cueanexo":  # Caso especial para cueanexo (convertir a texto)
                if isinstance(valor, list):
                    query += f" AND ({' OR '.join([f'CAST(cueanexo AS TEXT) ILIKE %s' for _ in valor])})"
                    parameters.extend([f"%{v}%" for v in valor])
                else:
                    query += " AND CAST(cueanexo AS TEXT) ILIKE %s"
                    parameters.append(f"%{valor}%")
            else:  # Para los demás campos
                if isinstance(valor, list):  # Si el valor es una lista (ej. varias localidades)
                    query += f" AND ({' OR '.join([f'{campo} ILIKE %s' for _ in valor])})"
                    parameters.extend([f"%{v}%" for v in valor])            
                else:  # Si es un solo valor (str)
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
