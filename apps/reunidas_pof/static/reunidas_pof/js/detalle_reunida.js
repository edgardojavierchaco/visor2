(function () {
    "use strict";

    /**
     * Inicializa controles visuales del panel de filtros del Detalle comun.
     *
     * - Mantiene el panel desplegado sin enviar el formulario.
     * - Valida CUEANEXO, CUE, Anexo, CUOF y CEIC en frontend como apoyo a la validacion backend.
     * - Muestra acciones cuando el usuario escribe o cambia filtros, sin auto-submit.
     * - Permite aplicar con Enter solo dentro de inputs del panel de filtros.
     */
    function initDetalleReunidaFiltros() {
        const botonFiltros = document.querySelector(".js-detalle-filtros-toggle");
        const panelFiltros = document.getElementById("detalleFiltrosPanel");
        const campoCueanexo = document.getElementById("filtroDetalleCueanexo");
        const campoCue = document.getElementById("filtroDetalleCue");
        const campoAnexo = document.getElementById("filtroDetalleAnexo");
        const campoCuof = document.getElementById("filtroDetalleCuof");
        const campoCeic = document.getElementById("filtroDetalleCeic");
        const formularioFiltros = panelFiltros ? panelFiltros.closest("form") : null;
        const controlesFiltros = formularioFiltros ? Array.from(
            formularioFiltros.querySelectorAll("input[type='text'], select")
        ) : [];
        const accionesFiltros = formularioFiltros ? formularioFiltros.querySelector("[data-detalle-filter-actions]") : null;
        const botonFiltrar = formularioFiltros ? formularioFiltros.querySelector(".js-detalle-filtrar") : null;

        if (botonFiltros && panelFiltros) {
            panelFiltros.hidden = false;
            botonFiltros.setAttribute("aria-expanded", "true");

            botonFiltros.addEventListener("click", function () {
                panelFiltros.hidden = false;
                botonFiltros.setAttribute("aria-expanded", "true");
            });
        }

        function mostrarAccionesFiltros() {
            if (accionesFiltros) {
                accionesFiltros.classList.remove("pof-hidden");
            }
        }

        function hayValoresFiltroDetalle() {
            return controlesFiltros.some(function (control) {
                return String(control.value || "").trim() !== "";
            });
        }

        function actualizarBotonFiltrarDetalle() {
            if (!botonFiltrar) {
                return;
            }

            const activo = hayValoresFiltroDetalle();
            botonFiltrar.disabled = !activo;
            botonFiltrar.setAttribute("aria-disabled", activo ? "false" : "true");
        }

        [
            [campoCueanexo, /^[0-9]{9}$/, "El filtro CUEANEXO debe tener 9 d\u00edgitos."],
            [campoCue, /^[0-9]{7}$/, "El filtro CUE debe tener 7 d\u00edgitos."],
            [campoAnexo, /^[0-9]{2}$/, "El filtro Anexo debe contener exactamente 2 d\u00edgitos."],
            [campoCuof, /^[0-9]+$/, "El filtro CUOF contiene un valor inv\u00e1lido."],
        ].forEach(function (configuracion) {
            const campo = configuracion[0];
            const patron = configuracion[1];
            const mensaje = configuracion[2];
            if (!campo) {
                return;
            }
            campo.addEventListener("input", function () {
                const valor = campo.value.trim();
                campo.setCustomValidity(!valor || patron.test(valor) ? "" : mensaje);
            });
        });

        if (campoCeic) {
            campoCeic.addEventListener("input", function () {
                const valor = campoCeic.value.trim();
                const ceicValido = !valor || (/^[0-9]{1,3}$/.test(valor) && Number(valor) > 0);
                campoCeic.setCustomValidity(ceicValido ? "" : "El filtro CEIC debe contener entre 1 y 3 d\u00edgitos y ser mayor a 0.");
            });
        }

        controlesFiltros.forEach(function (control) {
            control.addEventListener("input", function () {
                mostrarAccionesFiltros();
                actualizarBotonFiltrarDetalle();
            });
            control.addEventListener("change", function () {
                mostrarAccionesFiltros();
                actualizarBotonFiltrarDetalle();
            });
        });

        if (formularioFiltros) {
            formularioFiltros.addEventListener("keydown", function (event) {
                const target = event.target;
                if (target && target.matches("#detalleColumnaInput, #detalleBuscarOpcionFiltro")) {
                    return;
                }
                const esInputValido = target && target.matches("input[type='text'], input[type='number']");
                if (event.key !== "Enter" || !esInputValido) {
                    return;
                }
                event.preventDefault();
                if (typeof formularioFiltros.requestSubmit === "function") {
                    formularioFiltros.requestSubmit();
                } else {
                    if (typeof formularioFiltros.checkValidity === "function" && !formularioFiltros.checkValidity()) {
                        if (typeof formularioFiltros.reportValidity === "function") {
                            formularioFiltros.reportValidity();
                        }
                        return;
                    }
                    formularioFiltros.submit();
                }
            });
        }

        actualizarBotonFiltrarDetalle();
    }

    /**
     * Inicializa el buscador por columna y el panel avanzado del Detalle.
     *
     * - Reutiliza el patron visual de Visualizacion sin panel de columnas ni acciones Excel.
     * - Envía filtros por GET para conservar enlaces compartibles y paginacion simple.
     * - Usa opciones embebidas desde backend para evitar listas hardcodeadas en JavaScript.
     */
    function initDetalleReunidaFiltrosDinamicos() {
        const form = document.getElementById("detalleReunidaFiltrosForm");
        if (!form || form.dataset.detalleFiltrosDinamicos !== "1") {
            return;
        }

        const liveSearch = document.getElementById("detalleLiveSearch");
        const columnaSelect = document.getElementById("detalleColumnaSelect");
        const columnaInput = document.getElementById("detalleColumnaInput");
        const limpiarBusquedaColumnaBtn = document.getElementById("detalleLimpiarBusquedaColumna");
        const busquedaColumnaLoading = document.getElementById("detalleBusquedaColumnaLoading");
        const busquedaColumnaStatus = document.getElementById("detalleBusquedaColumnaStatus");
        const busquedaColumnaStatusText = document.getElementById("detalleBusquedaColumnaStatusText");
        const panelFiltros = document.getElementById("detallePanelFiltros");
        const toggleFiltros = form.querySelector("[data-detalle-panel-toggle='filtros']");
        const filtrosActivos = document.getElementById("detalleFiltrosActivos");
        const dialog = document.getElementById("detalleDialogFiltro");
        const dialogBackdrop = document.getElementById("detalleFiltroBackdrop");
        const dialogTitulo = document.getElementById("detalleDialogTitulo");
        const campoFiltroActivo = document.getElementById("detalleCampoFiltroActivo");
        const operadorFiltro = document.getElementById("detalleOperadorFiltro");
        const valorFiltroLabel = document.getElementById("detalleValorFiltroLabel");
        const valorFiltroMount = document.getElementById("detalleValorFiltroMount");
        const cerrarDialogoFiltro = document.getElementById("detalleCerrarDialogoFiltro");
        const filtroAplicarBtn = document.querySelector("#detalleDialogFiltro .pof-filter-apply-btn");
        const filterButtons = Array.from(form.querySelectorAll(".pof-visual-filter-btn"));
        const commonFilterUI = window.POFCommonFilterUI;
        const SEARCH_COLUMNS = ["cue", "anexo", "cui", "cuof", "cargo", "nombre_establecimiento"];
        const FILTER_OPERATOR_PRESETS = commonFilterUI.filterOperatorPresets;
        const sameFilterCriterion = commonFilterUI.sameFilterCriterion;
        const firstOperatorForConfig = commonFilterUI.firstOperatorForConfig;
        const fieldConfig = {};
        let filterOptions = {};
        const opcionesFiltroUrl = form.dataset.detalleOpcionesFiltroUrl || "";
        const apiDetalle = window.pofApi || null;
        const REMOTE_CHECKLIST_FIELDS = new Set([
            "region",
            "localidad",
            "departamento",
            "ambito",
            "categoria",
            "jornada",
            "acronimo",
            "estado_localizacion_padron",
            "estado_oferta_padron",
            "estado_establecimiento_padron"
        ]);
        const loadedRemoteFilters = new Set();
        const remoteFilterRequests = new Map();
        let searchInteractionDirty = false;
        let filterDialogState = null;
        let appliedColumnSearch = {
            columnId: columnaSelect ? columnaSelect.value : "",
            value: (columnaInput && columnaInput.value || "").trim()
        };

        const opcionesIniciales = document.getElementById("detalleFiltrosOpcionesData");
        if (opcionesIniciales) {
            try {
                filterOptions = JSON.parse(opcionesIniciales.textContent || "{}") || {};
            } catch (error) {
                window.console.error("No se pudieron leer las opciones iniciales de filtros del detalle.", error);
            }
        }

        filterButtons.forEach(function (button) {
            fieldConfig[button.dataset.filterField] = {
                field: button.dataset.filterField,
                label: button.dataset.filterLabel,
                mode: button.dataset.filterMode || "text",
                operators: button.dataset.filterOperators || "text"
            };
        });

        function escapeHtml(value) {
            return String(value == null ? "" : value)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        function clearColumnSearchParams(url) {
            SEARCH_COLUMNS.forEach(function (columnId) {
                url.searchParams.delete("col_" + columnId);
            });
            return url;
        }

        function setColumnSearchLoading(active) {
            if (busquedaColumnaLoading) {
                busquedaColumnaLoading.classList.toggle("pof-hidden", !active);
                busquedaColumnaLoading.setAttribute("aria-hidden", active ? "false" : "true");
            }
            if (liveSearch) {
                liveSearch.classList.toggle("pof-visual-search-busy", active);
                liveSearch.setAttribute("aria-busy", active ? "true" : "false");
            }
            if (busquedaColumnaStatus) {
                busquedaColumnaStatus.classList.toggle("pof-visual-search-status-hidden", !active);
                busquedaColumnaStatus.setAttribute("aria-hidden", active ? "false" : "true");
            }
            if (active && busquedaColumnaStatusText) {
                busquedaColumnaStatusText.textContent = "Buscando resultados...";
            }
        }

        function getColumnSearchState() {
            return {
                columnId: columnaSelect ? columnaSelect.value : "",
                value: (columnaInput && columnaInput.value || "").trim()
            };
        }

        function sameColumnSearchState(left, right) {
            return Boolean(left && right)
                && left.columnId === right.columnId
                && left.value === right.value;
        }

        function isColumnSearchInteractiveTarget(target) {
            if (!target || typeof target.closest !== "function") {
                return false;
            }
            return Boolean(target.closest(
                "button, a, input, select, textarea, label, "
                + "[role='button'], [role='link'], [contenteditable='true'], "
                + "[data-filter-chip], .pof-visual-dialog, .pof-visual-dialog-backdrop"
            ));
        }

        function markColumnSearchInteractionDirty() {
            searchInteractionDirty = true;
        }

        function submitColumnSearch() {
            const nextState = getColumnSearchState();
            if (sameColumnSearchState(appliedColumnSearch, nextState)) {
                searchInteractionDirty = false;
                setColumnSearchLoading(false);
                return;
            }
            const value = (columnaInput ? columnaInput.value : "").trim();
            const columnId = columnaSelect ? columnaSelect.value : "";
            const url = new URL(window.location.href);
            clearColumnSearchParams(url);
            if (value && SEARCH_COLUMNS.indexOf(columnId) !== -1) {
                url.searchParams.set("col_" + columnId, value);
            }
            url.searchParams.delete("page");
            if (url.toString() === window.location.href) {
                appliedColumnSearch = nextState;
                searchInteractionDirty = false;
                setColumnSearchLoading(false);
                return;
            }
            appliedColumnSearch = nextState;
            searchInteractionDirty = false;
            setColumnSearchLoading(true);
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    window.location.href = url.toString();
                });
            });
        }

        function clearColumnSearch() {
            const url = new URL(window.location.href);
            clearColumnSearchParams(url);
            url.searchParams.delete("page");
            if (columnaInput) {
                columnaInput.value = "";
            }
            appliedColumnSearch = {
                columnId: columnaSelect ? columnaSelect.value : "",
                value: ""
            };
            searchInteractionDirty = false;
            if (url.toString() === window.location.href) {
                setColumnSearchLoading(false);
                return;
            }
            setColumnSearchLoading(true);
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    window.location.href = url.toString();
                });
            });
        }

        function handleColumnSearchPointerDown(event) {
            if (liveSearch && event.target && liveSearch.contains(event.target)) {
                return;
            }
            if (isColumnSearchInteractiveTarget(event.target)) {
                return;
            }
            if (searchInteractionDirty) {
                submitColumnSearch();
            }
        }

        function togglePanelFiltros() {
            if (!panelFiltros || !toggleFiltros) {
                return;
            }
            const abrir = panelFiltros.hidden;
            panelFiltros.hidden = !abrir;
            toggleFiltros.classList.toggle("pof-visual-toggle-active", abrir);
            toggleFiltros.setAttribute("aria-expanded", abrir ? "true" : "false");
        }

        function getAdvancedFilterForField(field) {
            const params = new URLSearchParams(window.location.search || "");
            const campos = params.getAll("campo_filtro");
            const operadores = params.getAll("operador_filtro");
            const valores = params.getAll("valor_filtro");
            for (let index = 0; index < campos.length; index += 1) {
                if (campos[index] === field && valores[index]) {
                    return {
                        index: String(index),
                        operator: operadores[index] || "0",
                        value: valores[index]
                    };
                }
            }
            return null;
        }

        /**
         * Resuelve el criterio que debe precargarse en el dialogo del Detalle.
         *
         * - Prioriza el chip que el usuario eligio editar.
         * - Reconoce una busqueda rapida aplicada sobre el mismo campo.
         * - Conserva el comportamiento previo al abrir un filtro ya aplicado.
         */
        function getFilterDialogInitialState(config, editState) {
            if (editState && editState.field === config.field) {
                return {
                    source: editState.source || "avanzado",
                    index: editState.index == null ? null : String(editState.index),
                    param: editState.param || "",
                    operator: editState.operator || firstOperatorForConfig(config),
                    values: Array.isArray(editState.values) ? editState.values : [],
                    disableUntilChanged: true
                };
            }

            if (appliedColumnSearch.columnId === config.field && appliedColumnSearch.value) {
                return {
                    source: "columna",
                    index: null,
                    param: "",
                    operator: firstOperatorForConfig(config),
                    values: [appliedColumnSearch.value],
                    disableUntilChanged: true
                };
            }

            const advanced = getAdvancedFilterForField(config.field);
            if (advanced) {
                return {
                    source: "avanzado",
                    index: advanced.index,
                    param: "",
                    operator: advanced.operator,
                    values: [advanced.value],
                    disableUntilChanged: true
                };
            }

            return {
                source: "nuevo",
                index: null,
                param: "",
                operator: firstOperatorForConfig(config),
                values: [],
                disableUntilChanged: false
            };
        }

        function getCurrentFilterDialogState() {
            return {
                operator: operadorFiltro ? operadorFiltro.value : "",
                values: collectFilterValues()
            };
        }

        function syncFilterApplyButton() {
            if (!filtroAplicarBtn) {
                return;
            }
            const initial = filterDialogState && filterDialogState.initial;
            filtroAplicarBtn.disabled = Boolean(
                filterDialogState
                && filterDialogState.disableUntilChanged
                && sameFilterCriterion(initial, getCurrentFilterDialogState())
            );
        }

        function renderTextValueControl(mode, initialValue) {
            const type = mode === "number" ? "number" : "text";
            valorFiltroLabel.textContent = "Valor";
            valorFiltroMount.innerHTML = '<input type="' + type + '" id="detalleValorFiltro" class="pof-visual-dialog-input" autocomplete="off">';
            const input = document.getElementById("detalleValorFiltro");
            if (input) {
                input.value = initialValue == null ? "" : initialValue;
                input.focus();
            }
            syncFilterApplyButton();
        }

        function obtenerOpcionValorEtiqueta(opcion) {
            return {
                value: typeof opcion === "object" ? opcion.value : opcion,
                label: typeof opcion === "object" ? opcion.label : opcion
            };
        }

        function obtenerGrupoOferta(label) {
            const texto = String(label || "").trim();
            const partes = texto.split(" - ");
            if (partes.length > 1 && partes[0].trim()) {
                return partes[0].trim();
            }
            if (["Común", "Especial", "Adultos"].indexOf(texto) !== -1) {
                return texto;
            }
            return texto.toLowerCase() === "sin información" ? "Común" : "Otros";
        }

        function renderOpcionChecklist(value, label, selectedValues) {
            return '<label class="pof-visual-dialog-option" data-option-text="' + escapeHtml(commonFilterUI.normalizeText(label)) + '">'
                + '<input type="checkbox" value="' + escapeHtml(value) + '"' + (selectedValues.has(String(value)) ? " checked" : "") + '>'
                + '<span>' + escapeHtml(label) + '</span></label>';
        }

        function renderOpcionesOferta(opciones, selectedValues) {
            const grupos = {};
            const orden = [];
            opciones.forEach(function (opcion) {
                const item = obtenerOpcionValorEtiqueta(opcion);
                const grupo = obtenerGrupoOferta(item.label);
                if (!grupos[grupo]) {
                    grupos[grupo] = [];
                    orden.push(grupo);
                }
                if (String(item.label).trim() !== grupo || grupo === "Sin Información" || grupo === "Otros") {
                    grupos[grupo].push(item);
                }
            });

            const ordenPreferido = ["Común", "Especial", "Adultos", "Sin Información", "Otros"];
            orden.sort(function (a, b) {
                const ia = ordenPreferido.indexOf(a);
                const ib = ordenPreferido.indexOf(b);
                if (ia !== -1 || ib !== -1) {
                    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
                }
                return a.localeCompare(b);
            });

            return orden.map(function (grupo) {
                const opcionesGrupo = grupos[grupo];
                if (!opcionesGrupo.length && grupo === "Otros") {
                    return "";
                }
                let htmlGrupo = '<div class="pof-visual-dialog-section" data-option-section>';
                htmlGrupo += '<div class="pof-visual-dialog-section-title">' + escapeHtml(grupo) + '</div>';
                htmlGrupo += '<div class="pof-visual-dialog-section-grid">';
                opcionesGrupo.forEach(function (item) {
                    htmlGrupo += renderOpcionChecklist(item.value, item.label, selectedValues);
                });
                htmlGrupo += '</div></div>';
                return htmlGrupo;
            }).join("");
        }

        function renderChecklistValueControl(field, options, initialValues) {
            const selectedValues = new Set(initialValues || []);
            const opciones = Array.isArray(options) ? options : [];
            valorFiltroLabel.textContent = "Opciones";
            if (!opciones.length) {
                valorFiltroMount.innerHTML = '<div class="pof-visual-dialog-empty">Sin opciones disponibles.</div>';
                syncFilterApplyButton();
                return;
            }

            let html = '<input type="text" id="detalleBuscarOpcionFiltro" class="pof-visual-dialog-input" autocomplete="off" placeholder="Buscar opcion">';
            html += '<div class="pof-visual-dialog-options' + (field === "oferta" ? ' pof-visual-dialog-options-grouped' : '') + '" id="detalleOpcionesFiltro">';
            if (field === "oferta") {
                html += renderOpcionesOferta(opciones, selectedValues);
            } else {
                opciones.forEach(function (opcion) {
                    const item = obtenerOpcionValorEtiqueta(opcion);
                    html += renderOpcionChecklist(item.value, item.label, selectedValues);
                });
            }
            html += "</div>";
            valorFiltroMount.innerHTML = html;

            const search = document.getElementById("detalleBuscarOpcionFiltro");
            const optionsRoot = document.getElementById("detalleOpcionesFiltro");
            if (search && optionsRoot) {
                commonFilterUI.bindDialogOptionSearch(search, optionsRoot);
                search.focus();
            }
            syncFilterApplyButton();
        }

        /**
         * Carga una sola vez el catálogo remoto del campo activo del Detalle.
         *
         * - Usa únicamente GET contra el endpoint autenticado del Detalle común.
         * - Reutiliza el resultado en memoria durante la vida de la página.
         * - Valida campo, lista y formato antes de incorporarlos al control.
         */
        async function cargarOpcionesFiltroRemoto(campo) {
            if (!opcionesFiltroUrl || !apiDetalle || !REMOTE_CHECKLIST_FIELDS.has(campo)) {
                return true;
            }
            if (loadedRemoteFilters.has(campo)) {
                return true;
            }

            const solicitudExistente = remoteFilterRequests.get(campo);
            if (solicitudExistente) {
                return solicitudExistente;
            }

            const url = new URL(opcionesFiltroUrl, window.location.href);
            url.searchParams.set("campo", campo);
            const solicitud = apiDetalle.requestJson(url.toString(), {method: "GET"})
                .then(function (data) {
                    const opciones = data && data.opciones;
                    const opcionesValidas = Array.isArray(opciones) && opciones.every(function (opcion) {
                        return typeof opcion === "string" || (
                            opcion &&
                            typeof opcion === "object" &&
                            Object.prototype.hasOwnProperty.call(opcion, "value") &&
                            Object.prototype.hasOwnProperty.call(opcion, "label")
                        );
                    });
                    if (!data || data.ok !== true || data.campo !== campo || !opcionesValidas) {
                        throw new Error("Respuesta inválida del catálogo de filtros.");
                    }
                    filterOptions[campo] = opciones;
                    loadedRemoteFilters.add(campo);
                    return true;
                })
                .catch(function () {
                    if (filterDialogState && filterDialogState.field === campo) {
                        valorFiltroLabel.textContent = "Opciones";
                        valorFiltroMount.innerHTML = '<div class="pof-visual-dialog-empty">No se pudieron cargar las opciones. Intentá nuevamente.</div>';
                        if (filtroAplicarBtn) {
                            filtroAplicarBtn.disabled = true;
                        }
                    }
                    return false;
                })
                .finally(function () {
                    if (remoteFilterRequests.get(campo) === solicitud) {
                        remoteFilterRequests.delete(campo);
                    }
                });
            remoteFilterRequests.set(campo, solicitud);
            return solicitud;
        }

        function prepararDialogoFiltro(config, editState) {
            const initial = getFilterDialogInitialState(config, editState);
            campoFiltroActivo.value = config.field;
            dialogTitulo.textContent = config.label;
            operadorFiltro.innerHTML = (FILTER_OPERATOR_PRESETS[config.operators] || FILTER_OPERATOR_PRESETS.text).map(function (operator) {
                return '<option value="' + escapeHtml(operator.value) + '">' + escapeHtml(operator.label) + '</option>';
            }).join("");
            operadorFiltro.value = initial.operator;
            if (!operadorFiltro.value) {
                operadorFiltro.value = firstOperatorForConfig(config);
            }
            filterDialogState = {
                source: initial.source,
                index: initial.index,
                param: initial.param,
                field: config.field,
                initial: {
                    operator: operadorFiltro.value,
                    values: initial.values.slice()
                },
                disableUntilChanged: initial.disableUntilChanged
            };
            if (filtroAplicarBtn) {
                filtroAplicarBtn.disabled = initial.disableUntilChanged;
            }
            dialog.hidden = false;
            dialogBackdrop.hidden = false;
        }

        /**
         * Abre el dialogo de un filtro y espera el catalogo remoto solo si corresponde.
         *
         * - Conserva la apertura inmediata de filtros locales y de Proyecto Especial.
         * - Evita renderizar una respuesta tardía sobre otro campo o dialogo.
         */
        async function openFilterDialog(config, editState) {
            if (!dialog || !dialogBackdrop || !campoFiltroActivo || !operadorFiltro || !valorFiltroMount) {
                return;
            }
            prepararDialogoFiltro(config, editState);
            if (config.mode === "checklist") {
                if (opcionesFiltroUrl && REMOTE_CHECKLIST_FIELDS.has(config.field)) {
                    valorFiltroLabel.textContent = "Opciones";
                    valorFiltroMount.innerHTML = '<div class="pof-visual-dialog-empty">Cargando opciones...</div>';
                    if (filtroAplicarBtn) {
                        filtroAplicarBtn.disabled = true;
                    }
                    const cargadas = await cargarOpcionesFiltroRemoto(config.field);
                    if (
                        !cargadas ||
                        !filterDialogState ||
                        filterDialogState.field !== config.field ||
                        campoFiltroActivo.value !== config.field
                    ) {
                        return;
                    }
                }
                renderChecklistValueControl(
                    config.field,
                    filterOptions[config.field],
                    filterDialogState.initial.values
                );
            } else {
                renderTextValueControl(config.mode, filterDialogState.initial.values[0] || "");
            }
        }

        function closeFilterDialog() {
            if (dialog) {
                dialog.hidden = true;
            }
            if (dialogBackdrop) {
                dialogBackdrop.hidden = true;
            }
            if (campoFiltroActivo) {
                campoFiltroActivo.value = "";
            }
            filterDialogState = null;
            if (valorFiltroMount) {
                valorFiltroMount.innerHTML = "";
            }
        }

        function collectFilterValues() {
            const config = fieldConfig[campoFiltroActivo.value];
            if (!config) {
                return [];
            }
            if (config.mode === "checklist") {
                return Array.from(valorFiltroMount.querySelectorAll('input[type="checkbox"]:checked'))
                    .map(function (checkbox) { return checkbox.value; })
                    .filter(Boolean);
            }
            const input = document.getElementById("detalleValorFiltro");
            const value = input ? input.value.trim() : "";
            return value ? [value] : [];
        }

        function replaceFilterValuesForField(url, field, operator, values) {
            const params = url.searchParams;
            const campos = params.getAll("campo_filtro");
            const operadores = params.getAll("operador_filtro");
            const valores = params.getAll("valor_filtro");
            params.delete("campo_filtro");
            params.delete("operador_filtro");
            params.delete("valor_filtro");

            campos.forEach(function (campo, index) {
                if (campo === field) {
                    return;
                }
                params.append("campo_filtro", campo);
                params.append("operador_filtro", operadores[index] || "0");
                params.append("valor_filtro", valores[index] || "");
            });

            values.forEach(function (value) {
                params.append("campo_filtro", field);
                params.append("operador_filtro", operator);
                params.append("valor_filtro", value);
            });
            params.delete("page");
        }

        /**
         * Reemplaza un unico filtro avanzado del Detalle por su indice paralelo.
         *
         * - Conserva otros criterios del mismo campo.
         * - Evita duplicar el chip que origino la edicion.
         * - Mantiene alineados campo, operador y valor en la querystring.
         */
        function replaceAdvancedFilterByIndex(url, indexToReplace, field, operator, values) {
            const params = url.searchParams;
            const campos = params.getAll("campo_filtro");
            const operadores = params.getAll("operador_filtro");
            const valores = params.getAll("valor_filtro");
            params.delete("campo_filtro");
            params.delete("operador_filtro");
            params.delete("valor_filtro");

            campos.forEach(function (campo, index) {
                if (String(index) === String(indexToReplace)) {
                    return;
                }
                params.append("campo_filtro", campo);
                params.append("operador_filtro", operadores[index] || "0");
                params.append("valor_filtro", valores[index] || "");
            });

            values.forEach(function (value) {
                params.append("campo_filtro", field);
                params.append("operador_filtro", operator);
                params.append("valor_filtro", value);
            });
            params.delete("page");
        }

        function removeAdvancedFilterByIndex(url, indexToRemove) {
            const params = url.searchParams;
            const campos = params.getAll("campo_filtro");
            const operadores = params.getAll("operador_filtro");
            const valores = params.getAll("valor_filtro");
            params.delete("campo_filtro");
            params.delete("operador_filtro");
            params.delete("valor_filtro");

            campos.forEach(function (campo, index) {
                if (String(index) === String(indexToRemove)) {
                    return;
                }
                params.append("campo_filtro", campo);
                params.append("operador_filtro", operadores[index] || "0");
                params.append("valor_filtro", valores[index] || "");
            });
            params.delete("page");
        }

        /**
         * Abre el dialogo con el criterio representado por un chip del Detalle.
         *
         * - Reutiliza la configuracion del campo y sus controles actuales.
         * - Conserva el indice para editar solo el criterio avanzado elegido.
         * - Mantiene como origen la busqueda rapida o el filtro simple correspondiente.
         */
        function editFilterFromChip(chip) {
            const field = chip.dataset.filterEditField || chip.dataset.filterField;
            const config = fieldConfig[field];
            if (!config) {
                return;
            }
            const type = chip.dataset.filterType;
            openFilterDialog(config, {
                source: type,
                field: field,
                index: type === "avanzado" ? chip.dataset.filterIndex : null,
                param: type === "simple" ? chip.dataset.filterField : "",
                operator: chip.dataset.filterOperator || firstOperatorForConfig(config),
                values: chip.dataset.filterValue ? [chip.dataset.filterValue] : []
            });
        }

        function clearFilterFromChip(chip) {
            const url = new URL(window.location.href);
            const type = chip.dataset.filterType;
            const field = chip.dataset.filterField;
            if (type === "avanzado") {
                removeAdvancedFilterByIndex(url, chip.dataset.filterIndex);
            } else if (type === "simple" && field) {
                url.searchParams.delete(field);
            } else if (type === "columna" && field) {
                url.searchParams.delete("col_" + field);
            }
            url.searchParams.delete("page");
            window.location.href = url.toString();
        }

        if (toggleFiltros) {
            toggleFiltros.addEventListener("click", togglePanelFiltros);
        }
        if (limpiarBusquedaColumnaBtn) {
            limpiarBusquedaColumnaBtn.addEventListener("click", clearColumnSearch);
        }
        if (columnaInput) {
            columnaInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                }
            });
            columnaInput.addEventListener("input", markColumnSearchInteractionDirty);
        }
        if (columnaSelect) {
            columnaSelect.addEventListener("change", markColumnSearchInteractionDirty);
        }
        document.addEventListener("pointerdown", handleColumnSearchPointerDown, true);

        filterButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                const config = fieldConfig[button.dataset.filterField];
                if (config) {
                    void openFilterDialog(config);
                }
            });
        });

        if (operadorFiltro) {
            operadorFiltro.addEventListener("change", syncFilterApplyButton);
        }
        if (valorFiltroMount) {
            valorFiltroMount.addEventListener("input", syncFilterApplyButton);
            valorFiltroMount.addEventListener("change", syncFilterApplyButton);
        }

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!campoFiltroActivo || !campoFiltroActivo.value) {
                return;
            }
            if (filtroAplicarBtn && filtroAplicarBtn.disabled) {
                return;
            }
            const values = collectFilterValues();
            const url = new URL(window.location.href);
            const field = campoFiltroActivo.value;
            const operator = operadorFiltro.value || "0";
            if (filterDialogState && filterDialogState.source === "columna") {
                url.searchParams.delete("col_" + field);
                replaceFilterValuesForField(url, field, operator, values);
            } else if (filterDialogState && filterDialogState.source === "avanzado"
                && filterDialogState.index !== null && filterDialogState.index !== "") {
                replaceAdvancedFilterByIndex(url, filterDialogState.index, field, operator, values);
            } else if (filterDialogState && filterDialogState.source === "simple"
                && filterDialogState.param) {
                if (operator === filterDialogState.initial.operator && values.length <= 1) {
                    if (values.length) {
                        url.searchParams.set(filterDialogState.param, values[0]);
                    } else {
                        url.searchParams.delete(filterDialogState.param);
                    }
                    url.searchParams.delete("page");
                } else {
                    url.searchParams.delete(filterDialogState.param);
                    replaceFilterValuesForField(url, field, operator, values);
                }
            } else {
                replaceFilterValuesForField(url, field, operator, values);
            }
            closeFilterDialog();
            window.location.href = url.toString();
        });

        if (cerrarDialogoFiltro) {
            cerrarDialogoFiltro.addEventListener("click", closeFilterDialog);
        }
        if (dialogBackdrop) {
            dialogBackdrop.addEventListener("click", closeFilterDialog);
        }
        if (filtrosActivos) {
            filtrosActivos.addEventListener("click", function (event) {
                const chip = event.target.closest("[data-filter-chip]");
                if (!chip || !filtrosActivos.contains(chip)) {
                    return;
                }
                const removeControl = event.target.closest("[data-filter-chip-remove]");
                if (removeControl && chip.contains(removeControl)) {
                    event.preventDefault();
                    clearFilterFromChip(chip);
                    return;
                }
                const editControl = event.target.closest("[data-filter-chip-edit]");
                if (editControl && chip.contains(editControl)) {
                    event.preventDefault();
                    editFilterFromChip(chip);
                }
            });
        }
    }

    /**
     * Inicializa la carga diferida de cargos en el Detalle de Reunida común.
     *
     * - Escucha solo los botones `.js-detalle-grupo-toggle` ya renderizados.
     * - Consulta el endpoint existente por `cueanexo` y `cuof` solo al hacer clic.
     * - No precarga cargos en el HTML inicial y reutiliza el grupo ya cargado.
     */
    function initDetalleReunidaAjax() {
      const apiDetalle = window.pofApi || null;
      const botonesDetalleGrupo = Array.from(
        document.querySelectorAll(".js-detalle-grupo-toggle"),
      );

      const GRUPO_REAPERTURA_STORAGE_KEY = "pof.detalleReunida.grupoReapertura";

      if (!apiDetalle || !botonesDetalleGrupo.length) {
        return;
      }

      function obtenerTextoDetalleGrupo(valor) {
        if (valor === null || valor === undefined || valor === "") {
          return "—";
        }
        return String(valor);
      }

      /**
       * Guarda temporalmente qué Anexo/CUOF estaba abierto.
       *
       * - Usa sessionStorage, limitado a la pestaña actual.
       * - No modifica filtros ni agrega parámetros artificiales a la URL.
       */
      function guardarGrupoParaReapertura(trigger) {
        if (!trigger) {
          return;
        }

        const cueanexo = String(trigger.dataset.cueanexo || "").trim();
        const cuof = String(trigger.dataset.cuof || "").trim();
        const localizacionId = String(
          trigger.dataset.localizacionId || "",
        ).trim();

        if (!localizacionId && (!cueanexo || !cuof)) {
          return;
        }

        try {
          window.sessionStorage.setItem(
            GRUPO_REAPERTURA_STORAGE_KEY,
            JSON.stringify(
              localizacionId
                ? { localizacionId: localizacionId }
                : { cueanexo: cueanexo, cuof: cuof },
            ),
          );
        } catch (error) {
          // La reapertura automática es una mejora de UX;
          // no debe bloquear el CRUD si sessionStorage no está disponible.
        }
      }

      /**
       * Recupera una única vez el grupo pendiente de reapertura.
       */
      function obtenerGrupoParaReapertura() {
        try {
          const valor = window.sessionStorage.getItem(
            GRUPO_REAPERTURA_STORAGE_KEY,
          );

          window.sessionStorage.removeItem(GRUPO_REAPERTURA_STORAGE_KEY);

          if (!valor) {
            return null;
          }

          const grupo = JSON.parse(valor);

          if (
            !grupo ||
            (!grupo.localizacionId && (!grupo.cueanexo || !grupo.cuof))
          ) {
            return null;
          }

          return grupo;
        } catch (error) {
          return null;
        }
      }

      function limpiarContenedorDetalleGrupo(elemento) {
        while (elemento && elemento.firstChild) {
          elemento.removeChild(elemento.firstChild);
        }
      }

      function crearCeldaDetalleGrupo(valor) {
        const celda = document.createElement("td");
        celda.textContent = obtenerTextoDetalleGrupo(valor);
        return celda;
      }

      function crearCeldaCantidadDetalleGrupo(cargo) {
        const celda = document.createElement("td");
        const contenido = document.createElement("span");
        contenido.className = "pof-quantity-cell";
        contenido.appendChild(
          document.createTextNode(obtenerTextoDetalleGrupo(cargo.cantidad)),
        );

        if (cargo.tiene_modificacion_cantidad) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "pof-history-detail-btn pof-quantity-history-btn";
          button.dataset.pofQuantityHistory = "true";
          button.dataset.cargoIds = Array.isArray(cargo.cargo_ids)
            ? cargo.cargo_ids.join(",")
            : "";
          button.setAttribute("aria-label", "Ver historial de cantidad");
          button.title = "Ver historial de cantidad";
          button.textContent = "\uD83D\uDD51";
          contenido.appendChild(button);
        }

        celda.appendChild(contenido);
        return celda;
      }

      function crearCeldaModificacionCantidad(cargo) {
        const celda = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = cargo.tiene_modificacion_cantidad
          ? "pof-grid-badge pof-grid-badge-modificacion"
          : "pof-grid-badge pof-grid-badge-desafectado";
        badge.textContent = cargo.tiene_modificacion_cantidad
          ? "Modificado"
          : "Sin modificación";
        celda.appendChild(badge);
        return celda;
      }

      function crearCeldaObservacionDetalleGrupo(cargo) {
        const celda = document.createElement("td");
        const contenido = document.createElement("span");
        contenido.className = "pof-quantity-cell";
        contenido.appendChild(
          document.createTextNode(obtenerTextoDetalleGrupo(cargo.observacion)),
        );

        if (cargo.tiene_modificacion_observacion === true) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "pof-history-detail-btn pof-quantity-history-btn";
          button.dataset.pofObservationHistory = "true";
          button.dataset.cargoIds = Array.isArray(cargo.cargo_ids)
            ? cargo.cargo_ids.join(",")
            : "";
          button.setAttribute("aria-label", "Ver historial de observación");
          button.title = "Ver historial de observación";
          button.textContent = "🕘";
          contenido.appendChild(button);
        }

        celda.appendChild(contenido);
        return celda;
      }

      /**
       * Construye la celda Estado reutilizando los badges y el trigger de historial existentes.
       *
       * - No crea una variante visual nueva.
       * - Afectado reutiliza `pof-grid-badge-afectado`.
       * - Desafectado reutiliza `pof-grid-badge-desafectado`.
       * - El trigger de historial solo aparece ante un cambio real informado por backend.
       */
      function crearCeldaEstadoDetalleGrupo(cargo) {
        const celda = document.createElement("td");
        const contenido = document.createElement("span");
        const badge = document.createElement("span");
        const estado = String(cargo.estado || "").trim();
        const estadoNormalizado = estado.toUpperCase();

        contenido.className = "pof-quantity-cell";

        badge.className = estadoNormalizado.startsWith("DESAFECT")
          ? "pof-grid-badge pof-grid-badge-desafectado"
          : "pof-grid-badge pof-grid-badge-afectado";

        badge.textContent = obtenerTextoDetalleGrupo(estado);

        contenido.appendChild(badge);

        if (cargo.tiene_modificacion_estado === true) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "pof-history-detail-btn pof-quantity-history-btn";
          button.dataset.pofStateHistory = "true";
          button.dataset.cargoIds = Array.isArray(cargo.cargo_ids)
            ? cargo.cargo_ids.join(",")
            : "";
          button.setAttribute("aria-label", "Ver historial de Estado POF");
          button.title = "Ver historial de Estado POF";
          button.textContent = "\uD83D\uDD51";
          contenido.appendChild(button);
        }

        celda.appendChild(contenido);
        return celda;
      }

      /**
       * Obtiene los IDs físicos válidos asociados a una fila visible del Detalle.
       *
       * - Elimina duplicados.
       * - Descarta IDs inválidos.
       * - Evita editar arbitrariamente una fila consolidada con varios cargos físicos.
       */
      function obtenerCargoIdsDetalleGrupo(cargo) {
        if (!Array.isArray(cargo.cargo_ids)) {
          return [];
        }

        const ids = cargo.cargo_ids
          .map(function (cargoId) {
            return Number(cargoId);
          })
          .filter(function (cargoId) {
            return Number.isInteger(cargoId) && cargoId > 0;
          });

        return Array.from(new Set(ids));
      }

      /**
       * Construye la acción rápida para gestionar un cargo desde el Detalle.
       *
       * - Reutiliza el modal CRUD compartido.
       * - Solo permite edición directa cuando existe un único CargoPof real.
       * - Conserva CUEANEXO y CUOF para reabrir el mismo grupo después del guardado.
       */
      function crearCeldaAccionDetalleGrupo(cargo, contextoGrupo) {
        const celda = document.createElement("td");
        const cargoIds = obtenerCargoIdsDetalleGrupo(cargo);

        if (cargoIds.length !== 1) {
          celda.textContent = "—";
          return celda;
        }

        const cargoId = cargoIds[0];
        const boton = document.createElement("button");

        boton.type = "button";
        boton.className = "pof-grid-icon-btn pof-admin-gear-btn";
        boton.dataset.cargoGestion = "true";
        boton.dataset.cargoId = String(cargoId);
        boton.dataset.cueanexo = contextoGrupo.cueanexo || "";
        boton.dataset.cuof = contextoGrupo.cuof || "";
        boton.dataset.localizacionId = contextoGrupo.localizacionId || "";

        boton.title = "Gestionar este cargo";
        boton.setAttribute(
          "aria-label",
          "Gestionar cargo ID " + String(cargoId),
        );

        boton.textContent = "✏️";

        celda.appendChild(boton);
        return celda;
      }

      /**
       * Construye la tarjeta anidada de cargos correspondiente a un Anexo/CUOF.
       *
       * - Refuerza visualmente la jerarquía CUE -> Anexo/CUOF -> cargos.
       * - Reutiliza los badges de estado existentes.
       * - Añade la gestión rápida mediante el modal CRUD compartido.
       */
      function crearTablaDetalleGrupo(cargos, contextoGrupo) {
        const tarjeta = document.createElement("div");
        tarjeta.className = "pof-detalle-cargos-card";

        const cabecera = document.createElement("div");
        cabecera.className = "pof-detalle-cargos-card-header";

        const titulo = document.createElement("strong");
        titulo.textContent = contextoGrupo.cueanexo
          ? "📂 Cargos del Anexo " +
            obtenerTextoDetalleGrupo(contextoGrupo.anexo) +
            " · CUOF " +
            obtenerTextoDetalleGrupo(contextoGrupo.cuof)
          : "📂 Cargos del CUOF " +
            obtenerTextoDetalleGrupo(contextoGrupo.cuof);

        const contador = document.createElement("span");
        contador.className = "pof-grid-badge pof-grid-badge-modificacion";
        contador.textContent =
          cargos.length + (cargos.length === 1 ? " cargo" : " cargos");

        cabecera.appendChild(titulo);
        cabecera.appendChild(contador);

        const envoltorio = document.createElement("div");
        envoltorio.className = "pof-table-wrap pof-detalle-cargos-table-wrap";

        const tabla = document.createElement("table");
        tabla.className = "pof-table";

        const encabezado = document.createElement("thead");
        const filaEncabezado = document.createElement("tr");

        [
          "CEIC",
          "Cantidad",
          "Modificación de cantidad",
          "Cargo",
          "Unidad",
          "Puntos",
          "Total",
          "Observación",
          "Estado",
          "Acción",
        ].forEach(function (tituloColumna) {
          const th = document.createElement("th");
          th.textContent = tituloColumna;
          filaEncabezado.appendChild(th);
        });

        encabezado.appendChild(filaEncabezado);
        tabla.appendChild(encabezado);

        const cuerpo = document.createElement("tbody");

        cargos.forEach(function (cargo) {
          const fila = document.createElement("tr");

          fila.appendChild(crearCeldaDetalleGrupo(cargo.ceic));
          fila.appendChild(crearCeldaCantidadDetalleGrupo(cargo));
          fila.appendChild(crearCeldaModificacionCantidad(cargo));
          fila.appendChild(crearCeldaDetalleGrupo(cargo.cargo));
          fila.appendChild(crearCeldaDetalleGrupo(cargo.unidad_cantidad));
          fila.appendChild(crearCeldaDetalleGrupo(cargo.puntos_asignados));
          fila.appendChild(crearCeldaDetalleGrupo(cargo.total));
          fila.appendChild(crearCeldaObservacionDetalleGrupo(cargo));
          fila.appendChild(crearCeldaEstadoDetalleGrupo(cargo));
          fila.appendChild(crearCeldaAccionDetalleGrupo(cargo, contextoGrupo));

          cuerpo.appendChild(fila);
        });

        tabla.appendChild(cuerpo);
        envoltorio.appendChild(tabla);

        tarjeta.appendChild(cabecera);
        tarjeta.appendChild(envoltorio);

        return tarjeta;
      }

      function obtenerContenedorDetalleGrupo(button) {
        const targetId = button.dataset.target || "";
        return targetId ? document.getElementById(targetId) : null;
      }

      function obtenerFilaDetalleGrupo(contenedor) {
        return contenedor
          ? contenedor.closest("[data-detalle-grupo-row]")
          : null;
      }

      function mostrarContenedorDetalleGrupo(contenedor, visible) {
        const fila = obtenerFilaDetalleGrupo(contenedor);
        if (fila) {
          fila.hidden = !visible;
          fila.classList.toggle("pof-hidden", !visible);
        }
      }

      function crearEstadoDetalleGrupo(mensaje, tipo) {
        const estado = document.createElement("div");
        apiDetalle.showStatus(estado, tipo, mensaje);
        return estado;
      }

      function marcarBotonDetalleGrupo(button, cargando) {
        if (!button.dataset.labelDefault) {
          button.dataset.labelDefault =
            button.textContent.trim() || "Ver cargos";
        }
        button.disabled = !!cargando;
        button.setAttribute("aria-disabled", cargando ? "true" : "false");
        button.textContent = cargando
          ? "Cargando..."
          : button.dataset.labelDefault;
      }

      /**
       * Carga por AJAX un único grupo operativo ya visible en el detalle.
       *
       * - Usa el endpoint declarado por cada fila mediante `data-url`.
       * - No altera otros grupos ni precarga el resto de la pantalla.
       * - Deja el contenido cacheado en el contenedor para alternar sin refetch.
       */
      async function cargarDetalleGrupo(button) {
        const contenedor = obtenerContenedorDetalleGrupo(button);
        if (!contenedor) {
          return;
        }

        const urlBase = button.dataset.url || "";
        const cueanexo = button.dataset.cueanexo || "";
        const cuof = button.dataset.cuof || "";
        const localizacionId = button.dataset.localizacionId || "";
        const url = new URL(urlBase, window.location.origin);
        if (!localizacionId) {
          url.searchParams.set("cueanexo", cueanexo);
          url.searchParams.set("cuof", cuof);
        }

        limpiarContenedorDetalleGrupo(contenedor);
        contenedor.appendChild(crearEstadoDetalleGrupo("Cargando...", "info"));
        mostrarContenedorDetalleGrupo(contenedor, true);
        marcarBotonDetalleGrupo(button, true);

        try {
          const respuesta = await apiDetalle.requestJson(url.toString(), {
            method: "GET",
            credentials: "same-origin",
          });
          const cargos = Array.isArray(respuesta.cargos)
            ? respuesta.cargos
            : [];

          limpiarContenedorDetalleGrupo(contenedor);
          if (!respuesta.cantidad_cargos) {
            contenedor.appendChild(
              crearEstadoDetalleGrupo(
                "No hay cargos para este Anexo/CUOF.",
                "info",
              ),
            );
          } else {
            const contextoGrupo = {
              anexo:
                respuesta.anexo ||
                (cueanexo.length >= 2 ? cueanexo.slice(-2) : ""),
              cueanexo: respuesta.cueanexo || cueanexo,
              cuof: respuesta.cuof || cuof,
              localizacionId:
                respuesta.localizacion_id || localizacionId,
            };

            contenedor.appendChild(
              crearTablaDetalleGrupo(cargos, contextoGrupo),
            );
          }

          contenedor.dataset.loaded = "true";
          button.dataset.labelDefault = "👁️‍🗨️ Ocultar cargos";
          button.setAttribute("aria-expanded", "true");
        } catch (error) {
          limpiarContenedorDetalleGrupo(contenedor);
          contenedor.appendChild(
            crearEstadoDetalleGrupo(apiDetalle.formatError(error), "error"),
          );
          button.dataset.labelDefault = "👁️Ver cargos";
          button.setAttribute("aria-expanded", "false");
        } finally {
          marcarBotonDetalleGrupo(button, false);
        }
      }

      function alternarDetalleGrupo(button) {
        const contenedor = obtenerContenedorDetalleGrupo(button);
        const filaDetalleGrupo = obtenerFilaDetalleGrupo(contenedor);

        if (!contenedor || !filaDetalleGrupo) {
          return;
        }

        if (contenedor.dataset.loaded === "true") {
          const visible = filaDetalleGrupo.hidden;
          mostrarContenedorDetalleGrupo(contenedor, visible);
          button.dataset.labelDefault = visible
            ? "👁️‍🗨️ Ocultar cargos"
            : "👁️‍🗨️ Mostrar cargos";
          button.setAttribute("aria-expanded", visible ? "true" : "false");
          marcarBotonDetalleGrupo(button, false);
          return;
        }

        cargarDetalleGrupo(button);
      }

      /**
       * Abre automáticamente un grupo pedido por query string cuando existe.
       *
       * - Lee `cueanexo` y `cuof` desde la URL actual.
       * - Reutiliza la misma lógica de carga/toggle del botón del grupo.
       * - Si el grupo no existe, no rompe la pantalla ni dispara otras cargas.
       */
      function abrirGrupoDetalleDesdeQueryString() {
        const params = new URLSearchParams(window.location.search || "");

        let cueanexo = (params.get("cueanexo") || "").trim();
        let cuof = (params.get("cuof") || "").trim();
        let localizacionId = "";
        let esReaperturaTrasGestion = false;
        const esProyectoEspecial =
          params.get("cabecera_tipo") === "PROYECTO_ESPECIAL" ||
          Boolean(params.get("proyecto_especial_id"));

        if (esProyectoEspecial || !cueanexo || !cuof) {
          const grupoGuardado = obtenerGrupoParaReapertura();

          if (grupoGuardado) {
            esReaperturaTrasGestion = true;
            localizacionId = grupoGuardado.localizacionId || "";
            cueanexo = grupoGuardado.cueanexo || "";
            cuof = grupoGuardado.cuof || "";
          }
        }

        if (!localizacionId && (!cueanexo || !cuof)) {
          return;
        }

        const button = botonesDetalleGrupo.find(function (item) {
          if (localizacionId) {
            return (item.dataset.localizacionId || "") === localizacionId;
          }
          return (
            (item.dataset.cueanexo || "") === cueanexo &&
            (item.dataset.cuof || "") === cuof
          );
        });

        if (!button) {
          return;
        }

        if (!esReaperturaTrasGestion) {
          button.scrollIntoView({ behavior: "auto", block: "center" });
        }
        button.focus({ preventScroll: true });
        alternarDetalleGrupo(button);
      }

      botonesDetalleGrupo.forEach(function (button) {
        button.addEventListener("click", function () {
          alternarDetalleGrupo(button);
        });
      });

      document.addEventListener(
        "pof:cargo-gestion-actualizado",
        function (event) {
          const detalle = event.detail || {};
          const trigger = detalle.trigger || null;

          guardarGrupoParaReapertura(trigger);

          /*
           * Se refresca la página completa para mantener consistentes:
           * - cantidad del cargo;
           * - estado;
           * - total del cargo;
           * - total de cargos de la localización;
           * - total de cargos del grupo principal;
           * - total de puntos del grupo principal.
           */
          window.location.reload();
        },
      );

      abrirGrupoDetalleDesdeQueryString();
    }

    /**
     * Inicializa los modales Info CUE disponibles en el Detalle.
     *
     * - Abre el modal asociado al boton de cada card CUE normal.
     * - Cierra con boton, Escape o click sobre el fondo del modal.
     * - No lee ni modifica datos de cargos, filtros o AJAX.
     */
    function initDetalleReunidaInfoCue() {
        const botonesInfoCue = Array.from(document.querySelectorAll("[data-pof-cue-modal-open]"));
        const modalesInfoCue = Array.from(document.querySelectorAll("[data-pof-cue-modal]"));
        let botonActivoInfoCue = null;

        if (!botonesInfoCue.length || !modalesInfoCue.length) {
            return;
        }

        function obtenerModalInfoCue(boton) {
            const modalId = boton ? boton.dataset.pofCueModalOpen : "";
            return modalId ? document.getElementById(modalId) : null;
        }

        function cerrarModalInfoCue(modal) {
            if (!modal) {
                return;
            }
            modal.classList.add("pof-hidden");
            modal.setAttribute("aria-hidden", "true");
            if (botonActivoInfoCue) {
                botonActivoInfoCue.setAttribute("aria-expanded", "false");
                botonActivoInfoCue.focus({ preventScroll: true });
                botonActivoInfoCue = null;
            }
        }

        function abrirModalInfoCue(boton) {
            const modal = obtenerModalInfoCue(boton);
            if (!modal) {
                return;
            }
            botonActivoInfoCue = boton;
            modal.classList.remove("pof-hidden");
            modal.setAttribute("aria-hidden", "false");
            boton.setAttribute("aria-expanded", "true");

            const cerrar = modal.querySelector("[data-pof-cue-modal-close]");
            if (cerrar) {
                cerrar.focus({ preventScroll: true });
            }
        }

        botonesInfoCue.forEach(function (boton) {
            boton.addEventListener("click", function () {
                abrirModalInfoCue(boton);
            });
        });

        modalesInfoCue.forEach(function (modal) {
            modal.querySelectorAll("[data-pof-cue-modal-close]").forEach(function (botonCerrar) {
                botonCerrar.addEventListener("click", function () {
                    cerrarModalInfoCue(modal);
                });
            });

            modal.addEventListener("click", function (event) {
                if (event.target === modal) {
                    cerrarModalInfoCue(modal);
                }
            });
        });

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") {
                return;
            }
            const modalAbierto = modalesInfoCue.find(function (modal) {
                return !modal.classList.contains("pof-hidden");
            });
            if (modalAbierto) {
                cerrarModalInfoCue(modalAbierto);
            }
        });
    }

    initDetalleReunidaFiltros();
    initDetalleReunidaFiltrosDinamicos();
    initDetalleReunidaAjax();
    initDetalleReunidaInfoCue();
})();
