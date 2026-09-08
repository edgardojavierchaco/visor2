function openTab(tab, event) {

    // ocultar contenidos
    document.querySelectorAll(".tab-content")
        .forEach(t => t.classList.remove("active"));


    // quitar activo de tabs
    document.querySelectorAll(".nav-link")
        .forEach(b => b.classList.remove("active"));


    // mostrar tab seleccionado
    document.getElementById("tab-" + tab)
        .classList.add("active");


    // activar botón seleccionado
    if (event) {
        event.target.classList.add("active");
    }


    // reinicializar Select2 dentro de tabs
    setTimeout(() => {

        if (window.jQuery && $.fn.select2) {

            $('.select2').select2({
                width: '100%'
            });

        }

    }, 50);

}