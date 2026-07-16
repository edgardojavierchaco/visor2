(function () {
    "use strict";

    const modal = document.querySelector("[data-pof-quantity-history-modal]");
    const api = window.pofApi || null;

    if (!modal || !api) {
        return;
    }

    const summary = modal.querySelector("[data-pof-quantity-history-summary]");
    const status = modal.querySelector("[data-pof-quantity-history-status]");
    const content = modal.querySelector("[data-pof-quantity-history-content]");
    let triggerActivo = null;

    function limpiarElemento(elemento) {
        while (elemento && elemento.firstChild) {
            elemento.removeChild(elemento.firstChild);
        }
    }

    function valorVisible(valor) {
        if (valor === null || valor === undefined || valor === "") {
            return "—";
        }
        return String(valor);
    }

    function obtenerCargoIds(button) {
        const ids = String(button.dataset.cargoIds || "")
            .split(",")
            .map(function (valor) { return valor.trim(); })
            .filter(function (valor) { return /^\d+$/.test(valor) && Number(valor) > 0; })
            .map(Number);
        return Array.from(new Set(ids)).sort(function (a, b) { return a - b; });
    }

    function construirUrl(cargoIds) {
        const url = new URL(modal.dataset.url || "", window.location.origin);
        cargoIds.forEach(function (cargoId) {
            url.searchParams.append("cargo_id", String(cargoId));
        });
        return url.toString();
    }

    function crearItemResumen(label, valor, ancho) {
        const item = document.createElement("div");
        item.className = "pof-detail-item" + (ancho ? " pof-quantity-history-summary-wide" : "");
        const nombre = document.createElement("span");
        const contenido = document.createElement("strong");
        nombre.textContent = label;
        contenido.textContent = valorVisible(valor);
        item.appendChild(nombre);
        item.appendChild(contenido);
        return item;
    }

    function renderizarResumen(cargo) {
        limpiarElemento(summary);
        summary.appendChild(crearItemResumen("CEIC", cargo.ceic));
        summary.appendChild(crearItemResumen("Cargo", cargo.cargo, true));
        summary.appendChild(crearItemResumen("CUEANEXO", cargo.cueanexo));
        summary.appendChild(crearItemResumen("CUOF", cargo.cuof));
        summary.appendChild(crearItemResumen("Cantidad actual", cargo.cantidad_actual));
        summary.classList.remove("pof-hidden");
    }

    function crearCelda(valor) {
        const celda = document.createElement("td");
        celda.classList.add("text-center");
        celda.textContent = valorVisible(valor);
        return celda;
    }

    function crearEncabezado(titulo) {
        const th = document.createElement("th");
        th.textContent = titulo;
        return th;
    }

    function renderizarGrupo(cargo, mostrarOrigen) {
        const movimientos = Array.isArray(cargo.movimientos) ? cargo.movimientos : [];
        if (!movimientos.length) {
            return null;
        }

        const section = document.createElement("section");
        section.className = "pof-detail-section pof-quantity-history-group";
        const title = document.createElement("h3");
        title.textContent = mostrarOrigen
            ? "Registro físico #" + valorVisible(cargo.id) + " · CEIC " + valorVisible(cargo.ceic) + " · Cantidad actual " + valorVisible(cargo.cantidad_actual)
            : "Cambios de cantidad";
        section.appendChild(title);

        const wrap = document.createElement("div");
        wrap.className = "pof-table-wrap";
        const table = document.createElement("table");
        table.className = "pof-grid-table pof-quantity-history-table";
        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");
        const mostrarObservacion = movimientos.some(function (movimiento) {
            return String(movimiento.observacion || "").trim() !== "";
        });

        ["Fecha", "Anterior", "Variación", "Nueva", "Usuario"].forEach(function (titulo) {
            headerRow.appendChild(crearEncabezado(titulo));
        });
        if (mostrarObservacion) {
            headerRow.appendChild(crearEncabezado("Observación"));
        }
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        movimientos.forEach(function (movimiento) {
            const row = document.createElement("tr");
            row.appendChild(crearCelda(movimiento.fecha));
            row.appendChild(crearCelda(movimiento.cantidad_anterior));
            row.appendChild(crearCelda(movimiento.variacion));
            row.appendChild(crearCelda(movimiento.cantidad_nueva));
            row.appendChild(crearCelda(movimiento.usuario));
            if (mostrarObservacion) {
                row.appendChild(crearCelda(movimiento.observacion || ""));
            }
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        wrap.appendChild(table);
        section.appendChild(wrap);
        return section;
    }

    function renderizarHistorial(payload) {
        const cargo = payload.cargo || {};
        const cargos = Array.isArray(payload.cargos) ? payload.cargos : [];
        const cargosConCambios = cargos.filter(function (item) {
            return Array.isArray(item.movimientos) && item.movimientos.length > 0;
        });

        renderizarResumen(cargo);
        limpiarElemento(content);
        api.clearStatus(status);

        if (!payload.modificado || !cargosConCambios.length) {
            api.showStatus(status, "info", "No hay cambios reales de cantidad para este cargo.");
            return;
        }

        cargosConCambios.forEach(function (item) {
            const grupo = renderizarGrupo(item, cargos.length > 1);
            if (grupo) {
                content.appendChild(grupo);
            }
        });
    }

    function abrirModal(button) {
        triggerActivo = button;
        modal.classList.remove("pof-hidden");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("pof-modal-open");
        const cerrar = modal.querySelector("[data-pof-quantity-history-close]");
        if (cerrar) {
            cerrar.focus({preventScroll: true});
        }
    }

    function cerrarModal() {
        modal.classList.add("pof-hidden");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("pof-modal-open");
        if (triggerActivo) {
            triggerActivo.focus({preventScroll: true});
        }
        triggerActivo = null;
    }

    async function cargarHistorial(button) {
        const cargoIds = obtenerCargoIds(button);
        abrirModal(button);
        limpiarElemento(summary);
        summary.classList.add("pof-hidden");
        limpiarElemento(content);

        if (!cargoIds.length) {
            api.showStatus(status, "error", "No se pudo identificar el cargo seleccionado.");
            return;
        }

        modal.dataset.loading = "true";
        button.disabled = true;
        button.setAttribute("aria-disabled", "true");
        modal.setAttribute("aria-busy", "true");
        api.showStatus(status, "info", "Cargando historial de cantidad...");

        try {
            const respuesta = await api.requestJson(construirUrl(cargoIds), {
                method: "GET",
                credentials: "same-origin"
            });
            renderizarHistorial(respuesta.data || {});
        } catch (error) {
            api.showStatus(status, "error", api.formatError(error));
        } finally {
            modal.dataset.loading = "false";
            modal.removeAttribute("aria-busy");
            button.disabled = false;
            button.removeAttribute("aria-disabled");
        }
    }

    document.addEventListener("click", function (event) {
        const button = event.target.closest("[data-pof-quantity-history]");
        if (!button || modal.dataset.loading === "true") {
            return;
        }
        cargarHistorial(button);
    });

    modal.querySelectorAll("[data-pof-quantity-history-close]").forEach(function (button) {
        button.addEventListener("click", cerrarModal);
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            cerrarModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.classList.contains("pof-hidden")) {
            cerrarModal();
        }
    });
})();
