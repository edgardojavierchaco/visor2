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
    var exportLink = byId("cefMetricasExportar");
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
    function syncExport() {
        var disabled = dirty || !lastParams || exporting;
        exportLink.setAttribute("aria-disabled", String(disabled));
        if (disabled) { exportLink.removeAttribute("href"); return; }
        var params = new URLSearchParams(lastParams);
        params.delete("pagina");
        params.delete("columnas");
        if (mode === "listados") state.columns.forEach(function (key) { params.append("columnas", key); });
        exportLink.href = app.dataset.exportarUrl + "?" + params.toString();
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
        filterDialog.querySelector(".cef-filter-dialog-help").hidden = filter.type !== "multi";
        filterDialog.hidden = false;
        document.body.classList.add("cef-filter-dialog-open");
        filterInertNodes = Array.from(app.children).filter(function (child) { return child !== filterDialog && !child.inert; });
        filterInertNodes.forEach(function (child) { child.inert = true; });
        byId("cefConsultaFiltroX").focus();
    }
    function closeFilterDialog(restoreFocus) {
        if (!filterDialog || filterDialog.hidden) return;
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
            var searchChip = button("", function () { searchClear.click(); }, "cef-consultas-filter-chip");
            searchChip.id = "cefConsultasBusquedaBadge";
            searchChip.append(icon("fa-solid fa-magnifying-glass"), node("span", "", searchLabel), icon("fa-solid fa-xmark"));
            searchChip.setAttribute("aria-label", "Quitar " + searchLabel);
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
            var chip = button("", function () {
                keys.forEach(function (key) { delete state.filters[key]; });
                renderFilters();
                renderActiveFilters();
                schedule(0);
            }, "cef-consultas-filter-chip");
            chip.append(icon("fa-solid fa-filter"), node("span", "", filter.label + ": " + labels.join(", ")), icon("fa-solid fa-xmark"));
            chip.setAttribute("aria-label", "Quitar filtro " + filter.label + ": " + labels.join(", "));
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
                var cell = node("td", column.type === "number" ? "is-number" : "", displayValue(row[column.key]));
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
    function openDetailModal(row, tableData, trigger) {
        detailModalTrigger = trigger;
        byId("cefConsultasDetalleTipo").textContent = entity.key === "profesores" ? "Detalle de profesor" : "Detalle de alumno";
        byId("cefConsultasDetalleTitulo").textContent = row.persona || "Persona sin identificar";
        byId("cefConsultasDetalleBancoTitulo").innerHTML = '<i class="fa-solid fa-building-columns" aria-hidden="true"></i> ' +
            (entity.key === "profesores" ? "Banco de profesores del CEF" : "Banco de alumnos del CEF");
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
        var definition = byId("cefConsultasDefinicionPanel");
        definition.hidden = mode !== "estadisticas";
        byId("cefMetricasDefinicion").textContent = result.definition || "";
        var notes = byId("cefMetricasNotas");
        notes.replaceChildren();
        (result.notes || []).forEach(function (text) { notes.appendChild(node("li", "", text)); });
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
        return {
            type: normalizedChartType(chart.type || chart.tipo || "bar"),
            available: asList(chart.available_types || chart.tipos_disponibles).map(function (item) {
                return normalizedChartType(itemKey(item));
            }).filter(Boolean),
            labels: labels,
            series: series,
            omitted: chart.omitted === true || chart.omitido === true,
            message: String(chart.message || chart.mensaje || "")
        };
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

    function renderCartesian(data, type) {
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
        maxValue = maxValue || 1;

        var requestedWidth = Math.max(720, labelCount * Math.max(72, line ? 74 : seriesCount * 22 + 42));
        var width = Math.max(requestedWidth, chartRoot.clientWidth || 0);
        var rotateLabels = labelCount > 8;
        var height = 420;
        var margin = { top: 24, right: 24, bottom: rotateLabels ? 122 : 108, left: 62 };
        var plotWidth = width - margin.left - margin.right;
        var plotHeight = height - margin.top - margin.bottom;
        var baseline = margin.top + plotHeight;
        var svg = svgElement("svg", { viewBox: "0 0 " + width + " " + height, width: width, height: height, "aria-hidden": "true" });
        svg.style.minWidth = width + "px";
        svg.style.width = width + "px";
        svg.style.height = height + "px";

        for (var tick = 0; tick <= 5; tick += 1) {
            var ratio = tick / 5;
            var y = baseline - ratio * plotHeight;
            svg.appendChild(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: y, y2: y, "class": "metricas-grid-line" }));
            addSvgText(svg, formatNumber(maxValue * ratio), { x: margin.left - 9, y: y + 4, "text-anchor": "end" }, "metricas-axis-label");
        }

        var band = plotWidth / Math.max(1, labelCount);
        data.labels.forEach(function (label, index) {
            var x = margin.left + band * index + band / 2;
            var node;
            if (rotateLabels) {
                node = addSvgText(svg, shortLabel(label, 24), { x: x, y: baseline + 26, "text-anchor": "end", transform: "rotate(-32 " + x + " " + (baseline + 26) + ")" }, "metricas-category-label");
            } else {
                node = svgElement("text", { x: x, y: baseline + 28, "text-anchor": "middle", "class": "metricas-category-label" });
                wrapLabel(label, 22, 2).forEach(function (lineText, lineIndex) {
                    var tspan = svgElement("tspan", { x: x, dy: lineIndex ? 15 : 0 });
                    tspan.textContent = lineText;
                    node.appendChild(tspan);
                });
                svg.appendChild(node);
            }
            var title = svgElement("title");
            title.textContent = label;
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
                var groupWidth = band * .72;
                var groupStart = margin.left + band * index + (band - groupWidth) / 2;
                var stackOffset = 0;
                data.series.forEach(function (series, seriesIndex) {
                    var value = series.data[index];
                    if (value === null) return;
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
                    title.textContent = data.labels[index] + " · " + series.name + ": " + formatNumber(value);
                    rect.appendChild(title);
                    svg.appendChild(rect);
                    if (stacked) stackOffset += barHeight;
                    if (seriesCount === 1 && labelCount <= 12 && barHeight > 18) {
                        addSvgText(svg, formatNumber(value), { x: x + barWidth / 2, y: y - 5, "text-anchor": "middle" }, "metricas-value-label");
                    }
                });
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
        var type = normalizedChartType(requestedType && requestedType !== "auto" ? requestedType : data.type);
        chartBadge.textContent = chartLabels[type] || type;
        chartRoot.setAttribute("aria-label", (chartLabels[type] || "Gráfico") + " del resultado de la consulta");
        if (data.omitted) {
            chartBadge.textContent = "Agregá filtros";
            renderChartEmpty(data.message);
            return;
        }
        if (type === "kpi" || !data.labels.length) {
            renderChartEmpty("El total se muestra en el recuadro principal.");
            return;
        }
        if (chartIsEmpty(data)) {
            renderChartEmpty();
            return;
        }
        if (type === "doughnut") renderDonut(data);
        else renderCartesian(data, type);
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
    detailModal.addEventListener("click", function (event) {
        if (event.target === detailModal || event.target.closest("[data-cef-detalle-cerrar]")) closeDetailModal();
    });
    document.addEventListener("keydown", function (event) {
        if (detailModal.hidden) return;
        if (event.key === "Escape") {
            event.preventDefault();
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
    exportLink.addEventListener("click", function (event) {
        event.preventDefault();
        if (dirty || !lastParams || exporting) return;
        var url = exportLink.href;
        var name = entity.label;
        exporting = true;
        syncExport();
        setStatus("Preparando Excel con todos los resultados…");
        fetch(url, {credentials: "same-origin", cache: "no-store"}).then(function (response) {
            if (!response.ok || response.redirected) throw new Error("No se pudo exportar. Revisá los CEF y ciclos seleccionados o recargá tu sesión.");
            if (!(response.headers.get("Content-Type") || "").includes("spreadsheetml")) throw new Error("El servidor no devolvió un archivo Excel.");
            return response.blob();
        }).then(function (blob) {
            var link = node("a");
            var objectUrl = URL.createObjectURL(blob);
            link.href = objectUrl;
            link.download = "Consulta_CEF_" + name.replace(/\s+/g, "_") + ".xlsx";
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(function () { URL.revokeObjectURL(objectUrl); }, 1000);
            if (!dirty) setStatus("Excel descargado.");
        }).catch(function (error) { setStatus(error.message, true); })
          .finally(function () { exporting = false; syncExport(); });
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
        exportLink.removeAttribute("href");
        exportLink.setAttribute("aria-disabled", "true");
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