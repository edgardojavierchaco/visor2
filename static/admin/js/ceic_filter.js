document.addEventListener("DOMContentLoaded", function () {

    const modalidad = document.getElementById("id_modalidad");
    const nivel = document.getElementById("id_niveles");
    const ceic = document.getElementById("id_ceic");

    function actualizarCEIC() {
        const modalidadVal = modalidad.value;
        const nivelVal = nivel.value;

        if (!modalidadVal) return;

        // UX: bloquear nivel si no es modalidad 1
        if (parseInt(modalidadVal) !== 1) {
            nivel.disabled = true;
        } else {
            nivel.disabled = false;
        }

        fetch(`/bnhpersonas/filtrar-ceic/?modalidad=${modalidadVal}&nivel=${nivelVal}`)
            .then(r => r.json())
            .then(data => {
                ceic.innerHTML = '';

                data.forEach(item => {
                    const opt = document.createElement("option");
                    opt.value = item.c_ceic;
                    opt.text = item.descripcion;
                    ceic.appendChild(opt);
                });
            });
    }

    modalidad.addEventListener("change", actualizarCEIC);
    nivel.addEventListener("change", actualizarCEIC);
});