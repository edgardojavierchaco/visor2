(function () {
    "use strict";

    const root = document.querySelector("[data-pof-anexo-admin]");
    const api = window.pofApi || null;

    if (!root || !api) {
        return;
    }

    const urls = {
        catalogo: root.dataset.catalogoUrl || "",
        catalogoCrear: root.dataset.catalogoCrearUrl || "",
        catalogoDesactivarBase: root.dataset.catalogoDesactivarUrlBase || "",
        catalogoReactivarBase: root.dataset.catalogoReactivarUrlBase || "",
        catalogoHistorialBase: root.dataset.catalogoHistorialUrlBase || "",
        asociaciones: root.dataset.asociacionesUrl || "",
        asociar: root.dataset.asociarUrl || "",
        asociacionDesactivar: root.dataset.asociacionDesactivarUrl || "",
        asociacionReactivar: root.dataset.asociacionReactivarUrl || "",
        asociacionesHistorial: root.dataset.asociacionesHistorialUrl || ""
    };

    const catalogoForm = root.querySelector("[data-anexo-catalogo-form]");
    const catalogoCodigo = root.querySelector("[data-anexo-catalogo-codigo]");
    const catalogoCrear = root.querySelector("[data-anexo-catalogo-crear]");
    const catalogoStatus = root.querySelector("[data-anexo-catalogo-status]");
    const catalogoBody = root.querySelector("[data-anexo-catalogo-body]");

    const propietarioForm = root.querySelector("[data-anexo-propietario-form]");
    const propietarioTipo = root.querySelector("[data-anexo-propietario-tipo]");
    const propietarioValor = root.querySelector("[data-anexo-propietario-valor]");
    const propietarioLabel = root.querySelector("[data-anexo-propietario-label]");
    const propietarioStatus = root.querySelector("[data-anexo-propietario-status]");
    const cuofNote = root.querySelector("[data-anexo-cuof-note]");
    const ownerPanel = root.querySelector("[data-anexo-owner-panel]");
    const ownerTitle = root.querySelector("[data-anexo-owner-title]");
    const ownerRefresh = root.querySelector("[data-anexo-owner-refresh]");

    const codigoDisponible = root.querySelector("[data-anexo-codigo-disponible]");
    const asociarButton = root.querySelector("[data-anexo-asociar]");
    const asociacionStatus = root.querySelector("[data-anexo-asociacion-status]");
    const asociacionesBody = root.querySelector("[data-anexo-asociaciones-body]");
    const asociacionesHistorialBody = root.querySelector("[data-anexo-asociaciones-historial-body]");

    const catalogoHistoryModal = root.querySelector("[data-anexo-catalogo-history-modal]");
    const catalogoHistoryLabel = root.querySelector("[data-anexo-catalogo-history-label]");
    const catalogoHistoryStatus = root.querySelector("[data-anexo-catalogo-history-status]");
    const catalogoHistoryBody = root.querySelector("[data-anexo-catalogo-history-body]");

    let catalogo = [];
    let propietarioActual = null;
    let asociacionesActuales = [];
    let asociacionesCargadas = false;

    function escaparHtml(valor) {
        return String(valor == null ? "" : valor)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function urlConId(base, id) {
        return String(base || "").replace("/0/", "/" + encodeURIComponent(String(id)) + "/");
    }

    function formatoFecha(valor) {
        if (!valor) {
            return "—";
        }
        const fecha = new Date(valor);
        if (Number.isNaN(fecha.getTime())) {
            return String(valor);
        }
        return new Intl.DateTimeFormat("es-AR", {
            dateStyle: "short",
            timeStyle: "short"
        }).format(fecha);
    }

    function usuarioVisible(usuario) {
        if (!usuario) {
            return "Sistema";
        }
        return usuario.texto || "Usuario";
    }

    function badgeActivo(activo, textoActivo, textoInactivo, claseExtra) {
        const clase = activo ? "pof-badge pof-badge-open" : "pof-badge pof-badge-closed";
        return '<span class="' + clase + (claseExtra ? " " + claseExtra : "") + '">' +
            escaparHtml(activo ? textoActivo : textoInactivo) +
            "</span>";
    }

    function setButtonLoading(button, loading, textoLoading) {
        if (!button) {
            return;
        }
        if (!button.dataset.labelOriginal) {
            button.dataset.labelOriginal = button.innerHTML;
        }
        button.disabled = !!loading;
        if (loading) {
            button.textContent = textoLoading || "Procesando...";
        } else {
            button.innerHTML = button.dataset.labelOriginal;
        }
    }

    function renderCatalogo() {
        if (!catalogoBody) {
            return;
        }

        if (!catalogo.length) {
            catalogoBody.innerHTML =
                '<tr><td colspan="4" class="pof-empty">El catálogo está vacío. Agregá el primer Código Anexo POF.</td></tr>';
            return;
        }

        catalogoBody.innerHTML = catalogo.map(function (item) {
            const accion = item.activo
                ? '<button type="button" class="pof-grid-action-btn pof-grid-action-btn-danger" data-anexo-catalogo-action="desactivar" data-catalogo-id="' + item.id + '">Desactivar</button>'
                : '<button type="button" class="pof-grid-action-btn pof-grid-action-btn-primary" data-anexo-catalogo-action="reactivar" data-catalogo-id="' + item.id + '">Reactivar</button>';

            return '<tr>' +
                '<td class="pof-grid-cell-center"><span class="pof-anexo-code">' + escaparHtml(item.codigo) + '</span></td>' +
                '<td class="pof-grid-cell-center">' + badgeActivo(item.activo, "Activo", "Inactivo") + '</td>' +
                '<td class="pof-grid-cell-center">' + escaparHtml(formatoFecha(item.actualizado_en)) + '</td>' +
                '<td class="pof-grid-cell-actions"><div class="pof-grid-actions">' +
                    '<button type="button" class="pof-grid-action-btn pof-grid-action-btn-detail" data-anexo-catalogo-action="historial" data-catalogo-id="' + item.id + '" data-codigo="' + escaparHtml(item.codigo) + '">Historial</button>' +
                    accion +
                '</div></td>' +
            '</tr>';
        }).join("");
    }

    function renderCodigoDisponible() {
        if (!codigoDisponible) {
            return;
        }

        const asociadosActivos = new Set(
            asociacionesActuales
                .filter(function (item) { return item.activo; })
                .map(function (item) { return Number(item.catalogo_id); })
        );

        const disponibles = catalogo.filter(function (item) {
            return item.activo && !asociadosActivos.has(Number(item.id));
        });

        codigoDisponible.innerHTML = '<option value="">Seleccionar código</option>' +
            disponibles.map(function (item) {
                return '<option value="' + item.id + '">' + escaparHtml(item.codigo) + '</option>';
            }).join("");

        codigoDisponible.disabled =
            !propietarioActual ||
            !asociacionesCargadas ||
            !disponibles.length;
        asociarButton.disabled = true;
    }

    function renderAsociaciones() {
        if (!asociacionesBody) {
            return;
        }

        if (!asociacionesActuales.length) {
            asociacionesBody.innerHTML =
                '<tr><td colspan="5" class="pof-empty">Este propietario todavía no tiene Códigos Anexo POF asociados.</td></tr>';
            renderCodigoDisponible();
            return;
        }

        asociacionesBody.innerHTML = asociacionesActuales.map(function (item) {
            let accion = "";
            if (item.activo) {
                accion = '<button type="button" class="pof-grid-action-btn pof-grid-action-btn-danger" data-anexo-asociacion-action="desactivar" data-catalogo-id="' + item.catalogo_id + '">Desactivar</button>';
            } else if (item.catalogo_activo) {
                accion = '<button type="button" class="pof-grid-action-btn pof-grid-action-btn-primary" data-anexo-asociacion-action="reactivar" data-catalogo-id="' + item.catalogo_id + '">Reactivar</button>';
            } else {
                accion = '<span class="pof-anexo-action-note">Reactivá primero el catálogo</span>';
            }

            const estadoCatalogo = item.catalogo_activo
                ? badgeActivo(true, "Disponible", "")
                : badgeActivo(false, "", "Retirado", "pof-anexo-retired-badge");

            return '<tr>' +
                '<td class="pof-grid-cell-center"><span class="pof-anexo-code">' + escaparHtml(item.codigo) + '</span></td>' +
                '<td class="pof-grid-cell-center">' + estadoCatalogo + '</td>' +
                '<td class="pof-grid-cell-center">' + badgeActivo(item.activo, "Vigente", "Inactiva") + '</td>' +
                '<td class="pof-grid-cell-center">' + escaparHtml(formatoFecha(item.actualizado_en)) + '</td>' +
                '<td class="pof-grid-cell-actions"><div class="pof-grid-actions">' + accion + '</div></td>' +
            '</tr>';
        }).join("");

        renderCodigoDisponible();
    }

    function renderHistorialPropietario(items) {
        if (!asociacionesHistorialBody) {
            return;
        }

        if (!items.length) {
            asociacionesHistorialBody.innerHTML =
                '<tr><td colspan="4" class="pof-empty">No hay movimientos registrados para este propietario.</td></tr>';
            return;
        }

        asociacionesHistorialBody.innerHTML = items.map(function (item) {
            return '<tr>' +
                '<td class="pof-grid-cell-center">' + escaparHtml(formatoFecha(item.fecha)) + '</td>' +
                '<td class="pof-grid-cell-center"><span class="pof-anexo-code">' + escaparHtml(item.codigo) + '</span></td>' +
                '<td class="pof-grid-cell-center">' + escaparHtml(item.accion_texto || item.accion) + '</td>' +
                '<td class="pof-grid-cell-center">' + escaparHtml(usuarioVisible(item.usuario)) + '</td>' +
            '</tr>';
        }).join("");
    }

    async function cargarCatalogo(mostrarEstado) {
        if (!urls.catalogo) {
            return;
        }

        try {
            const url = new URL(urls.catalogo, window.location.origin);
            url.searchParams.set("incluir_inactivos", "1");
            const response = await api.requestJsonRead(url.toString());
            catalogo = Array.isArray(response.data && response.data.codigos)
                ? response.data.codigos
                : [];
            renderCatalogo();
            renderCodigoDisponible();
            if (mostrarEstado) {
                api.showStatus(catalogoStatus, "success", "Catálogo actualizado.");
            } else {
                api.clearStatus(catalogoStatus);
            }
        } catch (error) {
            api.showStatus(catalogoStatus, "error", api.formatError(error));
        }
    }

    function propietarioDesdeFormulario() {
        const tipo = String(propietarioTipo.value || "").trim().toUpperCase();
        let valor = String(propietarioValor.value || "").trim();

        if (tipo === "CUEANEXO") {
            valor = valor.replace(/\D+/g, "");
            propietarioValor.value = valor;
            if (valor.length !== 9) {
                throw new Error("El CUEANEXO debe tener exactamente 9 dígitos.");
            }
        } else if (!valor) {
            throw new Error("Ingresá el CUOF del Proyecto Especial sin CUEANEXO.");
        }

        return { tipo: tipo, valor: valor };
    }

    function parametrosPropietario(propietario) {
        const params = new URLSearchParams();
        params.set("tipo", propietario.tipo);
        params.set("valor", propietario.valor);
        return params;
    }

    async function cargarPropietario(propietario, mostrarEstado) {
        const params = parametrosPropietario(propietario);
        const asociacionesUrl = new URL(urls.asociaciones, window.location.origin);
        asociacionesUrl.search = params.toString();
        asociacionesUrl.searchParams.set("incluir_inactivas", "1");

        const historialUrl = new URL(urls.asociacionesHistorial, window.location.origin);
        historialUrl.search = params.toString();

        const resultados = await Promise.allSettled([
            api.requestJsonRead(asociacionesUrl.toString()),
            api.requestJsonRead(historialUrl.toString())
        ]);
        const asociacionesResultado = resultados[0];
        const historialResultado = resultados[1];

        propietarioActual = propietario;
        ownerTitle.textContent = propietario.tipo + " " + propietario.valor;
        ownerPanel.classList.remove("pof-hidden");

        const errores = [];

        if (asociacionesResultado.status === "fulfilled") {
            const respuesta = asociacionesResultado.value;
            propietarioActual = respuesta.data && respuesta.data.propietario
                ? respuesta.data.propietario
                : propietario;
            asociacionesActuales = Array.isArray(
                respuesta.data && respuesta.data.asociaciones
            )
                ? respuesta.data.asociaciones
                : [];
            asociacionesCargadas = true;
            ownerTitle.textContent =
                propietarioActual.tipo + " " + propietarioActual.valor;
            renderAsociaciones();
        } else {
            asociacionesActuales = [];
            asociacionesCargadas = false;
            asociacionesBody.innerHTML =
                '<tr><td colspan="5" class="pof-empty">No se pudieron cargar las asociaciones actuales. No se habilitan cambios hasta reintentar.</td></tr>';
            renderCodigoDisponible();
            api.logError(
                "cargar asociaciones anexo pof administracion",
                asociacionesResultado.reason
            );
            errores.push(
                "Asociaciones: " + api.formatError(asociacionesResultado.reason)
            );
        }

        if (historialResultado.status === "fulfilled") {
            const respuesta = historialResultado.value;
            renderHistorialPropietario(
                Array.isArray(respuesta.data && respuesta.data.historial)
                    ? respuesta.data.historial
                    : []
            );
        } else {
            asociacionesHistorialBody.innerHTML =
                '<tr><td colspan="4" class="pof-empty">No se pudo cargar el historial del propietario.</td></tr>';
            api.logError(
                "cargar historial anexo pof administracion",
                historialResultado.reason
            );
            errores.push(
                "Historial: " + api.formatError(historialResultado.reason)
            );
        }

        if (errores.length) {
            api.showStatus(propietarioStatus, "error", errores.join(" "));
        } else if (mostrarEstado) {
            api.showStatus(propietarioStatus, "success", "Asociaciones actualizadas.");
        } else {
            api.clearStatus(propietarioStatus);
        }
    }

    async function refrescarTodoPropietario(mensaje) {
        await cargarCatalogo(false);
        if (propietarioActual) {
            await cargarPropietario(propietarioActual, false);
        }
        if (mensaje) {
            api.showStatus(asociacionStatus, "success", mensaje);
        }
    }

    function actualizarTipoPropietario() {
        const esCueanexo = propietarioTipo.value === "CUEANEXO";
        propietarioLabel.textContent = esCueanexo ? "CUEANEXO" : "CUOF";
        propietarioValor.value = "";
        propietarioValor.maxLength = esCueanexo ? 9 : 100;
        propietarioValor.inputMode = esCueanexo ? "numeric" : "text";
        propietarioValor.placeholder = esCueanexo ? "9 dígitos" : "CUOF";
        cuofNote.classList.toggle("pof-hidden", esCueanexo);
        propietarioActual = null;
        asociacionesActuales = [];
        ownerPanel.classList.add("pof-hidden");
        api.clearStatus(propietarioStatus);
        api.clearStatus(asociacionStatus);
    }

    function abrirModalHistorialCatalogo(codigo) {
        catalogoHistoryLabel.textContent = "Código Anexo POF " + codigo;
        catalogoHistoryBody.innerHTML =
            '<tr><td colspan="3" class="pof-empty">Cargando historial...</td></tr>';
        api.clearStatus(catalogoHistoryStatus);
        catalogoHistoryModal.classList.remove("pof-hidden");
        catalogoHistoryModal.setAttribute("aria-hidden", "false");
        document.body.classList.add("pof-modal-open");
    }

    function cerrarModalHistorialCatalogo() {
        catalogoHistoryModal.classList.add("pof-hidden");
        catalogoHistoryModal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("pof-modal-open");
    }

    async function cargarHistorialCatalogo(id, codigo) {
        abrirModalHistorialCatalogo(codigo);

        try {
            const response = await api.requestJsonRead(urlConId(urls.catalogoHistorialBase, id));
            const historial = Array.isArray(response.data && response.data.historial)
                ? response.data.historial
                : [];

            if (!historial.length) {
                catalogoHistoryBody.innerHTML =
                    '<tr><td colspan="3" class="pof-empty">No hay movimientos registrados.</td></tr>';
                return;
            }

            catalogoHistoryBody.innerHTML = historial.map(function (item) {
                return '<tr>' +
                    '<td class="pof-grid-cell-center">' + escaparHtml(formatoFecha(item.fecha)) + '</td>' +
                    '<td class="pof-grid-cell-center">' + escaparHtml(item.accion_texto || item.accion) + '</td>' +
                    '<td class="pof-grid-cell-center">' + escaparHtml(usuarioVisible(item.usuario)) + '</td>' +
                '</tr>';
            }).join("");
        } catch (error) {
            catalogoHistoryBody.innerHTML = "";
            api.showStatus(catalogoHistoryStatus, "error", api.formatError(error));
        }
    }

    catalogoForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const codigo = String(catalogoCodigo.value || "").trim();

        if (!codigo) {
            api.showStatus(catalogoStatus, "warning", "Ingresá un Código Anexo POF.");
            catalogoCodigo.focus();
            return;
        }

        setButtonLoading(catalogoCrear, true, "Agregando...");
        try {
            const response = await api.requestJson(urls.catalogoCrear, {
                method: "POST",
                body: { codigo: codigo }
            });
            catalogoCodigo.value = "";
            await cargarCatalogo(false);
            api.showStatus(catalogoStatus, "success", response.mensaje || "Código agregado.");
            if (propietarioActual) {
                await cargarPropietario(propietarioActual, false);
            }
        } catch (error) {
            api.showStatus(catalogoStatus, "error", api.formatError(error));
        } finally {
            setButtonLoading(catalogoCrear, false);
        }
    });

    catalogoBody.addEventListener("click", async function (event) {
        const button = event.target.closest("[data-anexo-catalogo-action]");
        if (!button) {
            return;
        }

        const action = button.dataset.anexoCatalogoAction;
        const id = button.dataset.catalogoId;
        const codigo = button.dataset.codigo || "";

        if (action === "historial") {
            await cargarHistorialCatalogo(id, codigo);
            return;
        }

        const url = action === "desactivar"
            ? urlConId(urls.catalogoDesactivarBase, id)
            : urlConId(urls.catalogoReactivarBase, id);

        setButtonLoading(button, true, action === "desactivar" ? "Desactivando..." : "Reactivando...");
        try {
            const response = await api.requestJson(url, { method: "POST" });
            await cargarCatalogo(false);
            if (propietarioActual) {
                await cargarPropietario(propietarioActual, false);
            }
            api.showStatus(catalogoStatus, "success", response.mensaje || "Catálogo actualizado.");
        } catch (error) {
            api.showStatus(catalogoStatus, "error", api.formatError(error));
        } finally {
            setButtonLoading(button, false);
        }
    });

    propietarioTipo.addEventListener("change", actualizarTipoPropietario);

    propietarioValor.addEventListener("input", function () {
        if (propietarioTipo.value === "CUEANEXO") {
            propietarioValor.value = propietarioValor.value.replace(/\D+/g, "").slice(0, 9);
        }
    });

    propietarioForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        api.clearStatus(asociacionStatus);

        let propietario;
        try {
            propietario = propietarioDesdeFormulario();
        } catch (error) {
            api.showStatus(propietarioStatus, "warning", error.message);
            propietarioValor.focus();
            return;
        }

        api.showStatus(propietarioStatus, "info", "Cargando asociaciones...");
        await cargarPropietario(propietario, false);
    });

    ownerRefresh.addEventListener("click", async function () {
        if (!propietarioActual) {
            return;
        }
        api.showStatus(propietarioStatus, "info", "Actualizando...");
        await cargarPropietario(propietarioActual, true);
    });

    codigoDisponible.addEventListener("change", function () {
        asociarButton.disabled = !codigoDisponible.value || !propietarioActual;
    });

    asociarButton.addEventListener("click", async function () {
        if (!propietarioActual || !codigoDisponible.value) {
            return;
        }

        setButtonLoading(asociarButton, true, "Asociando...");
        try {
            const response = await api.requestJson(urls.asociar, {
                method: "POST",
                body: {
                    tipo_propietario: propietarioActual.tipo,
                    propietario: propietarioActual.valor,
                    catalogo_id: Number(codigoDisponible.value)
                }
            });
            await refrescarTodoPropietario(response.mensaje || "Código asociado.");
        } catch (error) {
            api.showStatus(asociacionStatus, "error", api.formatError(error));
        } finally {
            setButtonLoading(asociarButton, false);
            asociarButton.disabled = !codigoDisponible.value || !propietarioActual;
        }
    });

    asociacionesBody.addEventListener("click", async function (event) {
        const button = event.target.closest("[data-anexo-asociacion-action]");
        if (!button || !propietarioActual) {
            return;
        }

        const action = button.dataset.anexoAsociacionAction;
        const url = action === "desactivar"
            ? urls.asociacionDesactivar
            : urls.asociacionReactivar;

        setButtonLoading(button, true, action === "desactivar" ? "Desactivando..." : "Reactivando...");
        try {
            const response = await api.requestJson(url, {
                method: "POST",
                body: {
                    tipo_propietario: propietarioActual.tipo,
                    propietario: propietarioActual.valor,
                    catalogo_id: Number(button.dataset.catalogoId)
                }
            });
            await refrescarTodoPropietario(response.mensaje || "Asociación actualizada.");
        } catch (error) {
            api.showStatus(asociacionStatus, "error", api.formatError(error));
        } finally {
            setButtonLoading(button, false);
        }
    });

    root.querySelectorAll("[data-anexo-catalogo-history-close]").forEach(function (button) {
        button.addEventListener("click", cerrarModalHistorialCatalogo);
    });

    catalogoHistoryModal.addEventListener("click", function (event) {
        if (event.target === catalogoHistoryModal) {
            cerrarModalHistorialCatalogo();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !catalogoHistoryModal.classList.contains("pof-hidden")) {
            cerrarModalHistorialCatalogo();
        }
    });

    actualizarTipoPropietario();
    cargarCatalogo(false);
}());
