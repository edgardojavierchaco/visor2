// Ejecutar función en el evento click
document.getElementById('btn_open').addEventListener('click', openCloseMenu);

// Declaramos las variables
var sideMenu = document.getElementById('menu_side');
var btnOpen = document.getElementById('btn_open');
var body = document.getElementById('body');

// Evento para mostrar u ocultar el sidebar
function openCloseMenu() {
    body.classList.toggle('body_move');
    sideMenu.classList.toggle('menu__side_move');
}

// Si el ancho de la página es menor a 760 px, ocultará el menú al recargar la página
if (window.innerWidth < 760) {
    body.classList.add('body_move');
    sideMenu.classList.add('menu__side_move');
}

// Hace que el menú sea responsive
window.addEventListener('resize', function () {
    if (window.innerWidth > 760) {
        body.classList.remove('body_move');
        sideMenu.classList.remove('menu__side_move');
    }
    if (window.innerWidth < 760) {
        body.classList.add('body_move');
        sideMenu.classList.add('menu__side_move');
    }
});

