window.onscroll = function(){

    scroll = document.documentElement.scrollTop;

    header = document.getElementById('encabezado');

    if (scroll > 20){
        header.classList.add('nav__mod');
    }else if (scroll < 20){
        header.classList.remove('nav__mod');
    }

}

document.getElementById('btn_menu').addEventListener('click', mostrar_menu);

    menu = document.getElementById('encabezado');
    body = document.getElementById('container_all');
    nav = document.getElementById('nav');

function mostrar_menu(){

    body.classList.toggle('move__content');
    menu.classList.toggle('move__content');
    nav.classList.toggle('move__nav');
}

window.addEventListener('resize', function(){

    if (window.innerWidth > 760)  {
        body.classList.remove('move__content');
        menu.classList.remove('move__content');
        nav.classList.remove('move__nav');
    }

});