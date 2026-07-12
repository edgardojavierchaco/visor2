document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // CONTROLES
    // =====================================================

    const inputCue = document.getElementById("id_cueanexo");
    const inputNombre = document.getElementById("id_nom_est");

    const selectCui = document.getElementById("id_cui");
    const selectOferta = document.getElementById("id_oferta");

    const lista = document.getElementById("resultadoEscuelas");

    if (!inputCue) {
        return;
    }

    let temporizador = null;

    // =====================================================
    // BUSCADOR
    // =====================================================

    inputCue.addEventListener("keyup", function () {

        const texto = this.value.trim();

        clearTimeout(temporizador);

        if (texto.length < 3) {

            lista.innerHTML = "";

            limpiarFormulario();

            return;
        }

        temporizador = setTimeout(function () {

            buscarEscuelas(texto);

        }, 300);

    });

    // =====================================================
    // CONSULTA API
    // =====================================================

    function buscarEscuelas(texto) {

        fetch(`/sirtee/api/escuelas/?q=${encodeURIComponent(texto)}`)

            .then(response => {

                if (!response.ok) {

                    throw new Error("Error consultando escuelas");

                }

                return response.json();

            })

            .then(data => {

                mostrarResultados(data);

            })

            .catch(error => {

                console.error(error);

            });

    }

    // =====================================================
    // LISTADO
    // =====================================================

    function mostrarResultados(escuelas) {

        lista.innerHTML = "";

        if (!Array.isArray(escuelas)) {

            return;

        }

        escuelas.forEach(function (escuela) {

            const boton = document.createElement("button");

            boton.type = "button";

            boton.className =
                "list-group-item list-group-item-action";

            boton.innerHTML = `
                <strong>${escuela.cueanexo}</strong><br>
                ${escuela.nom_est}<br>
                <small>${(escuela.oferta || []).join(", ")}</small>
            `;

            boton.addEventListener("click", function () {

                seleccionarEscuela(escuela);

            });

            lista.appendChild(boton);

        });

    }

    // =====================================================
    // SELECCIONAR
    // =====================================================

    function seleccionarEscuela(escuela) {

        inputCue.value = escuela.cueanexo;

        inputNombre.value = escuela.nom_est || "";

        cargarSelect(
            selectCui,
            escuela.cui || []
        );

        cargarSelect(
            selectOferta,
            escuela.oferta || []
        );

        lista.innerHTML = "";

    }

    // =====================================================
    // CARGAR SELECT MULTIPLE
    // =====================================================

    function cargarSelect(select, valores) {

        if (!select) {

            return;

        }

        select.innerHTML = "";

        if (!Array.isArray(valores)) {

            valores = [valores];

        }

        valores.forEach(function (valor) {

            const option = document.createElement("option");

            option.value = valor;

            option.textContent = valor;

            option.selected = true;

            select.appendChild(option);

        });

        actualizarSelect2(select);

    }

    // =====================================================
    // LIMPIAR
    // =====================================================

    function limpiarFormulario() {

        inputNombre.value = "";

        if (selectCui) {

            selectCui.innerHTML = "";

            actualizarSelect2(selectCui);

        }

        if (selectOferta) {

            selectOferta.innerHTML = "";

            actualizarSelect2(selectOferta);

        }

    }

    // =====================================================
    // REFRESCAR SELECT2
    // =====================================================

    function actualizarSelect2(select) {

        if (window.jQuery && $(select).hasClass("select2")) {

            $(select).trigger("change");

        }

    }

});