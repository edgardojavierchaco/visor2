(function () {
    "use strict";
    var app = document.getElementById("cefMetricasApp");
    if (!app || app.dataset.metricasReady === "1") return;
    app.dataset.metricasReady = "1";
    var config;
    try { config = JSON.parse(document.getElementById("cef-metricas-config").textContent); }
    catch (error) { return; }

    function byId(id) { return document.getElementById(id); }
    function node(tag, className, text) {
        var result = document.createElement(tag);
        if (className) result.className = className;
        if (text !== undefined) result.textContent = text;
        return result;
    }
    function icon(className) {
        var result = node("i", className);
        result.setAttribute("aria-hidden", "true");
        return result;
    }
    function button(text, action, className) {
        var result = node("button", className || "btn btn-outline-secondary btn-sm", text);
        result.type = "button";
        result.addEventListener("click", action);
        return result;
    }
    function normalized(value) {
        return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es");
    }
    function selected(select) {
        return Array.from(select.selectedOptions).map(function (option) { return option.value; });
    }
    function options(select, items, values) {
        var chosen = new Set((values || []).map(String));
        select.replaceChildren();
        items.forEach(function (item) {
            var option = node("option", "", item.label);
            option.value = item.key || item.value;
            option.selected = chosen.has(String(option.value));
            select.appendChild(option);
        });
    }

    var form = byId("cefMetricasForm");
    var cyclesSelect = byId("cefMetricasCiclos");
    var cefsSelect = byId("cefMetricasCefs");
    var filtersRoot = byId("cefMetricasFiltros");
    var filtersPanel = byId("cefMetricasFiltrosPanel");
    var columnsPanel = byId("cefConsultasColumnasPanel");
    var filtersToggle = byId("cefConsultasAbrirFiltros");
    var columnsToggle = byId("cefConsultasAbrirColumnas");
    var resultsRoot = byId("cefMetricasResultado");
    var tableRoot = byId("cefMetricasTabla");
    var statusRoot = byId("cefMetricasEstado");
    var searchInput = byId("cefConsultasBuscar");
    var searchField = byId("cefConsultasBuscarCampoSelect");
    var searchClear = byId("cefConsultasBuscarLimpiar");
    var filterDialog = byId("cefConsultaFiltroDialog");
    var filterContent = byId("cefConsultaFiltroContenido");
    var filterTrigger = null;
    var filterInertNodes = [];
    var questionSelect = byId("cefConsultasPregunta");
    var exportButton = byId("cefMetricasExportar");
    var exportWrap = byId("cefMetricasExportarWrap");
    var exportMenu = byId("cefMetricasExportarMenu");
    var exportOptionList = byId("cefMetricasExportarMenu").querySelectorAll("[data-cef-export-option]");
    var chartRoot = byId("cefMetricasChart");
    var chartBadge = byId("cefMetricasChartBadge");
    var chartPanel = byId("cefMetricasGraficoPanel");
    var detailModal = byId("cefConsultasDetalleModal");
    var detailModalTrigger = null;
    var entity = (config.entidades || [])[0];
    var mode = "listados";
    var question = null;
    var states = {};
    var state;
    var rendering = false;
    var dirty = true;
    var timer = null;
    var loadingTimer = null;
    var controller = null;
    var requestVersion = 0;
    var lastResult = null;
    var lastParams = null;
    var exporting = false;
    var colors = ["#2563eb", "#0f766e", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#4d7c0f", "#be185d"];
    var chartLabels = {auto: "Automática", kpi: "Total", bar: "Barras", grouped_bar: "Barras agrupadas", stacked_bar: "Barras apiladas", line: "Línea", doughnut: "Dona"};

    function definitions() { return mode === "listados" ? entity.filters : (question ? question.filters : []); }
    function filterParamKeys(filter) {
        var base = "f_" + filter.key;
        return filter.type === "multi" ? [base] : [base + "_desde", base + "_hasta"];
    }
    function cloneFilters(filters) {
        var copy = {};
        Object.keys(filters || {}).forEach(function (key) { copy[key] = (filters[key] || []).slice(); });
        return copy;
    }
    function filterSemanticKey(filter) {
        var key = filter.key;
        if (entity.key === "alumnos") {
            if (key === "fecha") return "fecha_inscripcion";
            if (key === "edad") return normalized(filter.label).includes("inscrib") ? "edad_inscripcion" : "edad_actual";
        }
        if (entity.key === "profesores" && key === "fecha") return "fecha_asignacion";
        if (entity.key === "inventario" && key === "estado") return "estado_material";
        return key;
    }
    function filterValuesForDefinition(filters, filter) {
        var values = [];
        filterParamKeys(filter).forEach(function (param) {
            values = values.concat((filters[param] || []).slice());
        });
        return values;
    }
    function selectedCefItems() {
        var values = selected(cefsSelect);
        if (!values.length) return (config.cefs || []).slice();
        var chosen = new Set(values.map(String));
        return (config.cefs || []).filter(function (item) { return chosen.has(String(item.value)); });
    }
    function allFilterChoices(key) {
        var result = new Map();
        function collect(filters) {
            (filters || []).forEach(function (filter) {
                if (filter.key !== key) return;
                (filter.choices || []).forEach(function (choice) {
                    result.set(String(choice.value), choice);
                });
            });
        }
        (config.entidades || []).forEach(function (item) { collect(item.filters); });
        (config.preguntas || []).forEach(function (item) { collect(item.filters); });
        return Array.from(result.values());
    }
    function contextualChoices(filter) {
        var choices = (filter.choices || []).slice();
        if (filter.key === "grupo") {
            var ciclos = new Set(selected(cyclesSelect).map(String));
            var cefs = new Set(selected(cefsSelect).map(String));
            return choices.filter(function (choice) {
                var cicloOk = !choice.ciclo || ciclos.has(String(choice.ciclo));
                var cefOk = !choice.cef || !cefs.size || cefs.has(String(choice.cef));
                return cicloOk && cefOk;
            });
        }
        if (["region", "departamento", "localidad"].includes(filter.key)) {
            var allowed = new Set(selectedCefItems().map(function (item) { return String(item[filter.key] || ""); }));
            return choices.filter(function (choice) { return allowed.has(String(choice.value)); });
        }
        return choices;
    }
    function allowedContextValues(key) {
        if (key === "grupo") {
            var ciclos = new Set(selected(cyclesSelect).map(String));
            var cefs = new Set(selected(cefsSelect).map(String));
            return new Set(allFilterChoices("grupo").filter(function (choice) {
                var cicloOk = !choice.ciclo || ciclos.has(String(choice.ciclo));
                var cefOk = !choice.cef || !cefs.size || cefs.has(String(choice.cef));
                return cicloOk && cefOk;
            }).map(function (choice) { return String(choice.value); }));
        }
        if (["region", "departamento", "localidad"].includes(key)) {
            return new Set(selectedCefItems().map(function (item) { return String(item[key] || ""); }));
        }
        return null;
    }
    function pruneStateFilter(filters, param, allowed) {
        if (!filters || !filters[param] || !allowed) return;
        var values = filters[param].filter(function (value) { return allowed.has(String(value)); });
        if (values.length) filters[param] = values;
        else delete filters[param];
    }
    function reconcileContextFilters() {
        var allowedGroups = allowedContextValues("grupo");
        var allowedRegion = allowedContextValues("region");
        var allowedDepartamento = allowedContextValues("departamento");
        var allowedLocalidad = allowedContextValues("localidad");
        Object.keys(states).forEach(function (key) {
            var filters = states[key] && states[key].filters;
            pruneStateFilter(filters, "f_grupo", allowedGroups);
            pruneStateFilter(filters, "f_region", allowedRegion);
            pruneStateFilter(filters, "f_departamento", allowedDepartamento);
            pruneStateFilter(filters, "f_localidad", allowedLocalidad);
        });
        closeFilterDialog(false);
        if (state) renderActiveFilters();
    }
    function syncCompatibleFilters(sourceFilters, sourceDefinitions, targetDefinitions, targetFilters) {
        var result = cloneFilters(targetFilters || {});
        var sourceBySemanticKey = {};
        (sourceDefinitions || []).forEach(function (filter) { sourceBySemanticKey[filterSemanticKey(filter)] = filter; });
        (targetDefinitions || []).forEach(function (target) {
            var source = sourceBySemanticKey[filterSemanticKey(target)];
            if (!source || source.type !== target.type) return;
            var values = filterValuesForDefinition(sourceFilters, source);
            if (target.type === "multi" && Array.isArray(target.choices)) {
                var allowed = new Set(contextualChoices(target).map(function (choice) { return String(choice.value); }));
                values = values.filter(function (value) { return allowed.has(String(value)); });
            }
            var targetParams = filterParamKeys(target);
            if (target.type === "multi") {
                if (values.length) result[targetParams[0]] = values;
                else delete result[targetParams[0]];
                return;
            }
            var sourceParams = filterParamKeys(source);
            targetParams.forEach(function (targetParam, index) {
                var sourceValues = (sourceFilters[sourceParams[index]] || []).slice();
                if (sourceValues.length) result[targetParam] = sourceValues;
                else delete result[targetParam];
            });
        });
        return result;
    }
    function storageKey() { return "cef.consultas.columnas.v1." + entity.key; }
    function loadColumns() {
        var defaults = entity.columns.filter(function (col) { return col.default; }).map(function (col) { return col.key; });
        try {
            var saved = JSON.parse(localStorage.getItem(storageKey()));
            if (Array.isArray(saved)) {
                var valid = saved.filter(function (key) { return entity.columns.some(function (col) { return col.key === key; }); });
                if (!saved.length || valid.length) return new Set(valid);
            }
        } catch (error) { /* La consulta sigue disponible sin almacenamiento local. */ }
        return new Set(defaults);
    }
    function saveColumns() {
        try { localStorage.setItem(storageKey(), JSON.stringify(Array.from(state.columns))); }
        catch (error) { /* Preferencia sólo durante esta sesión. */ }
    }
    function destroySelects(root) {
        if (window.CEFSelects && window.CEFSelects.destroy) window.CEFSelects.destroy(root);
    }
    function enhance(root) {
        function bind() {
            if (!window.jQuery) return;
            window.jQuery(root).find("select[multiple]").off("change.cefConsultas").on("change.cefConsultas", function () {
                changed(this);
            });
        }
        root.querySelectorAll("select[multiple]").forEach(function (select) {
            select.dataset.closeOnSelect = "false";
        });
        if (window.CEFSelects && window.CEFSelects.init) window.CEFSelects.init(root, bind);
        else if (window.initCefSelects) { window.initCefSelects(root, bind); bind(); }
        else bind();
    }
    function setPanel(panel, toggle, open) {
        panel.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
    }
    function closePanels() {
        setPanel(filtersPanel, filtersToggle, false);
        setPanel(columnsPanel, columnsToggle, false);
    }
    function setStatus(message, error) {
        statusRoot.hidden = !message;
        statusRoot.textContent = message || "";
        statusRoot.classList.toggle("is-error", !!error);
    }
    function closeExportMenu() {
        exportMenu.hidden = true;
        exportButton.setAttribute("aria-expanded", "false");
    }

    function positionExportMenu() {
        if (exportMenu.hidden) return;

        var appRect = app.getBoundingClientRect();
        var wrapRect = exportWrap.getBoundingClientRect();
        var buttonRect = exportButton.getBoundingClientRect();
        var limiteIzquierdo = Math.max(8, appRect.left + 8);
        var limiteDerecho = Math.min(window.innerWidth - 8, appRect.right - 8);
        var anchoDisponible = Math.max(0, limiteDerecho - limiteIzquierdo);
        var anchoDeseado = 304;
        var ancho = Math.min(anchoDeseado, anchoDisponible || anchoDeseado);

        exportMenu.style.width = ancho + "px";

        var izquierda = Math.min(
            buttonRect.left,
            limiteDerecho - ancho
        );
        izquierda = Math.max(limiteIzquierdo, izquierda);

        exportMenu.style.left = (izquierda - wrapRect.left) + "px";
        exportMenu.style.right = "auto";
    }

    function exportDefinitions(targetMode) {
        return targetMode === "listados" ? (entity.filters || []) : (question ? question.filters || [] : []);
    }

    function exportStateFor(targetMode) {
        var key = entity.key + "/" + targetMode + (
            targetMode === "estadisticas" && question ? "/" + question.key : ""
        );
        var stored = states[key] || {};
        var targetFilters = targetMode === mode
            ? Object.keys(state && state.filters || {}).reduce(function (copy, filterKey) {
                copy[filterKey] = (state.filters[filterKey] || []).slice();
                return copy;
            }, {})
            : syncCompatibleFilters(
                state ? state.filters : {},
                definitions(),
                exportDefinitions(targetMode),
                {}
            );

        var sameMode = targetMode === mode;
        var activeState = sameMode && state ? state : stored;
        return {
            filters: targetFilters,
            search: activeState.search || "",
            searchField: activeState.searchField || "",
            page: 1,
            size: activeState.size || 25,
            columns: activeState.columns instanceof Set
                ? new Set(activeState.columns)
                : loadColumns()
        };
    }

    function buildParamsFor(targetMode) {
        var targetState = exportStateFor(targetMode);
        var params = new URLSearchParams();
        params.set("modo", targetMode);
        params.set("entidad", entity.key);
        params.set("pagina", targetState.page || 1);
        params.set("tamano", targetState.size || 25);
        selected(cyclesSelect).forEach(function (value) { params.append("ciclos", value); });
        selected(cefsSelect).forEach(function (value) { params.append("cefs", value); });

        if (targetMode === "estadisticas") {
            if (!question) throw new Error("No hay una estadística disponible para esta categoría.");
            params.set("pregunta", question.key);
        } else {
            if (String(targetState.search || "").trim()) params.set("buscar", String(targetState.search).trim());
            if (targetState.searchField) params.set("buscar_campo", targetState.searchField);
            (targetState.columns || new Set()).forEach(function (key) { params.append("columnas", key); });
        }

        Object.keys(targetState.filters || {}).forEach(function (key) {
            (targetState.filters[key] || []).forEach(function (value) { params.append(key, value); });
        });
        return params;
    }

    function syncExport() {
        var disabled = dirty || !lastParams || exporting;
        var listState = exportStateFor("listados");
        var sinColumnas = !listState.columns || listState.columns.size === 0;
        var sinEstadistica = !question;

        exportButton.disabled = disabled;
        exportButton.setAttribute("aria-disabled", String(disabled));
        exportButton.removeAttribute("title");

        exportOptionList.forEach(function (option) {
            var key = option.dataset.cefExportOption;
            option.hidden = false;
            var optionDisabled = disabled;
            if ((key === "excel-listado" || key === "excel-completo") && sinColumnas) optionDisabled = true;
            if ((key === "excel-completo" || key === "excel-estadistica" || key === "png") && sinEstadistica) optionDisabled = true;
            option.disabled = optionDisabled;
            option.setAttribute("aria-disabled", String(optionDisabled));
            if (sinColumnas && (key === "excel-listado" || key === "excel-completo")) {
                option.title = "Seleccioná al menos una columna del listado.";
            } else {
                option.removeAttribute("title");
            }
        });

        if (disabled) closeExportMenu();
    }

    function buildExportUrl(params, includeChart, includeStatistics) {
        var clean = new URLSearchParams(params || "");
        clean.delete("pagina");
        clean.delete("incluir_grafico");
        clean.delete("incluir_estadistica");
        if (includeChart) clean.set("incluir_grafico", "1");
        if (includeStatistics) clean.set("incluir_estadistica", "1");
        return app.dataset.exportarUrl + "?" + clean.toString();
    }

    function fetchStatisticsForExport() {
        var params = buildParamsFor("estadisticas");
        if (
            mode === "estadisticas" && !dirty && lastResult &&
            String(lastParams && lastParams.get("pregunta") || "") === String(question && question.key || "")
        ) {
            renderChart(lastResult);
            return Promise.resolve({result: lastResult, params: params});
        }

        return fetch(app.dataset.consultaUrl + "?" + params.toString(), {
            credentials: "same-origin",
            cache: "no-store",
            headers: {"Accept": "application/json"}
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (payload) {
                if (!response.ok || !payload.ok) {
                    throw new Error(payload.message || "No se pudo preparar la estadística para exportar.");
                }
                renderChart(payload);
                if (!chartRoot.querySelector("svg")) {
                    throw new Error(payload.empty_message || "La estadística actual no tiene un gráfico para exportar.");
                }
                return {result: payload, params: params};
            });
        });
    }

    function fetchExcelResponse(url, body) {
        var options = {credentials: "same-origin", cache: "no-store"};
        if (body) {
            options.method = "POST";
            options.body = body;
            var csrf = form.querySelector('[name="csrfmiddlewaretoken"]');
            if (csrf && csrf.value) options.headers = {"X-CSRFToken": csrf.value};
        }
        return fetch(url, options).then(function (response) {
            if (!response.ok || response.redirected) {
                return response.text().then(function (message) {
                    throw new Error(message || "No se pudo exportar. Revisá los filtros o recargá tu sesión.");
                });
            }
            if (!(response.headers.get("Content-Type") || "").includes("spreadsheetml")) {
                throw new Error("El servidor no devolvió un archivo Excel.");
            }
            return response.blob();
        });
    }

    function exportExcelList() {
        if (dirty || !lastParams || exporting) return;
        exporting = true;
        closeExportMenu();
        syncExport();
        setStatus("Preparando Excel del listado…");
        var params = buildParamsFor("listados");
        fetchExcelResponse(buildExportUrl(params, false, false))
            .then(function (blob) {
                downloadBlob(blob, "Consulta_CEF_" + entity.label.replace(/\s+/g, "_") + ".xlsx");
                if (!dirty) setStatus("Excel del listado descargado.");
            })
            .catch(function (error) { setStatus(error.message, true); })
            .finally(function () {
                exporting = false;
                syncExport();
            });
    }

    function exportExcelStatistics() {
        if (dirty || !lastParams || exporting || !question) return;
        exporting = true;
        closeExportMenu();
        syncExport();
        setStatus("Preparando Excel de estadística + gráfico…");

        fetchStatisticsForExport()
            .then(function (stat) {
                return currentChartPngBlob(stat.result, false).then(function (chartBlob) {
                    var body = new FormData();
                    body.append("grafico_png", chartBlob, "grafico.png");
                    return fetchExcelResponse(
                        buildExportUrl(stat.params, true, false),
                        body
                    );
                });
            })
            .then(function (blob) {
                downloadBlob(
                    blob,
                    "Consulta_CEF_Estadistica_" + entity.label.replace(/\s+/g, "_") + ".xlsx"
                );
                if (!dirty) setStatus("Excel de estadística + gráfico descargado.");
            })
            .catch(function (error) { setStatus(error.message, true); })
            .finally(function () {
                exporting = false;
                syncExport();
            });
    }

    function exportExcelComplete() {
        if (dirty || !lastParams || exporting) return;
        exporting = true;
        closeExportMenu();
        syncExport();
        setStatus("Preparando Excel completo: listado + estadística + gráfico…");

        var listParams = buildParamsFor("listados");
        fetchStatisticsForExport()
            .then(function (stat) {
                return currentChartPngBlob(stat.result, false).then(function (chartBlob) {
                    var body = new FormData();
                    body.append("grafico_png", chartBlob, "grafico.png");
                    body.append("estadistica_params", stat.params.toString());
                    return fetchExcelResponse(
                        buildExportUrl(listParams, true, true),
                        body
                    );
                });
            })
            .then(function (blob) {
                downloadBlob(
                    blob,
                    "Consulta_CEF_Completa_" + entity.label.replace(/\s+/g, "_") + ".xlsx"
                );
                if (!dirty) setStatus("Excel completo descargado.");
            })
            .catch(function (error) { setStatus(error.message, true); })
            .finally(function () {
                exporting = false;
                syncExport();
            });
    }
    function clearResultLoading() {
        clearTimeout(loadingTimer);
        loadingTimer = null;
        resultsRoot.classList.remove("is-updating");
    }
    function invalidate() {
        dirty = true;
        requestVersion += 1;
        if (controller) controller.abort();
        syncExport();
        clearResultLoading();
        resultsRoot.setAttribute("aria-busy", "true");
    }

    function renderEntities() {
        var root = byId("cefMetricasTipos");
        root.replaceChildren();
        config.entidades.forEach(function (item) {
            var card = button("", function () {
                if (entity.key === item.key) return;
                entity = item;
                question = null;
                changeWorkspace();
            }, "cef-metricas-query-card");
            card.dataset.entidad = item.key;
            card.setAttribute("aria-pressed", String(item.key === entity.key));
            card.setAttribute("aria-controls", "cefConsultasApartado");
            card.classList.toggle("is-selected", item.key === entity.key);
            var wrap = node("span", "cef-metricas-query-card-icon");
            wrap.appendChild(icon(item.icon));
            card.append(wrap, node("strong", "", item.label), icon("fa-solid fa-check cef-metricas-query-check"));
            root.appendChild(card);
        });
    }
    function changeWorkspace(previousContext) {
        clearTimeout(timer);
        closeOpenHelp(false);
        closeDetailModal(false);
        closeFilterDialog(false);
        invalidate();
        rendering = true;
        var questions = config.preguntas.filter(function (item) { return item.entidad === entity.key; });
        if (!question || question.entidad !== entity.key) question = questions[0] || null;
        options(questionSelect, questions, question ? [question.key] : []);
        var key = entity.key + "/" + mode + (mode === "estadisticas" && question ? "/" + question.key : "");
        if (!states[key]) states[key] = {filters: {}, search: "", searchField: "", page: 1, size: 25, columns: loadColumns()};
        state = states[key];
        if (previousContext && previousContext.entityKey === entity.key) {
            state.filters = syncCompatibleFilters(
                previousContext.filters,
                previousContext.definitions,
                definitions(),
                state.filters
            );
        }
        byId("cefConsultasEntidadTitulo").textContent = entity.label;
        byId("cefConsultasPreguntaCampo").hidden = mode !== "estadisticas";
        byId("cefConsultasBuscarCampo").hidden = mode !== "listados";
        columnsToggle.hidden = mode !== "listados";
        searchInput.value = state.search;
        options(searchField, [{value: "", label: "Todos"}].concat(entity.search_fields || []), [state.searchField || ""]);
        syncSearch();
        byId("cefConsultasTamano").value = state.size;
        byId("cefConsultasModos").querySelectorAll("button").forEach(function (item) {
            item.classList.toggle("is-selected", item.dataset.modo === mode);
            item.setAttribute("aria-pressed", String(item.dataset.modo === mode));
        });
        byId("cefMetricasTipos").querySelectorAll("button").forEach(function (item) {
            item.classList.toggle("is-selected", item.dataset.entidad === entity.key);
            item.setAttribute("aria-pressed", String(item.dataset.entidad === entity.key));
        });
        closePanels();
        byId("cefConsultasBuscarFiltro").value = "";
        byId("cefConsultasBuscarColumna").value = "";
        resultsRoot.hidden = true;
        lastResult = null;
        lastParams = null;
        renderFilters();
        renderColumns();
        renderActiveFilters();
        rendering = false;
        schedule(0, false);
    }
    function renderFilters() {
        filtersRoot.replaceChildren();
        definitions().forEach(function (filter) {
            var control = button(filter.label, function () { openFilterDialog(filter, control); }, "cef-filter-btn-field");
            var item = node("div", "col");
            item.dataset.optionText = filter.label;
            control.setAttribute("aria-haspopup", "dialog");
            item.appendChild(control);
            filtersRoot.appendChild(item);
        });
        filterOptions(byId("cefConsultasBuscarFiltro"), filtersRoot, byId("cefConsultasFiltrosVacios"));
    }
    function openFilterDialog(filter, trigger) {
        destroySelects(filterContent);
        filterContent.replaceChildren();
        filterTrigger = trigger;
        var shell = filterContent;
        var id = "cefConsultaFiltro-" + filter.key;
        var label = node("label", "", filter.label);
        label.htmlFor = filter.type === "multi" ? id : id + "-desde";
        shell.appendChild(label);
        if (filter.type === "multi") {
            var select = node("select");
            select.multiple = true;
            select.id = id;
            select.hidden = true;
            select.dataset.filterParam = "f_" + filter.key;
            options(select, contextualChoices(filter), state.filters[select.dataset.filterParam] || []);
            shell.appendChild(select);
            label.textContent = "Opciones";
            label.removeAttribute("for");
            label.id = id + "-label";
            var search = node("input", "form-control form-control-sm cef-filter-options-search");
            search.type = "search";
            search.placeholder = "Buscar opción...";
            search.setAttribute("aria-label", "Buscar opción de " + filter.label);
            var checklist = node("div", "cef-filter-checklist");
            checklist.setAttribute("role", "group");
            checklist.setAttribute("aria-labelledby", label.id);
            Array.from(select.options).forEach(function (option) {
                var item = node("label", "cef-filter-check");
                item.dataset.optionText = option.textContent;
                var check = node("input", "form-check-input");
                check.type = "checkbox";
                check.checked = option.selected;
                check.addEventListener("change", function () { option.selected = check.checked; });
                item.append(check, node("span", "", option.textContent));
                checklist.appendChild(item);
            });
            var empty = node("p", "cef-consultas-muted", "No hay opciones que coincidan.");
            empty.hidden = true;
            search.addEventListener("input", function () { filterOptions(search, checklist, empty); });
            shell.append(search, checklist, empty);
        } else {
            var range = node("div", "cef-consultas-range");
            ["desde", "hasta"].forEach(function (side) {
                var input = node("input", "form-control form-control-sm");
                input.type = filter.type === "date_range" ? "date" : "number";
                input.id = id + "-" + side;
                input.setAttribute("aria-label", filter.label + " " + side);
                input.placeholder = side === "desde" ? "Desde" : "Hasta";
                input.dataset.filterParam = "f_" + filter.key + "_" + side;
                if (filter.min !== undefined) input.min = filter.min;
                if (filter.max !== undefined) input.max = filter.max;
                if (input.type === "number") input.step = "1";
                input.value = (state.filters[input.dataset.filterParam] || [""])[0];
                var sideLabel = node("label", "cef-range-side", side === "desde" ? "Desde" : "Hasta");
                sideLabel.appendChild(input);
                range.appendChild(sideLabel);
            });
            shell.appendChild(range);
        }

        byId("cefConsultaFiltroTitulo").textContent = "Agregar filtro: " + filter.label;
        byId("cefConsultaFiltroAyuda").textContent = filter.type === "multi"
            ? "Si no seleccionás ninguna opción, se incluyen todos los valores. Podés elegir una o varias opciones."
            : "Podés indicar sólo Desde, sólo Hasta o ambos límites. Si dejás ambos vacíos, este filtro no restringe la consulta.";
        closeOpenHelp(false);
        filterDialog.hidden = false;
        document.body.classList.add("cef-filter-dialog-open");
        filterInertNodes = Array.from(app.children).filter(function (child) { return child !== filterDialog && !child.inert; });
        filterInertNodes.forEach(function (child) { child.inert = true; });
        byId("cefConsultaFiltroX").focus();
    }
    function closeFilterDialog(restoreFocus) {
        if (!filterDialog || filterDialog.hidden) return;
        closeOpenHelp(false);
        destroySelects(filterContent);
        filterDialog.hidden = true;
        document.body.classList.remove("cef-filter-dialog-open");
        filterInertNodes.forEach(function (child) { child.inert = false; });
        filterInertNodes = [];
        if (restoreFocus !== false && filterTrigger && filterTrigger.isConnected) filterTrigger.focus();
        filterTrigger = null;
    }
    function syncSearch() {
        var selectedOption = searchField.options[searchField.selectedIndex];
        var label = selectedOption ? selectedOption.textContent : "Todos";
        searchField.title = label;
        searchInput.placeholder = searchField.value ? "Buscar en " + label + "..." : "Buscar en todos los resultados...";
        searchClear.hidden = !searchInput.value;
        renderActiveFilters();
    }
    function updateSearch(delay) {
        state.search = searchInput.value;
        syncSearch();
        schedule(delay);
    }
    function syncColumns() {
        byId("cefConsultasColumnasContador").textContent = "Mostrando " + state.columns.size + " de " + entity.columns.length + " columnas";
        saveColumns();
        if (lastResult && !dirty) renderTable(lastResult.table);
        syncExport();
    }
    function filterOptions(input, root, empty) {
        var text = normalized(input.value.trim());
        var visible = 0;
        root.querySelectorAll("[data-option-text]").forEach(function (item) {
            item.hidden = !normalized(item.dataset.optionText).includes(text);
            if (!item.hidden) visible += 1;
        });
        empty.hidden = visible > 0;
        var clear = app.querySelector('[data-cef-panel-clear="' + input.id + '"]');
        if (clear) clear.disabled = !input.value;
    }
    function renderColumns() {
        var root = byId("cefConsultasColumnas");
        root.replaceChildren();
        entity.columns.forEach(function (column) {
            var item = node("div", "col");
            item.dataset.optionText = column.label;
            var check = node("div", "form-check");
            var label = node("label", "form-check-label small", column.label);
            var input = node("input", "form-check-input");
            input.type = "checkbox";
            input.id = "cefConsultaColumna-" + column.key;
            label.htmlFor = input.id;
            input.checked = state.columns.has(column.key);
            input.addEventListener("change", function () {
                if (input.checked) state.columns.add(column.key); else state.columns.delete(column.key);
                syncColumns();
            });
            check.append(input, label);
            check.addEventListener("click", function (event) {
                if (event.target.closest("input, label")) return;
                input.click();
            });
            item.appendChild(check);
            root.appendChild(item);
        });
        filterOptions(byId("cefConsultasBuscarColumna"), root, byId("cefConsultasColumnasVacias"));
        syncColumns();
    }
    function readFilters() {
        var result = Object.assign({}, state.filters);
        filterContent.querySelectorAll("[data-filter-param]").forEach(function (control) {
            var values = control.tagName === "SELECT" ? selected(control) : (control.value ? [control.value] : []);
            if (values.length) result[control.dataset.filterParam] = values;
            else delete result[control.dataset.filterParam];
        });
        state.filters = result;
    }
    function renderActiveFilters() {
        var root = byId("cefMetricasFiltrosResumen");
        root.replaceChildren();
        if (mode === "listados" && state.search.trim()) {
            var selectedOption = searchField.options[searchField.selectedIndex];
            var fieldLabel = selectedOption ? selectedOption.textContent : "Todos";
            var searchLabel = "Búsqueda rápida en " + fieldLabel + ": " + state.search.trim();
            var searchChip = node("span", "cef-consultas-filter-chip");
            searchChip.id = "cefConsultasBusquedaBadge";
            var searchRemove = button("", function () { searchClear.click(); }, "cef-consultas-filter-chip-remove");
            searchRemove.appendChild(icon("fa-solid fa-xmark"));
            searchRemove.setAttribute("aria-label", "Quitar " + searchLabel);
            searchRemove.title = "Quitar";
            searchChip.append(icon("fa-solid fa-magnifying-glass"), node("span", "cef-consultas-filter-chip-text", searchLabel), searchRemove);
            root.appendChild(searchChip);
        }
        var count = 0;
        definitions().forEach(function (filter) {
            var keys = filter.type === "multi" ? ["f_" + filter.key] : ["f_" + filter.key + "_desde", "f_" + filter.key + "_hasta"];
            var labels = [];
            keys.forEach(function (key) {
                var values = state.filters[key] || [];
                values.forEach(function (value) {
                    var choice = (filter.choices || []).find(function (item) { return String(item.value) === value; });
                    labels.push(choice ? choice.label : (key.endsWith("_hasta") ? "hasta " : "desde ") + value);
                });
            });
            if (!labels.length) return;
            count += 1;
            var chip = node("span", "cef-consultas-filter-chip");
            var removeChip = button("", function () {
                keys.forEach(function (key) { delete state.filters[key]; });
                renderFilters();
                renderActiveFilters();
                schedule(0);
            }, "cef-consultas-filter-chip-remove");
            removeChip.appendChild(icon("fa-solid fa-xmark"));
            removeChip.setAttribute("aria-label", "Quitar filtro " + filter.label + ": " + labels.join(", "));
            removeChip.title = "Quitar";
            chip.append(
                icon("fa-solid fa-filter"),
                node("span", "cef-consultas-filter-chip-text", filter.label + ": " + labels.join(", ")),
                removeChip
            );
            root.appendChild(chip);
        });
        byId("cefMetricasFiltrosCount").textContent = count ? "(" + count + ")" : "";
    }
    function changed(control) {
        if (rendering || !state || filterContent.contains(control)) return;
        if (control === cyclesSelect || control === cefsSelect) {
            reconcileContextFilters();
            schedule(180);
            return;
        }
    }
    function buildParams() {
        var params = new URLSearchParams();
        params.set("modo", mode);
        params.set("entidad", entity.key);
        params.set("pagina", state.page);
        params.set("tamano", state.size);
        selected(cyclesSelect).forEach(function (value) { params.append("ciclos", value); });
        selected(cefsSelect).forEach(function (value) { params.append("cefs", value); });
        if (mode === "estadisticas") params.set("pregunta", question.key);
        else {
            if (state.search.trim()) params.set("buscar", state.search.trim());
            if (state.searchField) params.set("buscar_campo", state.searchField);
        }
        Object.keys(state.filters).forEach(function (key) {
            state.filters[key].forEach(function (value) { params.append(key, value); });
        });
        return params;
    }
    function schedule(delay, resetPage) {
        if (rendering) return;
        if (resetPage !== false) state.page = 1;
        clearTimeout(timer);
        invalidate();
        timer = setTimeout(requestResults, delay === undefined ? 200 : delay);
    }
    function requestResults() {
        if (!selected(cyclesSelect).length || !config.cefs.length) {
            resultsRoot.hidden = true;
            resultsRoot.setAttribute("aria-busy", "false");
            setStatus(!config.cefs.length ? "No hay CEF disponibles para tu usuario." : "Elegí al menos un ciclo para consultar.");
            return;
        }
        if (!form.reportValidity()) {
            resultsRoot.hidden = true;
            resultsRoot.setAttribute("aria-busy", "false");
            setStatus("Revisá los valores de los filtros.", true);
            return;
        }
        if (mode === "estadisticas" && !question) {
            resultsRoot.setAttribute("aria-busy", "false");
            setStatus("No hay preguntas estadísticas disponibles para esta categoría.");
            return;
        }
        var params = buildParams();
        var version = requestVersion;
        controller = new AbortController();
        // Como en Padrón, conservar la tabla durante el debounce y las respuestas rápidas.
        setStatus(resultsRoot.hidden ? "Cargando resultados…" : "");
        loadingTimer = setTimeout(function () {
            if (version === requestVersion && dirty && app.isConnected) resultsRoot.classList.add("is-updating");
        }, 180);
        fetch(app.dataset.consultaUrl + "?" + params.toString(), {
            signal: controller.signal,
            headers: {"Accept": "application/json"},
            credentials: "same-origin",
            cache: "no-store"
        })
            .then(function (response) {
                if (response.status === 403) throw new Error("No tenés permisos para consultar los CEF o ciclos seleccionados.");
                if (response.redirected) throw new Error("Tu sesión venció. Recargá la página para ingresar nuevamente.");
                return response.json().then(function (payload) {
                    if (!response.ok || payload.ok === false) throw new Error(payload.message || "No se pudo cargar la consulta.");
                    return payload;
                });
            }).then(function (payload) {
                if (version !== requestVersion || !app.isConnected) return;
                // Padrón restaura la opacidad antes de mostrar la respuesta nueva.
                clearResultLoading();
                lastResult = payload;
                lastParams = params;
                dirty = false;
                state.page = payload.table.pagination ? payload.table.pagination.page : 1;
                renderResult(payload);
                setStatus("");
                syncExport();
            }).catch(function (error) {
                if (error.name === "AbortError" || version !== requestVersion) return;
                resultsRoot.hidden = true;
                setStatus(error.message === "Failed to fetch" ? "No se pudo conectar. Intentá nuevamente." : error.message, true);
            }).finally(function () {
                if (version !== requestVersion) return;
                clearResultLoading();
                resultsRoot.setAttribute("aria-busy", "false");
            });
    }

    function basicTable(columns, rows, rowAction) {
        var scroll = node("div", "cef-table-wrap cef-consultas-table-scroll");
        scroll.tabIndex = 0;
        scroll.setAttribute("role", "region");
        scroll.setAttribute("aria-label", "Tabla de resultados");
        var table = node("table", "cef-dt cef-consultas-table");
        var head = node("thead");
        var tr = node("tr");
        if (rowAction) {
            var actionHead = node("th", "is-action", "Detalle");
            actionHead.scope = "col";
            tr.appendChild(actionHead);
        }
        columns.forEach(function (column) {
            var th = node("th", column.type === "number" ? "is-number" : "", column.label);
            th.scope = "col";
            tr.appendChild(th);
        });
        head.appendChild(tr);
        table.appendChild(head);
        var body = node("tbody");
        rows.forEach(function (row) {
            var line = node("tr");
            if (rowAction) {
                var actionCell = node("td", "is-action");
                var actionButton = button("", function () { rowAction(row, actionButton); }, "btn btn-outline-primary btn-sm cef-consultas-row-action");
                actionButton.title = "Ver detalle";
                actionButton.setAttribute("aria-label", "Ver detalle de " + (row.persona || "la persona"));
                actionButton.appendChild(icon("fa-solid fa-eye"));
                actionCell.appendChild(actionButton);
                line.appendChild(actionCell);
            }
            columns.forEach(function (column) {
                var value = row[column.key];
                var shown = (column.key === "ciclo" || column.key === "anio")
                    ? (value === null || value === undefined || value === "" ? "Sin información" : String(value))
                    : displayValue(value);
                var cell = node("td", column.type === "number" ? "is-number" : "", shown);
                line.appendChild(cell);
            });
            body.appendChild(line);
        });
        table.appendChild(body);
        scroll.appendChild(table);
        return {scroll: scroll, body: body};
    }

    function renderDetailSection(root, columns, rows) {
        root.replaceChildren();
        if (rows.length) root.appendChild(basicTable(columns || [], rows).scroll);
        else root.appendChild(node("p", "cef-consultas-detail-empty", "No hay registros que coincidan con los CEF, ciclos y filtros seleccionados."));
    }
    function helpTarget(toggle) {
        var id = toggle && toggle.getAttribute("aria-controls");
        return id ? byId(id) : null;
    }
    function helpSurface(toggle) {
        return toggle ? toggle.closest(".cef-consultas-help-surface, .cef-filter-dialog-card, .cef-consultas-detail-section") : null;
    }
    function closeHelp(toggle, restoreFocus) {
        var target = helpTarget(toggle);
        if (!toggle || !target) return false;
        var wasOpen = toggle.getAttribute("aria-expanded") === "true" || !target.hidden;
        target.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
        var surface = helpSurface(toggle);
        if (surface) surface.classList.remove("is-help-open");
        if (restoreFocus && wasOpen && toggle.isConnected) toggle.focus();
        return wasOpen;
    }
    function closeOpenHelp(restoreFocus) {
        var toggle = app.querySelector("[data-cef-help-toggle][aria-expanded='true']");
        return toggle ? closeHelp(toggle, restoreFocus) : false;
    }
    function closeAllHelp(except) {
        app.querySelectorAll("[data-cef-help-toggle][aria-expanded='true']").forEach(function (toggle) {
            if (toggle !== except) closeHelp(toggle, false);
        });
    }
    function toggleHelp(toggle) {
        var target = helpTarget(toggle);
        if (!toggle || !target) return;
        var opening = target.hidden;
        closeAllHelp(toggle);
        target.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));
        var surface = helpSurface(toggle);
        if (surface) surface.classList.toggle("is-help-open", opening);
    }
    function openDetailModal(row, tableData, trigger) {
        detailModalTrigger = trigger;
        var esProfesor = entity.key === "profesores";
        byId("cefConsultasDetalleTipo").textContent = esProfesor ? "Detalle de profesor" : "Detalle de alumno";
        byId("cefConsultasDetalleTitulo").textContent = row.persona || "Persona sin identificar";
        byId("cefConsultasDetalleGruposTituloTexto").textContent =
            esProfesor ? "Asignaciones a grupos" : "Inscripciones a grupos";
        byId("cefConsultasDetalleGruposAyuda").textContent = esProfesor
            ? "Muestra las asignaciones del profesor a grupos que coinciden con los CEF, ciclos y filtros seleccionados."
            : "Muestra las inscripciones del alumno a grupos que coinciden con los CEF, ciclos y filtros seleccionados.";
        byId("cefConsultasDetalleBancoTituloTexto").textContent =
            esProfesor ? "Registro del profesor en los CEF" : "Registro del alumno en los CEF";
        byId("cefConsultasDetalleBancoAyuda").textContent = esProfesor
            ? "Indica en qué CEF y ciclo el profesor está registrado para poder ser asignado a grupos. Las asignaciones concretas se muestran en el bloque de grupos."
            : "Indica en qué CEF y ciclo el alumno está registrado para poder ser inscripto en grupos. Las inscripciones concretas se muestran en el bloque de grupos.";
        closeOpenHelp(false);
        renderDetailSection(byId("cefConsultasDetalleGrupos"), tableData.detail_columns, row.relations || []);
        renderDetailSection(byId("cefConsultasDetalleBanco"), tableData.bank_columns, row.bank || []);
        detailModal.hidden = false;
        detailModal.removeAttribute("aria-hidden");
        document.body.classList.add("cef-consultas-modal-open");
        window.requestAnimationFrame(function () {
            var close = detailModal.querySelector("[data-cef-detalle-cerrar]");
            if (close) close.focus();
        });
    }
    function closeDetailModal(restoreFocus) {
        if (!detailModal || detailModal.hidden) return;
        closeOpenHelp(false);
        detailModal.hidden = true;
        detailModal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("cef-consultas-modal-open");
        if (restoreFocus !== false && detailModalTrigger && detailModalTrigger.isConnected) detailModalTrigger.focus();
        detailModalTrigger = null;
    }
    function renderTable(tableData) {
        tableRoot.replaceChildren();
        var columns = tableData.columns.filter(function (column) { return mode === "estadisticas" || state.columns.has(column.key); });
        if (!tableData.rows.length) {
            tableRoot.appendChild(node("div", "cef-consultas-empty", "No se encontraron resultados. Podés cambiar la búsqueda o quitar filtros."));
            return;
        }
        var hasDetail = mode === "listados" && (entity.key === "alumnos" || entity.key === "profesores");
        if (!columns.length && !hasDetail) {
            tableRoot.appendChild(node("div", "cef-consultas-empty", "Todas las columnas están ocultas. Elegí columnas para mostrar."));
            return;
        }
        var rendered = basicTable(columns, tableData.rows, hasDetail ? function (row, trigger) {
            openDetailModal(row, tableData, trigger);
        } : null);
        tableRoot.appendChild(rendered.scroll);
    }
    function renderResult(result) {
        resultsRoot.hidden = false;
        var total = result.total;
        var pagination = result.table.pagination || {};
        var count = pagination.total_rows || 0;
        byId("cefConsultasTotal").textContent = mode === "listados"
            ? total.formatted + " " + total.unit + (entity.key === "inventario" ? " · " + formatNumber(count) + " registros" : " encontrados")
            : total.label + ": " + total.formatted + (total.unit && total.unit !== "%" ? " " + total.unit : "");
        byId("cefConsultasRango").textContent = "Mostrando " + (pagination.from || 0) + "–" + (pagination.to || 0) + " de " + formatNumber(count);
        var detail = byId("cefConsultasDetalleTotal");
        detail.textContent = total.detail || "";
        detail.hidden = !total.detail;
        renderTable(result.table);
        var pages = byId("cefConsultasPaginas");
        pages.replaceChildren();
        function pageButton(label, page, disabled) {
            var control = button(label, function () { state.page = page; schedule(0, false); });
            control.disabled = disabled;
            return control;
        }
        pages.append(pageButton("Anterior", state.page - 1, state.page <= 1),
            node("span", "", "Página " + state.page + " de " + (pagination.pages || 1)),
            pageButton("Siguiente", state.page + 1, state.page >= (pagination.pages || 1)));
        chartPanel.hidden = mode !== "estadisticas";
        if (mode === "estadisticas") {
            byId("cefConsultasGraficoTitulo").textContent = result.question;
            renderChart(result);
        }
        var definitionText = result.definition || "";
        var resultNotes = result.notes || [];
        var definition = byId("cefMetricasDefinicion");
        definition.textContent = definitionText;
        definition.hidden = !definitionText;
        var notes = byId("cefMetricasNotas");
        notes.replaceChildren();
        resultNotes.forEach(function (text) { notes.appendChild(node("li", "", text)); });
        notes.hidden = !resultNotes.length;
        var resultHelpToggle = byId("cefConsultasResultadoAyudaToggle");
        resultHelpToggle.hidden = !definitionText && !resultNotes.length;
        if (resultHelpToggle.hidden) closeHelp(resultHelpToggle, false);
    }

    /* Se conserva el renderizador SVG del motor anterior, sin selector de gráfico. */
    function asList(value) {
        if (Array.isArray(value)) return value;
        if (!value || typeof value !== "object") return [];
        return Object.keys(value).map(function (key) {
            var item = value[key];
            if (item && typeof item === "object" && !Array.isArray(item)) {
                return Object.assign({ key: key }, item);
            }
            return { key: key, label: String(item || key) };
        });
    }

    function itemKey(item) {
        if (item === null || item === undefined) return "";
        if (typeof item !== "object") return String(item);
        var value = item.key;
        if (value === undefined) value = item.value;
        if (value === undefined) value = item.id;
        return value === null || value === undefined ? "" : String(value);
    }

    function itemLabel(item) {
        if (item === null || item === undefined) return "";
        if (typeof item !== "object") return String(item);
        return String(item.label || item.nombre || item.text || item.key || item.value || "");
    }

    function numberValue(value) {
        if (value === null || value === undefined || value === "") return null;
        var numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : null;
    }

    function formatNumber(value, maximumFractionDigits) {
        var numeric = numberValue(value);
        if (numeric === null) return "Sin datos para calcular";
        return new Intl.NumberFormat("es-AR", {
            maximumFractionDigits: maximumFractionDigits === undefined ? 2 : maximumFractionDigits
        }).format(numeric);
    }

    function displayValue(value) {
        if (value && typeof value === "object") {
            if (value.formatted !== undefined) return String(value.formatted);
            if (value.display !== undefined) return String(value.display);
            return formatNumber(value.value);
        }
        return typeof value === "number" ? formatNumber(value) : (value === null || value === undefined || value === "" ? "Sin información" : String(value));
    }

    function normalizedChartType(type) {
        var aliases = {
            bars: "bar",
            barras: "bar",
            barras_agrupadas: "grouped_bar",
            grouped: "grouped_bar",
            barras_apiladas: "stacked_bar",
            stacked: "stacked_bar",
            linea: "line",
            donut: "doughnut",
            dona: "doughnut"
        };
        type = String(type || "bar");
        return aliases[type] || type;
    }

    function chartData(result) {
        var chart = result.chart || result.grafico || {};
        var labels = asList(chart.labels || chart.etiquetas).map(itemLabel);
        var rawSeries = asList(chart.series || chart.datasets);
        var series = rawSeries.map(function (item, index) {
            var data = item.data || item.values || item.valores || [];
            return {
                name: String(item.name || item.label || item.nombre || "Serie " + (index + 1)),
                data: Array.isArray(data) ? data.map(numberValue) : []
            };
        });
        var data = {
            type: normalizedChartType(chart.type || chart.tipo || "bar"),
            available: asList(chart.available_types || chart.tipos_disponibles).map(function (item) {
                return normalizedChartType(itemKey(item));
            }).filter(Boolean),
            labels: labels,
            fullLabels: asList(chart.full_labels || chart.etiquetas_completas).map(itemLabel),
            orientation: String(chart.orientation || chart.orientacion || ""),
            presentation: String(chart.presentation || ""),
            categoryGroups: asList(chart.category_groups),
            keys: asList(chart.keys),
            maxValue: numberValue(chart.max_value || chart.valor_maximo),
            valueSuffix: String(chart.value_suffix || chart.sufijo_valor || ""),
            series: series,
            omitted: chart.omitted === true || chart.omitido === true,
            message: String(chart.message || chart.mensaje || "")
        };
        if (question && question.key === "asistencia_mes") {
            var periods = labels.map(function (_, index) { return index; }).filter(function (index) {
                return series.some(function (item) { return Number.isFinite(item.data[index]); });
            });
            data.emptyPeriods = periods.length === 0;
            if (periods.length === 1) {
                var index = periods[0];
                data.type = "bar";
                data.presentation = "asistencia_mes_unico";
                data.orientation = "vertical";
                data.valueSuffix = " %";
                data.labels = [labels[index]];
                data.fullLabels = [data.fullLabels[index] || labels[index]];
                data.keys = [data.keys[index]];
                data.series = series.map(function (item) {
                    return {name: item.name, data: [item.data[index] === undefined ? null : item.data[index]]};
                });
            }
        }
        return data;
    }

    function svgElement(name, attributes) {
        var node = document.createElementNS("http://www.w3.org/2000/svg", name);
        Object.keys(attributes || {}).forEach(function (key) {
            node.setAttribute(key, attributes[key]);
        });
        return node;
    }

    function addSvgText(svg, text, attributes, className) {
        var node = svgElement("text", attributes || {});
        if (className) node.setAttribute("class", className);
        node.textContent = text;
        svg.appendChild(node);
        return node;
    }

    function shortLabel(label, length) {
        label = String(label || "Sin información");
        return label.length > length ? label.slice(0, Math.max(1, length - 1)) + "…" : label;
    }

    function wrapLabel(label, maxLength, maxLines) {
        var words = String(label || "Sin información").trim().split(/\s+/).filter(Boolean);
        var lines = [];
        var current = "";
        words.forEach(function (word) {
            var candidate = current ? current + " " + word : word;
            if (current && candidate.length > maxLength && lines.length < maxLines - 1) {
                lines.push(current);
                current = word;
            } else {
                current = candidate;
            }
        });
        if (current) lines.push(current);
        lines = lines.slice(0, maxLines);
        if (lines.length === maxLines && words.join(" ").length > lines.join(" ").length) {
            lines[maxLines - 1] = shortLabel(lines[maxLines - 1], Math.max(1, maxLength - 1));
        }
        return lines.length ? lines : ["Sin información"];
    }

    function renderLegend(series, labelsForDonut) {
        var legend = document.createElement("div");
        legend.className = "cef-metricas-chart-legend";
        var items = labelsForDonut || series.map(function (item) { return item.name; });
        items.forEach(function (label, index) {
            var item = document.createElement("span");
            var swatch = document.createElement("i");
            swatch.style.backgroundColor = colors[index % colors.length];
            var text = document.createTextNode(String(label || "Sin información"));
            item.append(swatch, text);
            legend.appendChild(item);
        });
        chartRoot.appendChild(legend);
    }

    function chartIsEmpty(data) {
        if (!data.labels.length || !data.series.length) return true;
        return !data.series.some(function (series) {
            return series.data.some(function (value) { return value !== null; });
        });
    }

    function renderChartEmpty(message) {
        var empty = document.createElement("div");
        empty.className = "cef-metricas-chart-empty";
        var icon = document.createElement("i");
        icon.className = "fa-regular fa-chart-bar";
        icon.setAttribute("aria-hidden", "true");
        var text = document.createElement("span");
        text.textContent = message || "No hay datos para representar con estos filtros.";
        empty.append(icon, text);
        chartRoot.appendChild(empty);
    }


    function renderHorizontalBars(data) {
        var labelCount = data.labels.length;
        var seriesCount = Math.max(1, data.series.length);
        var maxValue = 0;
        data.series.forEach(function (series) {
            series.data.forEach(function (value) {
                if (value !== null) maxValue = Math.max(maxValue, Math.max(0, value || 0));
            });
        });
        maxValue = Math.max(maxValue || 1, data.maxValue || 0);

        var longest = data.labels.reduce(function (max, label) {
            return Math.max(max, String(label || "").length);
        }, 0);
        var width = Math.max(760, chartRoot.clientWidth || 0);
        var marginLeft = Math.min(300, Math.max(150, longest * 6.2));
        var rowHeight = Math.max(30, seriesCount * 18 + 16);
        var margin = { top: 22, right: 76, bottom: 46, left: marginLeft };
        var height = Math.max(320, margin.top + margin.bottom + labelCount * rowHeight);
        var plotWidth = width - margin.left - margin.right;
        var plotHeight = height - margin.top - margin.bottom;
        var svg = svgElement("svg", {
            viewBox: "0 0 " + width + " " + height,
            width: width,
            height: height,
            "aria-hidden": "true"
        });
        svg.style.minWidth = width + "px";
        svg.style.width = width + "px";
        svg.style.height = height + "px";

        for (var tick = 0; tick <= 5; tick += 1) {
            var ratio = tick / 5;
            var x = margin.left + ratio * plotWidth;
            svg.appendChild(svgElement("line", {
                x1: x, x2: x, y1: margin.top, y2: margin.top + plotHeight,
                "class": "metricas-grid-line"
            }));
            addSvgText(
                svg,
                formatNumber(maxValue * ratio) + data.valueSuffix,
                { x: x, y: height - 18, "text-anchor": "middle" },
                "metricas-axis-label"
            );
        }

        var band = plotHeight / Math.max(1, labelCount);
        data.labels.forEach(function (label, index) {
            var centerY = margin.top + band * index + band / 2;
            var labelNode = addSvgText(
                svg,
                shortLabel(label, 38),
                { x: margin.left - 10, y: centerY + 4, "text-anchor": "end" },
                "metricas-category-label"
            );
            var labelTitle = svgElement("title");
            labelTitle.textContent = data.fullLabels[index] || label;
            labelNode.appendChild(labelTitle);

            var groupHeight = Math.min(band * .68, Math.max(14, seriesCount * 18));
            var groupStart = centerY - groupHeight / 2;
            data.series.forEach(function (series, seriesIndex) {
                var value = series.data[index];
                if (value === null) return;
                value = Math.max(0, value);
                var barHeight = groupHeight / seriesCount;
                var barWidth = (value / maxValue) * plotWidth;
                var y = groupStart + seriesIndex * barHeight;
                var rect = svgElement("rect", {
                    x: margin.left,
                    y: y + 1.5,
                    width: Math.max(0, barWidth),
                    height: Math.max(1, barHeight - 3),
                    rx: 3,
                    fill: colors[seriesIndex % colors.length]
                });
                var title = svgElement("title");
                title.textContent =
                    (data.fullLabels[index] || label) + " · " +
                    series.name + ": " + formatNumber(value) + data.valueSuffix;
                rect.appendChild(title);
                svg.appendChild(rect);

                if (seriesCount === 1) {
                    var valueX = margin.left + barWidth + 7;
                    var valueAnchor = "start";
                    if (valueX > width - margin.right - 12) {
                        valueX = width - margin.right - 6;
                        valueAnchor = "end";
                    }
                    addSvgText(
                        svg,
                        formatNumber(value) + data.valueSuffix,
                        {
                            x: valueX,
                            y: centerY + 4,
                            "text-anchor": valueAnchor
                        },
                        "metricas-value-label"
                    );
                }
            });
        });

        chartRoot.appendChild(svg);
        if (data.series.length > 1) renderLegend(data.series);
    }

    function renderCartesian(data, type) {
        if (data.orientation === "horizontal" && type === "bar") {
            renderHorizontalBars(data);
            return;
        }
        var occupancy = data.presentation === "grupos_ocupacion" && type === "bar";
        var singleMonth = data.presentation === "asistencia_mes_unico" && type === "bar";
        var compactPercentage = occupancy || singleMonth;
        var standardBars = type === "bar" && !compactPercentage;
        var compactBars = compactPercentage || standardBars;
        var labelCount = data.labels.length;
        var seriesCount = Math.max(1, data.series.length);
        var stacked = type === "stacked_bar";
        var line = type === "line";
        var maxValue = 0;
        data.labels.forEach(function (_, index) {
            if (stacked) {
                var sum = data.series.reduce(function (total, series) {
                    return total + Math.max(0, series.data[index] || 0);
                }, 0);
                maxValue = Math.max(maxValue, sum);
            } else {
                data.series.forEach(function (series) { maxValue = Math.max(maxValue, Math.max(0, series.data[index] || 0)); });
            }
        });
        maxValue = compactPercentage ? Math.max(100, Math.ceil(maxValue / 20) * 20) : (maxValue || 1);
        var countStep = standardBars && data.series.every(function (series) {
            return series.data.every(function (value) { return value === null || Number.isInteger(value); });
        }) ? Math.max(1, Math.ceil(maxValue / 5)) : 0;
        if (countStep) maxValue = Math.ceil(maxValue / countStep) * countStep;
        var spans = [];
        var offsets = [];
        var gap = 0;
        var categoryLines = [];
        function occupancyLines(label, length) {
            var chunks = String(label || "Sin información").trim().split(/\s+/).flatMap(function (word) {
                return word.match(new RegExp(".{1," + length + "}", "gu")) || [];
            });
            return wrapLabel(chunks.join(" "), length, Number.MAX_SAFE_INTEGER);
        }
        if (occupancy) {
            data.labels.forEach(function (label, index) {
                var category = data.categoryGroups[index] || {};
                var previous = spans[spans.length - 1];
                if (!previous || previous.key !== category.key) {
                    if (previous) gap += 28;
                    spans.push({key: category.key, label: category.label || "", start: index, end: index});
                } else previous.end = index;
                offsets.push(gap);
                categoryLines.push(occupancyLines(label, 16));
            });
        }
        if (standardBars) {
            categoryLines = data.labels.map(function (label) { return occupancyLines(label, 16); });
        }
        var grouped = occupancy && spans.some(function (span) { return Boolean(span.label); });
        var cycleLabels = occupancy && data.categoryGroups.some(function (category) { return Boolean(category.cycle); });
        var labelHeight = occupancy || standardBars ? Math.max.apply(null, categoryLines.map(function (lines) { return lines.length; })) * 15 : 0;

        var requestedWidth = Math.max(720, labelCount * Math.max(72, line ? 74 : seriesCount * 22 + 42));
        var occupancyWidth = Math.max(360, 86 + labelCount * 128 + gap, Math.min(960, chartRoot.clientWidth || 960, 86 + labelCount * 190 + gap));
        var width = occupancy || standardBars ? occupancyWidth : singleMonth ? Math.max(340, 126 + seriesCount * 86, Math.min(520, chartRoot.clientWidth || 520)) : Math.max(requestedWidth, chartRoot.clientWidth || 0);
        var rotateLabels = !occupancy && !standardBars && labelCount > 8;
        var height = 420;
        var margin = { top: 24, right: 24, bottom: rotateLabels ? 122 : 108, left: 62 };
        if (occupancy) {
            margin.top = 28;
            margin.bottom = labelHeight + 20 + (cycleLabels ? 16 : 0) + (grouped ? 44 : 0);
            height = Math.max(grouped ? 320 : 300, margin.top + 160 + margin.bottom);
        }
        if (standardBars) {
            margin.top = 28;
            margin.bottom = Math.max(50, labelHeight + 24);
            height = Math.max(320, margin.top + 160 + margin.bottom);
        }
        if (singleMonth) {
            height = 320;
            margin.top = 28;
            margin.bottom = 66;
        }
        var plotWidth = width - margin.left - margin.right;
        var plotHeight = height - margin.top - margin.bottom;
        var baseline = margin.top + plotHeight;
        var svg = svgElement("svg", { viewBox: "0 0 " + width + " " + height, width: width, height: height, "aria-hidden": "true" });
        svg.style.minWidth = width + "px";
        svg.style.width = width + "px";
        svg.style.height = height + "px";

        var ticks = compactPercentage ? [0, 20, 40, 60, 80, 100] : countStep ? Array.from({length: Math.round(maxValue / countStep) + 1}, function (_, index) { return index * countStep; }) : [0, 1, 2, 3, 4, 5].map(function (tick) { return maxValue * (tick / 5); });
        if (compactPercentage && maxValue > 100) ticks.push(maxValue);
        ticks.forEach(function (value, tickIndex) {
            var ratio = compactPercentage || countStep ? value / maxValue : tickIndex / 5;
            var y = baseline - ratio * plotHeight;
            svg.appendChild(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: y, y2: y, "class": "metricas-grid-line" }));
            addSvgText(svg, formatNumber(value) + (compactPercentage ? data.valueSuffix : ""), { x: margin.left - 9, y: y + 4, "text-anchor": "end" }, "metricas-axis-label");
        });

        var band = (plotWidth - gap) / Math.max(1, labelCount);
        function categoryX(index) {
            return margin.left + band * index + band / 2 + (offsets[index] || 0);
        }
        if (grouped) {
            spans.forEach(function (span, index) {
                var start = categoryX(span.start) - band / 2;
                var end = categoryX(span.end) + band / 2;
                if (index) svg.appendChild(svgElement("line", {
                    x1: start - 14, x2: start - 14, y1: margin.top, y2: baseline + 4,
                    "class": "metricas-grid-line", "stroke-dasharray": "3 4"
                }));
                var footerY = baseline + labelHeight + 20 + (cycleLabels ? 16 : 0);
                svg.appendChild(svgElement("line", {x1: start + 8, x2: end - 8, y1: footerY, y2: footerY, "class": "metricas-grid-line"}));
                occupancyLines(span.label, Math.max(16, Math.floor((end - start - 12) / 7))).forEach(function (text, lineIndex) {
                    addSvgText(svg, text, {x: (start + end) / 2, y: footerY + 17 + lineIndex * 14, "text-anchor": "middle", "font-weight": 700}, "metricas-axis-label");
                });
            });
        }
        data.labels.forEach(function (label, index) {
            var x = categoryX(index);
            var node;
            if (rotateLabels) {
                node = addSvgText(svg, shortLabel(label, 24), { x: x, y: baseline + 26, "text-anchor": "end", transform: "rotate(-32 " + x + " " + (baseline + 26) + ")" }, "metricas-category-label");
            } else {
                node = svgElement("text", { x: x, y: baseline + (compactBars ? 18 : 28), "text-anchor": "middle", "class": "metricas-category-label" });
                (occupancy || standardBars ? categoryLines[index] : wrapLabel(label, 22, 2)).forEach(function (lineText, lineIndex) {
                    var tspan = svgElement("tspan", { x: x, dy: lineIndex ? 15 : 0 });
                    tspan.textContent = lineText;
                    node.appendChild(tspan);
                });
                svg.appendChild(node);
                if (occupancy && cycleLabels) {
                    addSvgText(svg, (data.categoryGroups[index] || {}).cycle || "", {x: x, y: baseline + labelHeight + 20, "text-anchor": "middle"}, "metricas-axis-label");
                }
            }
            var title = svgElement("title");
            title.textContent = occupancy ? (data.fullLabels[index] || label) + " · ID " + data.keys[index] : label;
            node.appendChild(title);
        });

        if (line) {
            data.series.forEach(function (series, seriesIndex) {
                var points = [];
                series.data.forEach(function (value, index) {
                    if (value === null) return;
                    var x = margin.left + band * index + band / 2;
                    var y = baseline - (Math.max(0, value) / maxValue) * plotHeight;
                    points.push(x + "," + y);
                });
                if (points.length) {
                    svg.appendChild(svgElement("polyline", {
                        points: points.join(" "),
                        fill: "none",
                        stroke: colors[seriesIndex % colors.length],
                        "stroke-linecap": "round",
                        "stroke-linejoin": "round",
                        "stroke-width": 3
                    }));
                }
                series.data.forEach(function (value, index) {
                    if (value === null) return;
                    var x = margin.left + band * index + band / 2;
                    var y = baseline - (Math.max(0, value) / maxValue) * plotHeight;
                    var circle = svgElement("circle", { cx: x, cy: y, r: 4.2, fill: colors[seriesIndex % colors.length], stroke: "#fff", "stroke-width": 2 });
                    var title = svgElement("title");
                    title.textContent = data.labels[index] + " · " + series.name + ": " + formatNumber(value);
                    circle.appendChild(title);
                    svg.appendChild(circle);
                });
            });
        } else {
            data.labels.forEach(function (_, index) {
                var groupWidth = occupancy ? Math.min(56 * seriesCount, band * .52) : singleMonth ? Math.min(72 * seriesCount, band * .72) : standardBars ? Math.min(56 * seriesCount, band * .52) : band * .72;
                var groupStart = compactBars ? categoryX(index) - groupWidth / 2 : margin.left + band * index + (band - groupWidth) / 2;
                var stackOffset = 0;
                data.series.forEach(function (series, seriesIndex) {
                    var value = series.data[index];
                    if (value === null) {
                        if (occupancy) addSvgText(svg, "Sin datos", {x: categoryX(index), y: baseline - 8, "text-anchor": "middle"}, "metricas-axis-label");
                        return;
                    }
                    value = Math.max(0, value);
                    var barWidth = stacked ? groupWidth : groupWidth / seriesCount;
                    var barHeight = (value / maxValue) * plotHeight;
                    var x = stacked ? groupStart : groupStart + seriesIndex * barWidth;
                    var y = stacked ? baseline - stackOffset - barHeight : baseline - barHeight;
                    var rect = svgElement("rect", {
                        x: x + 1.5,
                        y: y,
                        width: Math.max(1, barWidth - 3),
                        height: Math.max(0, barHeight),
                        rx: 3,
                        fill: colors[seriesIndex % colors.length]
                    });
                    var title = svgElement("title");
                    title.textContent = (occupancy ? data.fullLabels[index] || data.labels[index] : data.labels[index]) + " · " + series.name + ": " + formatNumber(value) + (compactPercentage ? data.valueSuffix : "");
                    rect.appendChild(title);
                    svg.appendChild(rect);
                    if (stacked) stackOffset += barHeight;
                    if ((singleMonth || seriesCount === 1) && (compactBars || (labelCount <= 12 && barHeight > 18))) {
                        addSvgText(svg, formatNumber(value) + (compactPercentage ? data.valueSuffix : ""), { x: x + barWidth / 2, y: y - (compactBars ? 7 : 5), "text-anchor": "middle" }, "metricas-value-label");
                    }
                    if (singleMonth) {
                        addSvgText(svg, series.name, {x: x + barWidth / 2, y: baseline + 44, "text-anchor": "middle"}, "metricas-axis-label");
                    }
                });
            });
        }

        if (compactBars) {
            svg.querySelectorAll("text").forEach(function (label) {
                label.style.fontSize = "13px";
            });
        }
        chartRoot.appendChild(svg);
        if (data.series.length > 1) renderLegend(data.series);
    }

    function renderDonut(data) {
        var values = data.series[0].data.map(function (value) { return Math.max(0, value || 0); });
        var total = values.reduce(function (sum, value) { return sum + value; }, 0);
        if (!total) {
            renderChartEmpty();
            return;
        }
        var width = 620;
        var height = 300;
        var cx = 190;
        var cy = 145;
        var radius = 88;
        var circumference = 2 * Math.PI * radius;
        var offset = 0;
        var svg = svgElement("svg", { viewBox: "0 0 " + width + " " + height, width: width, height: height, "aria-hidden": "true" });
        svg.appendChild(svgElement("circle", { cx: cx, cy: cy, r: radius, fill: "none", stroke: "#e2e8f0", "stroke-width": 42 }));
        values.forEach(function (value, index) {
            if (!value) return;
            var length = value / total * circumference;
            var circle = svgElement("circle", {
                cx: cx,
                cy: cy,
                r: radius,
                fill: "none",
                stroke: colors[index % colors.length],
                "stroke-width": 42,
                "stroke-dasharray": length + " " + (circumference - length),
                "stroke-dashoffset": -offset,
                transform: "rotate(-90 " + cx + " " + cy + ")"
            });
            var title = svgElement("title");
            title.textContent = data.labels[index] + ": " + formatNumber(value) + " (" + formatNumber(value / total * 100) + " %)";
            circle.appendChild(title);
            svg.appendChild(circle);
            offset += length;
        });
        addSvgText(svg, formatNumber(total), { x: cx, y: cy + 4, "text-anchor": "middle", "font-size": 28, "font-weight": 800, fill: "#0d2748" });
        addSvgText(svg, "Total", { x: cx, y: cy + 25, "text-anchor": "middle", "font-size": 11, fill: "#64748b" });
        data.labels.forEach(function (label, index) {
            var y = 45 + index * 27;
            if (y > height - 16) return;
            svg.appendChild(svgElement("rect", { x: 355, y: y - 10, width: 11, height: 11, rx: 2, fill: colors[index % colors.length] }));
            addSvgText(svg, shortLabel(label, 29), { x: 374, y: y, "font-size": 11, fill: "#475569" });
            addSvgText(svg, formatNumber(values[index]), { x: 590, y: y, "text-anchor": "end", "font-size": 11, "font-weight": 700, fill: "#334155" });
        });
        chartRoot.appendChild(svg);
    }

    function renderChart(result, requestedType) {
        chartRoot.replaceChildren();
        var data = chartData(result);
        chartRoot.classList.toggle("is-grupos-ocupacion", data.presentation === "grupos_ocupacion");
        chartRoot.classList.toggle("is-asistencia-mes-unico", data.presentation === "asistencia_mes_unico");
        var type = data.presentation === "asistencia_mes_unico" ? "bar" : normalizedChartType(requestedType && requestedType !== "auto" ? requestedType : data.type);
        chartRoot.classList.toggle("is-barras-compactas", type === "bar" && data.orientation !== "horizontal");
        chartBadge.textContent = chartLabels[type] || type;
        chartRoot.setAttribute("aria-label", (chartLabels[type] || "Gráfico") + " del resultado de la consulta");
        if (data.omitted) {
            chartBadge.textContent = "Agregá filtros";
            renderChartEmpty(data.message);
            return;
        }
        if (data.emptyPeriods) {
            renderChartEmpty();
            return;
        }
        if (type === "kpi" || !data.labels.length) {
            renderChartEmpty("El total se muestra en el recuadro principal.");
            return;
        }
        if (chartIsEmpty(data) && data.presentation !== "grupos_ocupacion") {
            renderChartEmpty();
            return;
        }
        if (type === "doughnut") renderDonut(data);
        else renderCartesian(data, type);
    }

    function safeFilePart(value) {
        return String(value || "Grafico")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-zA-Z0-9_-]+/g, "_")
            .replace(/^_+|_+$/g, "")
            .slice(0, 110) || "Grafico";
    }

    function downloadBlob(blob, filename) {
        var link = node("a");
        var objectUrl = URL.createObjectURL(blob);
        link.href = objectUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(function () { URL.revokeObjectURL(objectUrl); }, 1000);
    }

    function exportableSvgMarkup(svg) {
        var clone = svg.cloneNode(true);
        clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        clone.removeAttribute("aria-hidden");
        var style = svgElement("style");
        style.textContent = [
            "text{font-family:Inter,Arial,sans-serif;}",
            ".metricas-grid-line{stroke:#e2e8f0;stroke-width:1;}",
            ".metricas-axis-label,.metricas-category-label{fill:#64748b;font-size:11px;}",
            ".metricas-value-label{fill:#334155;font-size:10px;font-weight:700;}"
        ].join("");
        clone.insertBefore(style, clone.firstChild);
        return new XMLSerializer().serializeToString(clone);
    }

    function drawWrappedCanvasText(ctx, text, x, y, maxWidth, lineHeight, maxLines) {
        var words = String(text || "").trim().split(/\s+/).filter(Boolean);
        var line = "";
        var lines = [];
        words.forEach(function (word) {
            var candidate = line ? line + " " + word : word;
            if (line && ctx.measureText(candidate).width > maxWidth) {
                lines.push(line);
                line = word;
            } else {
                line = candidate;
            }
        });
        if (line) lines.push(line);
        lines = lines.slice(0, maxLines || lines.length);
        lines.forEach(function (value, index) {
            ctx.fillText(value, x, y + index * lineHeight, maxWidth);
        });
        return lines.length;
    }

    function statisticContextText(result) {
        var query = result.query || result.consulta || {};
        var cycles = asList(query.cycle_labels || query.ciclos_etiquetas || query.ciclos).map(itemLabel).filter(Boolean);
        var cefs = asList(query.cefs || query.cef_labels || query.cefs_etiquetas).map(itemLabel).filter(Boolean);
        var parts = [];
        if (cycles.length) parts.push("Ciclo: " + cycles.join(", "));
        if (cefs.length) parts.push("CEF: " + cefs.join(", "));
        return parts.join(" · ");
    }

    function currentChartPngBlob(result, includeStatistics) {
        result = result || lastResult;
        return new Promise(function (resolve, reject) {
            var svg = chartRoot.querySelector("svg");
            if (!svg || !result) {
                reject(new Error("No hay un gráfico disponible para descargar."));
                return;
            }

            var viewBox = svg.viewBox && svg.viewBox.baseVal;
            var svgWidth = viewBox && viewBox.width ? viewBox.width : Number(svg.getAttribute("width")) || svg.clientWidth || 900;
            var svgHeight = viewBox && viewBox.height ? viewBox.height : Number(svg.getAttribute("height")) || svg.clientHeight || 420;
            var data = chartData(result);
            var legendItems = data.type !== "doughnut" && data.series.length > 1 ? data.series : [];
            var legendColumns = Math.max(1, Math.min(4, legendItems.length));
            var legendRows = legendItems.length ? Math.ceil(legendItems.length / legendColumns) : 0;
            var padding = 20;
            var headerHeight = includeStatistics ? 132 : 46;
            var legendHeight = legendRows ? 18 + legendRows * 24 : 0;
            var logicalWidth = Math.max(720, svgWidth + padding * 2);
            var logicalHeight = headerHeight + svgHeight + legendHeight + padding;
            var scale = Math.min(2, 16000 / logicalWidth, 12000 / logicalHeight);
            scale = Math.max(.25, scale);

            var canvas = document.createElement("canvas");
            canvas.width = Math.round(logicalWidth * scale);
            canvas.height = Math.round(logicalHeight * scale);
            var ctx = canvas.getContext("2d");
            if (!ctx) {
                reject(new Error("El navegador no pudo preparar la imagen del gráfico."));
                return;
            }
            ctx.scale(scale, scale);
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, logicalWidth, logicalHeight);
            ctx.strokeStyle = "#d5dde7";
            ctx.lineWidth = 1;
            ctx.strokeRect(.5, .5, logicalWidth - 1, logicalHeight - 1);

            var title = String(result.question || (question && question.label) || "Estadística CEF");
            ctx.fillStyle = "#23476e";
            ctx.font = "700 15px Inter, Arial, sans-serif";
            ctx.textBaseline = "middle";
            ctx.textAlign = "left";
            ctx.fillText(title, padding, 24, logicalWidth - 150);
            ctx.fillStyle = "#526174";
            ctx.font = "12px Inter, Arial, sans-serif";
            ctx.textAlign = "right";
            ctx.fillText(chartBadge.textContent || "Gráfico", logicalWidth - padding, 24, 110);
            ctx.textAlign = "left";

            if (includeStatistics) {
                var total = result.total || {};
                var totalText = String(total.label || "Total") + ": " + String(total.formatted || "—");
                if (total.unit && total.unit !== "%") totalText += " " + total.unit;
                ctx.fillStyle = "#173f66";
                ctx.font = "700 13px Inter, Arial, sans-serif";
                ctx.fillText(totalText, padding, 52, logicalWidth - padding * 2);

                var contextText = statisticContextText(result);
                if (contextText) {
                    ctx.fillStyle = "#526174";
                    ctx.font = "12px Inter, Arial, sans-serif";
                    ctx.fillText(contextText, padding, 73, logicalWidth - padding * 2);
                }

                var definition = String(result.definition || "");
                if (definition) {
                    ctx.fillStyle = "#68758a";
                    ctx.font = "11px Inter, Arial, sans-serif";
                    drawWrappedCanvasText(
                        ctx, definition, padding, contextText ? 95 : 76,
                        logicalWidth - padding * 2, 16, 2
                    );
                }
            }

            var svgBlob = new Blob([exportableSvgMarkup(svg)], {type: "image/svg+xml;charset=utf-8"});
            var svgUrl = URL.createObjectURL(svgBlob);
            var image = new Image();

            image.onload = function () {
                try {
                    var imageX = data.presentation === "grupos_ocupacion" || data.presentation === "asistencia_mes_unico" || (data.type === "bar" && data.orientation !== "horizontal") ? (logicalWidth - svgWidth) / 2 : padding;
                    ctx.drawImage(image, imageX, headerHeight, svgWidth, svgHeight);
                    URL.revokeObjectURL(svgUrl);

                    if (legendItems.length) {
                        var legendTop = headerHeight + svgHeight + 13;
                        var cellWidth = (logicalWidth - padding * 2) / legendColumns;
                        ctx.font = "12px Inter, Arial, sans-serif";
                        ctx.textBaseline = "middle";
                        legendItems.forEach(function (item, index) {
                            var row = Math.floor(index / legendColumns);
                            var column = index % legendColumns;
                            var x = padding + column * cellWidth;
                            var y = legendTop + row * 24;
                            ctx.fillStyle = colors[index % colors.length];
                            ctx.fillRect(x, y - 5, 11, 11);
                            ctx.fillStyle = "#68758a";
                            var label = String(item.name || "Serie " + (index + 1));
                            while (label.length > 4 && ctx.measureText(label).width > cellWidth - 24) {
                                label = label.slice(0, -2);
                            }
                            if (label !== String(item.name || "Serie " + (index + 1))) label += "…";
                            ctx.fillText(label, x + 18, y, cellWidth - 24);
                        });
                    }

                    canvas.toBlob(function (blob) {
                        if (!blob) {
                            reject(new Error("No se pudo generar el archivo PNG."));
                            return;
                        }
                        resolve(blob);
                    }, "image/png");
                } catch (error) {
                    URL.revokeObjectURL(svgUrl);
                    reject(error);
                }
            };
            image.onerror = function () {
                URL.revokeObjectURL(svgUrl);
                reject(new Error("No se pudo convertir el gráfico a PNG."));
            };
            image.src = svgUrl;
        });
    }

    function exportStatisticPng(includeStatistics) {
        return fetchStatisticsForExport().then(function (stat) {
            return currentChartPngBlob(stat.result, includeStatistics).then(function (blob) {
                var prefix = includeStatistics ? "Estadistica_Grafico_CEF_" : "Grafico_CEF_";
                downloadBlob(
                    blob,
                    prefix + safeFilePart(entity.label + "_" + (stat.result.question || "Estadistica")) + ".png"
                );
            });
        });
    }


    if (!entity) { setStatus("No hay listados configurados.", true); return; }
    rendering = true;
    options(cyclesSelect, config.ciclos || [], (config.defaults || {}).ciclos || []);
    options(cefsSelect, config.cefs || [], []);
    enhance(form);
    rendering = false;
    renderEntities();
    byId("cefConsultasModos").addEventListener("click", function (event) {
        var control = event.target.closest("[data-modo]");
        if (!control || mode === control.dataset.modo) return;
        var previousContext = state ? {
            entityKey: entity.key,
            filters: cloneFilters(state.filters),
            definitions: definitions().slice()
        } : null;
        mode = control.dataset.modo;
        changeWorkspace(previousContext);
    });
    questionSelect.addEventListener("change", function () {
        var previousContext = state ? {
            entityKey: entity.key,
            filters: cloneFilters(state.filters),
            definitions: definitions().slice()
        } : null;
        question = config.preguntas.find(function (item) { return item.key === questionSelect.value; });
        changeWorkspace(previousContext);
    });
    app.querySelectorAll("[data-cef-panel-clear]").forEach(function (control) {
        control.addEventListener("click", function () {
            var input = byId(control.dataset.cefPanelClear);
            input.value = "";
            input.dispatchEvent(new Event("input", {bubbles: true}));
            input.focus();
        });
    });
    [byId("cefConsultasBuscarFiltro"), byId("cefConsultasBuscarColumna")].forEach(function (input) {
        input.addEventListener("search", function () {
            input.dispatchEvent(new Event("input", {bubbles: true}));
        });
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") event.preventDefault();
            if (event.key === "Escape") {
                input.value = "";
                input.dispatchEvent(new Event("input", {bubbles: true}));
            }
        });
    });
    filtersToggle.addEventListener("click", function () {
        setPanel(columnsPanel, columnsToggle, false);
        setPanel(filtersPanel, filtersToggle, filtersPanel.hidden);
    });
    columnsToggle.addEventListener("click", function () {
        setPanel(filtersPanel, filtersToggle, false);
        setPanel(columnsPanel, columnsToggle, columnsPanel.hidden);
    });
    byId("cefConsultasBuscarFiltro").addEventListener("input", function () {
        filterOptions(this, filtersRoot, byId("cefConsultasFiltrosVacios"));
    });
    byId("cefConsultasBuscarColumna").addEventListener("input", function () {
        filterOptions(this, byId("cefConsultasColumnas"), byId("cefConsultasColumnasVacias"));
    });
    byId("cefConsultasColumnasIniciales").addEventListener("click", function () {
        state.columns = new Set(entity.columns.filter(function (col) { return col.default; }).map(function (col) { return col.key; }));
        renderColumns();
    });
    byId("cefConsultasColumnasTodas").addEventListener("click", function () {
        state.columns = new Set(entity.columns.map(function (col) { return col.key; }));
        renderColumns();
    });
    byId("cefConsultasColumnasNinguna").addEventListener("click", function () {
        state.columns = new Set();
        renderColumns();
    });
    searchField.addEventListener("change", function () {
        state.searchField = searchField.value;
        syncSearch();
        if (state.search.trim()) schedule(0);
    });
    searchClear.addEventListener("click", function () {
        searchInput.value = "";
        updateSearch(0);
        searchInput.focus();
    });
    byId("cefConsultaFiltroCerrar").addEventListener("click", function () { closeFilterDialog(); });
    byId("cefConsultaFiltroX").addEventListener("click", function () { closeFilterDialog(); });

    filterContent.addEventListener("input", function () {
        filterContent.querySelectorAll("input").forEach(function (input) { input.setCustomValidity(""); });
    });
    byId("cefConsultaFiltroForm").addEventListener("submit", function (event) {
        event.preventDefault();
        var limits = filterContent.querySelectorAll(".cef-consultas-range input");
        if (limits.length === 2) {
            limits[1].setCustomValidity("");
            if (limits[0].value && limits[1].value) {
                var invalid = limits[0].type === "number"
                    ? Number(limits[0].value) > Number(limits[1].value)
                    : limits[0].value > limits[1].value;
                if (invalid) limits[1].setCustomValidity("Hasta debe ser igual o posterior a Desde.");
            }
        }
        if (!this.reportValidity()) return;
        readFilters();
        renderActiveFilters();
        closeFilterDialog();
        schedule(0);
    });
    filterDialog.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            if (closeOpenHelp(true)) return;
            closeFilterDialog();
        }
        if (event.key === "Tab") {
            var items = Array.from(filterDialog.querySelectorAll("button, input, select, [tabindex='0']")).filter(function (item) {
                return !item.disabled && item.getClientRects().length && !item.classList.contains("select2-hidden-accessible");
            });
            var first = items[0], last = items[items.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
    });
    document.addEventListener("click", function (event) {
        var helpToggle = event.target.closest("[data-cef-help-toggle]");
        if (helpToggle && app.contains(helpToggle)) {
            event.preventDefault();
            event.stopPropagation();
            toggleHelp(helpToggle);
            return;
        }
        if (!event.target.closest(".cef-consultas-help-wrap")) closeOpenHelp(false);
    });
    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape" || !detailModal.hidden || !filterDialog.hidden) return;
        if (closeOpenHelp(true)) event.preventDefault();
    });
    detailModal.addEventListener("click", function (event) {
        if (event.target === detailModal || event.target.closest("[data-cef-detalle-cerrar]")) closeDetailModal();
    });
    document.addEventListener("keydown", function (event) {
        if (detailModal.hidden) return;
        if (event.key === "Escape") {
            event.preventDefault();
            if (closeOpenHelp(true)) return;
            closeDetailModal();
            return;
        }
        if (event.key !== "Tab") return;
        var focusable = Array.from(detailModal.querySelectorAll("button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"));
        if (!focusable.length) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (!detailModal.contains(document.activeElement)) { event.preventDefault(); first.focus(); }
        else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    byId("cefMetricasLimpiar").addEventListener("click", function () {
        state.filters = {};
        state.search = "";
        searchInput.value = "";
        syncSearch();
        byId("cefConsultasBuscarFiltro").value = "";
        renderFilters();
        renderActiveFilters();
        schedule(0);
    });
    searchInput.addEventListener("input", function (event) {
        if (event.isComposing) {
            state.search = searchInput.value;
            syncSearch();
            clearTimeout(timer);
            invalidate();
            return;
        }
        updateSearch(220);
    });
    searchInput.addEventListener("compositionend", function () { updateSearch(220); });
    form.addEventListener("change", function (event) { changed(event.target); });
    form.addEventListener("input", function (event) {
        if (event.target.dataset.filterParam) changed(event.target);
    });
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (event.target === form) schedule(0);
    });
    byId("cefConsultasTamano").addEventListener("change", function () {
        state.size = Number(this.value);
        schedule(0);
    });
    exportButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        if (exportButton.disabled) return;
        var open = exportMenu.hidden;
        if (open) {
            exportMenu.hidden = false;
            positionExportMenu();
        } else {
            closeExportMenu();
        }
        exportButton.setAttribute("aria-expanded", String(open));
    });

    window.addEventListener("resize", function () {
        if (!exportMenu.hidden) positionExportMenu();
    });

    exportMenu.addEventListener("click", function (event) {
        var option = event.target.closest("[data-cef-export-option]");
        if (!option || option.disabled) return;
        var action = option.dataset.cefExportOption;

        if (action === "excel-listado") {
            exportExcelList();
            return;
        }
        if (action === "excel-completo") {
            exportExcelComplete();
            return;
        }
        if (action === "excel-estadistica") {
            exportExcelStatistics();
            return;
        }
        if (action === "png") {
            closeExportMenu();
            if (dirty || exporting || !question) return;
            exporting = true;
            syncExport();
            setStatus("Preparando gráfico PNG…");
            exportStatisticPng(false)
                .then(function () {
                    if (!dirty) setStatus("Gráfico PNG descargado.");
                })
                .catch(function (error) {
                    setStatus(error.message || "No se pudo descargar la imagen.", true);
                })
                .finally(function () {
                    exporting = false;
                    syncExport();
                });
        }
    });

    document.addEventListener("click", function (event) {
        if (!exportWrap.contains(event.target)) closeExportMenu();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !exportMenu.hidden) {
            closeExportMenu();
            exportButton.focus();
        }
    });

    function scrubSensitiveClientState() {
        clearTimeout(timer);
        clearTimeout(loadingTimer);
        timer = null;
        loadingTimer = null;
        requestVersion += 1;
        if (controller) {
            controller.abort();
            controller = null;
        }
        closeFilterDialog(false);
        closeDetailModal(false);
        states = {};
        state = null;
        lastResult = null;
        lastParams = null;
        dirty = true;
        exporting = false;
        closeExportMenu();
        exportButton.disabled = true;
        exportButton.setAttribute("aria-disabled", "true");
        searchInput.value = "";
        searchClear.hidden = true;
        byId("cefMetricasFiltrosResumen").replaceChildren();
        byId("cefMetricasTabla").replaceChildren();
        byId("cefConsultasPaginas").replaceChildren();
        byId("cefConsultasTotal").textContent = "";
        byId("cefConsultasRango").textContent = "";
        byId("cefConsultasDetalleTotal").textContent = "";
        byId("cefConsultasDetalleTitulo").textContent = "";
        byId("cefConsultasDetalleGrupos").replaceChildren();
        byId("cefConsultasDetalleBanco").replaceChildren();
        chartRoot.replaceChildren();
        resultsRoot.classList.remove("is-updating");
        resultsRoot.setAttribute("aria-busy", "false");
        resultsRoot.hidden = true;
        setStatus("");
    }

    window.addEventListener("pagehide", scrubSensitiveClientState);
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) window.location.reload();
    });

    changeWorkspace();
}());