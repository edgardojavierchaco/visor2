//Ejecutar funcion en el evento click
document.getElementById("btn_open").addEventListener("click", open_close_menu);

//Declaramos las variables
var side_menu=document.getElementById("menu_side");
var btn_open=document.getElementById("btn_open");
var body=document.getElementById("body");

//EVento para mostrar u ocultar el sidebar
function open_close_menu(){
    body.classList.toggle("body_move");
    side_menu.classList.toggle("menu__side_move");
}

//si el ancho de la página es menor a 760 px, ocultará el menú al recargar la página
if (window.innerWidth<760){
    body.classList.add("body_move");
    side_menu.classList.add("menu__side_move");
}

//hace que el menú sea responsive
window.addEventListener("resize", function(){
    if (window.innerWidth>760){
        body.classList.remove("body_move");
        side_menu.classList.remove("menu__side_move");
    }
    if (window.innerWidth < 760){

        body.classList.add("body_move");
        side_menu.classList.add("menu__side_move");
    }
})