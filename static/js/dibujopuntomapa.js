let map = L.map("map", {
    center: [-25.388415775410138, -60.99025493373542],
    zoom: 6.5
});

var capa = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { attribution: "&copy; OpenStreetMap" }
).addTo(map);


let misDatos = null;
        fetch("js/v_capa_unica_ofertas.geojson")
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                
                misDatos = data; // Almacena los datos una vez que se carguen
                
            });
                

        let markers = []; // Array para almacenar los marcadores


        // Agregar el control de ubicación
        L.control.locate().addTo(map);

        // Crear un botón personalizado para calcular rutas
        let calcularRutaButton = L.easyButton({
            states: [{
                stateName: 'calcular-ruta',
                icon: 'fa-road',
                title: 'Calcular Ruta', // Título o descripción del botón
                onClick: function (control) {
                    if (markers.length >= 2) {
                        if (navigator.geolocation) {
                            navigator.geolocation.getCurrentPosition(function (position) {
                                const latLngInicio = [position.coords.latitude, position.coords.longitude]; // Obtiene la ubicación del usuario como punto de origen
                                const latLngDestino = markers[0].getLatLng(); // Coordenadas del marcador como punto de destino

                                L.Routing.control({
                                    waypoints: [latLngInicio, latLngDestino],
                                    language: 'es',
                                    routeWhileDragging: true,
                                }).addTo(map);
                            });
                        } else {
                            alert('El navegador no admite la geolocalización.');
                        }
                    } else {
                        alert('Agrega al menos un marcador en el mapa para calcular una ruta.');
                    }
                    control.state('calcular-ruta'); // Cambia el estado del botón
                },
            }],
        });

        calcularRutaButton.addTo(map); // Agrega el botón al mapa


        let drawnItems = L.featureGroup();
        map.addLayer(drawnItems);


        let drawControl = new L.Control.Draw({
            edit: {
                featureGroup: drawnItems,
                edit: {
                        title: 'Editar elementos',
                        edit: 'Editar',
                        save: 'Guardar',
                        cancel: 'Cancelar',
                    }
            },
            draw: {
                polygon: {
                    allowIntersection: false,
                    drawError: {
                        color: '#b00b00',
                        timeout: 1000
                    },
                    shapeOptions: {
                        color: '#23bfc2'
                    },
                },
                marker: true, // Habilita la herramienta de marcador
                circlemarker: false,
                rectangle: true,
                circle: {
                    allowIntersection: false,
                    drawError: {
                        color: '#b00b00',
                        timeout: 1000
                    },
                    shapeOptions: {
                        color: '#23bfc2'
                    },
                },
                polyline: {
                    metric: true,
                    feet: false,
                    shapeOptions: {
                        color: '#23bfc2'
                        title: 'Polilínea'
                    },
                },
                locateButton: { // Agrega un botón personalizado
                    title: "Encuentra cercanos", // Título del botón
                    text: "Encuentra cercanos", // Texto del botón
                    icon: { html: "📍" }, // Icono del botón (puedes personalizarlo)
                },
            },
            position: 'topright',
        });

        map.addControl(drawControl);


        // Escuchar el evento 'draw:created' para el botón "Encuentra cercanos"
        map.on('draw:created', function (e) {
            let type = e.layerType;
            let layer = e.layer;

            if (type === 'marker') {
                // Activar la funcionalidad de locate
                map.locate({
                    setView: true,
                    maxZoom: 16,
                    watch: false,
                });
            }

            drawnItems.addLayer(layer);
            markers.push(layer); // Agregar el marcador al array de marcadores
        });

        // Crear un botón personalizado para agregar marcadores
        let agregarMarcadorButton = L.easyButton({
            states: [{
                stateName: 'agregar-marcador',
                icon: 'fa-solid fa-location-crosshairs',
                title: 'Agregar Marcador de destino', // Título o descripción del botón
                onClick: function (control) {
                    map.on('click', function (e) {
                        let latLng = e.latlng; // Obtén las coordenadas del clic
                        let marker = L.marker(latLng).addTo(map);
                        markers.push(marker); // Agregar el marcador al array de marcadores
                        map.off('click'); // Detener la escucha del evento de clic después de agregar el marcador
                    });
                    control.state('agregar-marcador'); // Cambia el estado del botón
                },
            }],
        });

        agregarMarcadorButton.addTo(map); // Agrega el botón al mapa

        // Crea un botón personalizado para resetear la vista

        let resetViewButton = L.easyButton({
            states: [{
                stateName: 'reset-view',
                icon: 'fa-refresh', // Icono para el botón de reset
                title: 'Restablecer Vista', // Título o descripción del botón de reset
                onClick: function (control) {
                    // Recargar la página
                    location.reload();
                },
            }],
        });

        resetViewButton.addTo(map); // Agrega el botón de reset al mapa

        // Crear una instancia del control "EasyPrint" y agregarlo al mapa
        var easyPrint = L.easyPrint({
            title: 'Imprimir Mapa', // Título del botón de impresión
            position: 'topright', // Posición del control en el mapa
        }).addTo(map);



        // Resto de tu código para calcular distancias y mostrar marcadores cercanos
        // ...

        map.addEventListener("draw:created", function (e) {
            drawnItems.clearLayers();
            let layer = e.layer;
            drawnItems.addLayer(layer);

            if (layer instanceof L.Polyline) {
                let distance = turf.length(layer.toGeoJSON(), { units: 'kilometers' });
                alert(`Distancia: ${distance.toFixed(2)} km`);
            } else if (layer instanceof L.Circle) {
                let lat = layer._latlng.lat;
                let lng = layer._latlng.lng;
                let radio = layer._mRadius / 1000; // Radio en kilómetros
                let area = Math.PI * Math.pow(radio, 2);
                alert(`Área: ${area.toFixed(2)} km²`);
            } else if (layer instanceof L.Rectangle) {
                // Aquí puedes realizar acciones específicas para el cuadrado (rectangle) si es necesario
            } else if (layer instanceof L.Marker) {
                let lat = layer._latlng.lat;
                let lng = layer._latlng.lng;
                let punto = turf.point([lng, lat]);

                let puntoCercano = turf.nearestPoint(punto, misDatos);

                let distancia = turf.distance(punto, puntoCercano);

                // Agregar el punto más cercano a la lista
                let lista = document.querySelector('#lista');
                lista.innerHTML = ` <tr>
                    <td><a href='/map/listados/?cueanexo=${puntoCercano.properties.cueanexo}'>${puntoCercano.properties.cueanexo}</a></td>
                    <td>${puntoCercano.properties.nom_est}</td>
                    <td>${puntoCercano.properties.ambito}</td>
                    <td>${puntoCercano.properties.departamento}</td>
                    <td>${puntoCercano.properties.region_loc}</td>
                    <td>${distancia.toFixed(2)} km</td>
                </tr>`;

                // Agregar el marcador del punto más cercano al mapa
                let latlng = L.latLng(puntoCercano.geometry.coordinates[1], puntoCercano.geometry.coordinates[0]);
                L.marker(latlng).addTo(map);
            }

            if (misDatos) { // Verificar si los datos están disponibles
                if (layer instanceof L.Circle) {
                    let lat = layer._latlng.lat;
                    let lng = layer._latlng.lng;
                    let radio = layer._mRadius;
                    let point = turf.point([lng, lat]);
                    let buffered = turf.buffer(point, radio / 1000, { units: 'kilometers' });
                    let ptsWithin = turf.pointsWithinPolygon(misDatos, buffered.geometry);
                    let cadena = ptsWithin.features;

                    // Agregar marcadores al mapa
                    cadena.forEach(function (feature) {
                        let latlng = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);
                        L.marker(latlng).addTo(map);
                    });

                    let lista = document.querySelector('#lista')
                    lista.innerHTML = ''
                    for (let i of cadena) {
                        lista.innerHTML += ` <tr>
                            <td><a href='/map/listados/?cueanexo=${i.properties.cueanexo}'>${i.properties.cueanexo}</a></td>
                            <td>${i.properties.nom_est}</td>
                            <td>${i.properties.ambito}</td>
                            <td>${i.properties.departamento}</td>
                            <td>${i.properties.region_loc}</td>
                            </tr>`
                    }
                } else {
                    let geojson = layer.toGeoJSON().geometry;
                    let ptsWithin = turf.pointsWithinPolygon(misDatos, geojson)
                    let cadena = ptsWithin.features;

                    // Agregar marcadores al mapa
                    cadena.forEach(function (feature) {
                        let latlng = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);
                        L.marker(latlng).addTo(map);
                    });

                    let lista = document.querySelector('#lista')
                    lista.innerHTML = ''
                    for (let i of cadena) {
                        lista.innerHTML += ` <tr>
                            <td><a href='/map/listados/?cueanexo=${i.properties.cueanexo}'>${i.properties.cueanexo}</a></td>
                            <td>${i.properties.nom_est}</td>
                            <td>${i.properties.ambito}</td>
                            <td>${i.properties.departamento}</td>
                            <td>${i.properties.region_loc}</td>
                            </tr>`
                    }
                }
            }
        });
