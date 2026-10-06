(function () {
    "use strict";

    const modal = document.querySelector("[data-pof-observation-history-modal]");
    const api = window.pofApi || null;

    if (!modal || !api) {
        return;
    }

    const summary = modal.querySelector("[data-pof-observation-history-summary]");
    const status = modal.querySelector("[data-pof-observation-history-status]");
    const content = modal.querySelector("[data-pof-observation-history-content]");
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

    function crearItemResumen(label, valor, clase) {
        const item = document.createElement("div");
        item.className = "pof-detail-item" + (clase ? " " + clase : "");
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
        summary.appendChild(crearItemResumen("Cargo", cargo.cargo));
        summary.appendChild(crearItemResumen("CUEANEXO", cargo.cueanexo));
        summary.appendChild(crearItemResumen("CUOF", cargo.cuof));
        summary.appendChild(crearItemResumen("Observación actual", cargo.observacion_actual, "pof-observation-history-summary-observation"));
        summary.classList.remove("pof-hidden");
    }

    function crearBloqueObservacion(etiqueta, valor, clase) {
        const bloque = document.createElement("div");
        bloque.className = "pof-observation-timeline-value " + (clase || "");

        const label = document.createElement("span");
        label.className = "pof-observation-timeline-value-label";
        label.textContent = etiqueta;

        const texto = document.createElement("div");
        texto.className = "pof-observation-timeline-value-text";
        texto.textContent = valorVisible(valor);

        bloque.appendChild(label);
        bloque.appendChild(texto);
        return bloque;
    }

    function crearEventoTimeline(evento, indice, abiertoPorDefecto) {
        const entrada = document.createElement("div");
        entrada.className = "pof-observation-timeline-entry";
        entrada.style.setProperty("--pof-observation-event-index", String(indice));

        const nodo = document.createElement("span");
        nodo.className = "pof-observation-timeline-node";
        nodo.setAttribute("aria-hidden", "true");
        entrada.appendChild(nodo);

        const tarjeta = document.createElement("article");
        tarjeta.className = "pof-observation-timeline-card";

        const cabecera = document.createElement("div");
        cabecera.className = "pof-observation-timeline-head";

        const meta = document.createElement("div");
        meta.className = "pof-observation-timeline-meta";

        const fecha = document.createElement("span");
        fecha.className = "pof-observation-timeline-date";
        fecha.textContent = valorVisible(evento.fecha);

        const usuario = document.createElement("span");
        usuario.className = "pof-observation-timeline-user";
        usuario.textContent = valorVisible(evento.usuario);

        meta.appendChild(fecha);
        meta.appendChild(usuario);

        const badge = document.createElement("span");
        badge.className =
            "pof-observation-timeline-badge " +
            (evento.tipo_evento === "inicial"
                ? "pof-observation-timeline-badge-initial"
                : "pof-observation-timeline-badge-change");
        badge.textContent =
            evento.label ||
            (evento.tipo_evento === "inicial"
                ? "Observación inicial"
                : "Observación modificada");

        cabecera.appendChild(meta);
        cabecera.appendChild(badge);
        tarjeta.appendChild(cabecera);

        if (evento.tipo_evento === "inicial") {
            tarjeta.appendChild(
                crearBloqueObservacion(
                    "Valor inicial",
                    evento.valor_inicial || evento.resumen,
                    "pof-observation-timeline-value-initial"
                )
            );
        } else {
            const resumen = document.createElement("div");
            resumen.className = "pof-observation-timeline-current";
            resumen.textContent = valorVisible(
                evento.resumen || evento.observacion_nueva
            );
            tarjeta.appendChild(resumen);

            const acciones = document.createElement("div");
            acciones.className = "pof-observation-timeline-actions";
            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "pof-observation-timeline-toggle";
            toggle.setAttribute("aria-expanded", abiertoPorDefecto ? "true" : "false");
            toggle.textContent = abiertoPorDefecto ? "Ocultar cambio" : "Ver cambio";
            acciones.appendChild(toggle);
            tarjeta.appendChild(acciones);

            const detalle = document.createElement("div");
            detalle.className = "pof-observation-timeline-change";
            if (!abiertoPorDefecto) {
                detalle.classList.add("pof-hidden");
            }
            detalle.appendChild(
                crearBloqueObservacion(
                    "Antes",
                    evento.observacion_anterior,
                    "pof-observation-timeline-value-before"
                )
            );
            detalle.appendChild(
                crearBloqueObservacion(
                    "Después",
                    evento.observacion_nueva,
                    "pof-observation-timeline-value-after"
                )
            );
            tarjeta.appendChild(detalle);

            toggle.addEventListener("click", function () {
                const abrir = detalle.classList.contains("pof-hidden");
                detalle.classList.toggle("pof-hidden", !abrir);
                toggle.setAttribute("aria-expanded", abrir ? "true" : "false");
                toggle.textContent = abrir ? "Ocultar cambio" : "Ver cambio";
            });
        }

        entrada.appendChild(tarjeta);
        return entrada;
    }

    function renderizarGrupo(cargo, mostrarOrigen) {
        const movimientos = Array.isArray(cargo.movimientos) ? cargo.movimientos : [];
        if (!movimientos.length) {
            return null;
        }

        const section = document.createElement("section");
        section.className = "pof-observation-timeline-group";

        if (mostrarOrigen) {
            const title = document.createElement("h3");
            title.className = "pof-observation-timeline-group-title";
            title.textContent =
                "Registro físico #" + valorVisible(cargo.id) +
                " · CEIC " + valorVisible(cargo.ceic);
            section.appendChild(title);
        }

        const timeline = document.createElement("div");
        timeline.className = "pof-observation-timeline";

        movimientos.forEach(function (movimiento, indice) {
            timeline.appendChild(
                crearEventoTimeline(
                    movimiento,
                    indice,
                    false
                )
            );
        });

        section.appendChild(timeline);
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
            api.showStatus(status, "info", "No hay historial de observación registrado para este cargo.");
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
        const cerrar = modal.querySelector("[data-pof-observation-history-close]");
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
        api.showStatus(status, "info", "Cargando historial de observación...");

        try {
            const respuesta = await api.requestJsonRead(construirUrl(cargoIds), {
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
        const button = event.target.closest("[data-pof-observation-history]");
        if (!button || modal.dataset.loading === "true") {
            return;
        }
        cargarHistorial(button);
    });

    modal.querySelectorAll("[data-pof-observation-history-close]").forEach(function (button) {
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
