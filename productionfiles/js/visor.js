const map = L.map("map").setView([-27.45,-58.98],7)

L.tileLayer(
"https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
).addTo(map)

let markersLayer = L.layerGroup().addTo(map)

function obtenerFiltros(){

return{

Cueanexo:document.getElementById("cueanexo").value,

Cui:document.getElementById("cui").value,

nom_est:document.getElementById("nom_est").value,

Modalidad:document.getElementById("modalidad").value,

Ambito:document.getElementById("ambito").value,

Sector:document.getElementById("sector").value,

Region:document.getElementById("region").value,

Oferta:document.getElementById("oferta").value

}

}

function cargarDatos(){

let params = new URLSearchParams(obtenerFiltros())

fetch("/mapas/api/filtros/?"+params)

.then(r=>r.json())

.then(data=>{

markersLayer.clearLayers()

data.forEach(e=>{

let m = L.marker([e.lat,e.long])

.bindPopup(
"<b>"+e.nom_est+"</b><br>"+
e.oferta
)

markersLayer.addLayer(m)

})

})

}

document.querySelectorAll("#sidebar select,#sidebar input")
.forEach(e=>{

e.addEventListener("change",cargarDatos)

e.addEventListener("keyup",cargarDatos)

})

cargarDatos()