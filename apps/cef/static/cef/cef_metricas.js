(function () {
    "use strict";

    var app = document.getElementById("cefMetricasApp");
    if (!app || app.dataset.metricasReady === "1") return;
    app.dataset.metricasReady = "1";

    var configNode = document.getElementById("cef-metricas-config");
    var config;
    try {
        config = JSON.parse(configNode ? configNode.textContent : "{}");
    } catch (error) {
        config = {};
    }

    var form = document.getElementById("cefMetricasForm");
    var cyclesSelect = document.getElementById("cefMetricasCiclos");
    var cefsSelect = document.getElementById("cefMetricasCefs");
    var clearCyclesButton = document.getElementById("cefMetricasLimpiarCiclos");
    var clearCefsButton = document.getElementById("cefMetricasLimpiarCefs");
    var areaSelect = document.getElementById("cefMetricasArea");
    var indicatorSelect = document.getElementById("cefMetricasIndicador");
    var indicatorHelp = document.getElementById("cefMetricasIndicadorAyuda");
    var groupSelect = document.getElementById("cefMetricasAgrupar");
    var compareSelect = document.getElementById("cefMetricasComparar");
    var chartTypeSelect = document.getElementById("cefMetricasGrafico");
    var filtersRoot = document.getElementById("cefMetricasFiltros");
    var filtersSection = document.getElementById("cefMetricasFiltrosSection");
    var filtersCount = document.getElementById("cefMetricasFiltrosCount");
    var noFilters = document.getElementById("cefMetricasSinFiltros");
    var applyButton = document.getElementById("cefMetricasAplicar");
    var clearButton = document.getElementById("cefMetricasLimpiar");
    var statusRoot = document.getElementById("cefMetricasEstado");
    var resultsRoot = document.getElementById("cefMetricasResultado");
    var summaryNode = document.getElementById("cefMetricasResumen");
    var exportLink = document.getElementById("cefMetricasExportar");
    var kpiLabel = document.getElementById("cefMetricasKpiLabel");
    var kpiValue = document.getElementById("cefMetricasKpiValue");
    var kpiDetail = document.getElementById("cefMetricasKpiDetail");
    var chartRoot = document.getElementById("cefMetricasChart");
    var chartBadge = document.getElementById("cefMetricasChartBadge");
    var tableRoot = document.getElementById("cefMetricasTabla");
    var definitionNode = document.getElementById("cefMetricasDefinicion");
    var notesNode = document.getElementById("cefMetricasNotas");

    var requestController = null;
    var requestVersion = 0;
    var lastResult = null;
    var lastParams = null;
    var ALL_SCOPE_VALUE = "__all__";
    var previousScopeSelections = new WeakMap();
    var colors = ["#2563eb", "#0f766e", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#4d7c0f", "#be185d"];
    var chartLabels = {
        auto: "Automática",
        kpi: "Total",
        bar: "Barras",
        grouped_bar: "Barras agrupadas",
        stacked_bar: "Barras apiladas",
        line: "Línea",
        doughnut: "Dona"
    };

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

    function findByKey(items, key) {
        var wanted = String(key || "");
        return asList(items).find(function (item) { return itemKey(item) === wanted; }) || null;
    }

    function destroySelects(root) {
        if (window.CEFSelects && typeof window.CEFSelects.destroy === "function") {
            window.CEFSelects.destroy(root);
        }
    }

    function initSelects(root, callback) {
        if (window.CEFSelects && typeof window.CEFSelects.init === "function") {
            window.CEFSelects.init(root, callback);
        } else if (typeof window.initCefSelects === "function") {
            window.initCefSelects(root, callback);
        } else if (callback) {
            callback();
        }
    }

    function replaceOptions(select, items, selected, emptyLabel) {
        destroySelects(select);
        select.replaceChildren();
        if (emptyLabel !== undefined && emptyLabel !== null) {
            var emptyOption = document.createElement("option");
            emptyOption.value = "";
            emptyOption.textContent = emptyLabel;
            select.appendChild(emptyOption);
        }
        var selectedValues = new Set((Array.isArray(selected) ? selected : [selected]).filter(function (value) {
            return value !== undefined && value !== null;
        }).map(String));
        asList(items).forEach(function (item) {
            var option = document.createElement("option");
            option.value = itemKey(item);
            option.textContent = itemLabel(item);
            option.selected = selectedValues.has(option.value);
            select.appendChild(option);
        });
        initSelects(select);
    }

    function selectedValues(select) {
        return Array.prototype.slice.call(select.selectedOptions || []).map(function (option) {
            return option.value;
        }).filter(Boolean);
    }

    function scopeItems(items) {
        return [{ key: ALL_SCOPE_VALUE, label: "Todos" }].concat(asList(items));
    }

    function rememberScopeSelection(select) {
        previousScopeSelections.set(select, new Set(selectedValues(select)));
    }

    function syncScopeSelect(select) {
        if (window.CEFSelects && typeof window.CEFSelects.sync === "function") {
            window.CEFSelects.sync(select);
        }
    }

    function selectAllScope(select) {
        Array.prototype.forEach.call(select.options, function (option) {
            option.selected = option.value === ALL_SCOPE_VALUE;
        });
        rememberScopeSelection(select);
        syncScopeSelect(select);
    }

    function normalizeScopeSelection(select) {
        var current = new Set(selectedValues(select));
        var previous = previousScopeSelections.get(select) || new Set();

        if (!current.size) {
            selectAllScope(select);
            return;
        } else if (current.has(ALL_SCOPE_VALUE) && current.size > 1) {
            var keepAll = !previous.has(ALL_SCOPE_VALUE);
            Array.prototype.forEach.call(select.options, function (option) {
                option.selected = keepAll
                    ? option.value === ALL_SCOPE_VALUE
                    : option.value !== ALL_SCOPE_VALUE && current.has(option.value);
            });
        }

        rememberScopeSelection(select);
        syncScopeSelect(select);
    }

    function bindScopeSelection(select) {
        initSelects(select, function () {
            if (!window.jQuery) return;
            window.jQuery(select)
                .off("change.cefMetricasScope")
                .on("change.cefMetricasScope", function () {
                    normalizeScopeSelection(select);
                });
        });
    }

    function scopeValues(select, items) {
        var values = selectedValues(select);
        if (values.indexOf(ALL_SCOPE_VALUE) === -1) return values;
        return asList(items).map(itemKey).filter(Boolean);
    }

    function areas() {
        return asList(config.areas);
    }

    function currentArea() {
        return findByKey(areas(), areaSelect.value) || areas()[0] || null;
    }

    function areaIndicators(area) {
        return asList(area && (area.indicators || area.indicadores));
    }

    function currentIndicator() {
        var area = currentArea();
        return findByKey(areaIndicators(area), indicatorSelect.value) || areaIndicators(area)[0] || null;
    }

    function updateIndicatorHelp() {
        if (!indicatorHelp) return;
        var indicator = currentIndicator();
        var definition = indicator && (indicator.definition || indicator.definicion);
        indicatorHelp.textContent = definition
            ? "Qué representa: " + definition
            : "Elegí una medición para ver qué representa el número.";
    }

    function areaDefinitions(area, name) {
        if (!area) return [];
        if (name === "filters") return asList(area.filters || area.filtros);
        return asList(area.dimensions || area.dimensiones || area.groupings || area.agrupaciones);
    }

    function resolveDefinitions(definitions, allowed) {
        var all = asList(definitions);
        if (!Array.isArray(allowed)) return all;
        return allowed.map(function (entry) {
            if (entry && typeof entry === "object") return entry;
            return findByKey(all, entry);
        }).filter(Boolean);
    }

    function filterType(filter) {
        return String(filter.type || filter.tipo || "multi").toLowerCase();
    }

    function fieldShell(filter) {
        var shell = document.createElement("div");
        shell.className = "cef-field";
        shell.dataset.metricasFilter = itemKey(filter);
        var label = document.createElement("label");
        label.textContent = "Incluir sólo: " + itemLabel(filter);
        shell.appendChild(label);
        return { shell: shell, label: label };
    }

    function renderRangeFilter(filter, kind) {
        var parts = fieldShell(filter);
        var key = itemKey(filter);
        parts.label.htmlFor = "cefMetricasFilter_" + key + "_desde";
        var range = document.createElement("div");
        range.className = "cef-metricas-range";
        ["desde", "hasta"].forEach(function (side) {
            var wrap = document.createElement("label");
            var caption = document.createElement("span");
            caption.textContent = side === "desde" ? "Desde" : "Hasta";
            var input = document.createElement("input");
            input.className = "form-control";
            input.id = "cefMetricasFilter_" + key + "_" + side;
            input.type = kind === "date_range" ? "date" : "number";
            input.dataset.filterKey = key;
            input.dataset.filterSide = side;
            if (kind !== "date_range") {
                if (filter.min !== undefined) input.min = filter.min;
                if (filter.max !== undefined) input.max = filter.max;
                input.step = filter.step || "1";
            }
            wrap.append(caption, input);
            range.appendChild(wrap);
        });
        parts.shell.appendChild(range);
        return parts.shell;
    }

    function renderMultiFilter(filter) {
        var parts = fieldShell(filter);
        var key = itemKey(filter);
        var select = document.createElement("select");
        select.id = "cefMetricasFilter_" + key;
        select.multiple = true;
        select.dataset.cefSelect = "true";
        select.dataset.cefSelectSearch = "always";
        select.dataset.filterKey = key;
        select.dataset.placeholder = filter.placeholder || "Todos (sin limitar)";
        parts.label.htmlFor = select.id;
        asList(filter.choices || filter.opciones).forEach(function (choice) {
            var option = document.createElement("option");
            option.value = itemKey(choice);
            option.textContent = itemLabel(choice);
            select.appendChild(option);
        });
        parts.shell.appendChild(select);
        return parts.shell;
    }

    function renderFilters(openFilters) {
        var area = currentArea();
        var indicator = currentIndicator();
        var definitions = areaDefinitions(area, "filters");
        var allowed = indicator && (indicator.filters || indicator.filtros);
        var visible = resolveDefinitions(definitions, allowed || []);
        var labelOverrides = indicator && (indicator.filter_labels || indicator.etiquetas_filtros) || {};
        destroySelects(filtersRoot);
        filtersRoot.replaceChildren();
        visible.forEach(function (filter) {
            if (labelOverrides[itemKey(filter)]) {
                filter = Object.assign({}, filter, { label: labelOverrides[itemKey(filter)] });
            }
            var type = filterType(filter);
            filtersRoot.appendChild(
                type === "date_range" || type === "number_range"
                    ? renderRangeFilter(filter, type)
                    : renderMultiFilter(filter)
            );
        });
        filtersCount.textContent = visible.length + (visible.length === 1 ? " filtro" : " filtros");
        noFilters.hidden = visible.length > 0;
        filtersRoot.hidden = visible.length === 0;
        if (filtersSection) filtersSection.hidden = visible.length === 0;
        if (filtersSection && openFilters !== undefined) {
            filtersSection.open = visible.length > 0 && openFilters;
        }
        initSelects(filtersRoot);
    }

    function dimensionList(indicator, property) {
        var area = currentArea();
        var definitions = areaDefinitions(area, "dimensions");
        var raw = indicator && indicator[property];
        if (!raw && property === "groupings") raw = indicator && indicator.agrupaciones;
        if (!raw && property === "comparisons") raw = indicator && indicator.comparaciones;
        return resolveDefinitions(definitions, raw || []);
    }

    function populateCompare(preferred) {
        var indicator = currentIndicator();
        var options = groupSelect.value === "grupo" ? [] : dimensionList(indicator, "comparisons").filter(function (dimension) {
            return itemKey(dimension) !== groupSelect.value;
        });
        replaceOptions(compareSelect, options, preferred || "", "No comparar");
        compareSelect.disabled = !groupSelect.value || options.length === 0;
        if (compareSelect.disabled) compareSelect.value = "";
    }

    function populateDimensions(preferredGroup, preferredCompare) {
        var indicator = currentIndicator();
        var groups = dimensionList(indicator, "groupings");
        var chosenGroup = preferredGroup;
        if (chosenGroup === undefined || chosenGroup === null) {
            chosenGroup = groups.length ? itemKey(groups[0]) : "";
        }
        replaceOptions(groupSelect, groups, chosenGroup, "Sólo total general");
        populateCompare(preferredCompare || "");
    }

    function populateIndicators(preferred, openFilters) {
        var indicators = areaIndicators(currentArea());
        var selected = findByKey(indicators, preferred) ? preferred : (indicators[0] ? itemKey(indicators[0]) : "");
        replaceOptions(indicatorSelect, indicators, selected);
        updateIndicatorHelp();
        renderFilters(openFilters);
        populateDimensions();
    }

    function resetChartChoice() {
        chartTypeSelect.replaceChildren();
        var option = document.createElement("option");
        option.value = "auto";
        option.textContent = "Automática";
        chartTypeSelect.appendChild(option);
        chartTypeSelect.value = "auto";
    }

    function initializeForm() {
        var defaults = config.defaults || config.predeterminados || {};
        var cycleItems = config.ciclos || config.cycles || [];
        var defaultCycles = defaults.ciclos || defaults.cycles || [];
        replaceOptions(cyclesSelect, scopeItems(cycleItems), defaultCycles.length ? defaultCycles : [ALL_SCOPE_VALUE]);
        replaceOptions(cefsSelect, scopeItems(config.cefs || []), (defaults.cefs || []).length ? defaults.cefs : [ALL_SCOPE_VALUE]);
        rememberScopeSelection(cyclesSelect);
        rememberScopeSelection(cefsSelect);
        bindScopeSelection(cyclesSelect);
        bindScopeSelection(cefsSelect);
        var areaItems = areas();
        var defaultArea = defaults.area || (areaItems[0] && itemKey(areaItems[0])) || "";
        replaceOptions(areaSelect, areaItems, defaultArea);
        populateIndicators(defaults.indicador || defaults.indicator, false);
        populateDimensions(defaults.agrupar || defaults.group, defaults.comparar || defaults.compare);
        chartTypeSelect.value = defaults.grafico || defaults.chart || "auto";
    }

    function appendRepeated(params, key, values) {
        values.forEach(function (value) { params.append(key, value); });
    }

    function buildParams() {
        var cycles = scopeValues(cyclesSelect, config.ciclos || config.cycles || []);
        if (!cycles.length) throw new Error("Seleccioná al menos un ciclo para realizar el análisis.");
        var params = new URLSearchParams();
        appendRepeated(params, "ciclos", cycles);
        var selectedCefs = selectedValues(cefsSelect);
        if (selectedCefs.indexOf(ALL_SCOPE_VALUE) === -1) {
            appendRepeated(params, "cefs", selectedCefs);
        }
        params.set("area", areaSelect.value);
        var indicator = currentIndicator();
        var indicatorKey = itemKey(indicator);
        if (indicatorKey && indicatorSelect.value !== indicatorKey) {
            populateIndicators(indicatorKey);
        }
        params.set("indicador", itemKey(currentIndicator()) || indicatorKey);
        params.set("agrupar", groupSelect.value || "");
        params.set("comparar", compareSelect.value || "");
        params.set("grafico", chartTypeSelect.value || "auto");

        filtersRoot.querySelectorAll("select[data-filter-key]").forEach(function (select) {
            appendRepeated(params, "f_" + select.dataset.filterKey, selectedValues(select));
        });
        filtersRoot.querySelectorAll("input[data-filter-key]").forEach(function (input) {
            var value = input.value.trim();
            if (!value) return;
            params.set("f_" + input.dataset.filterKey + "_" + input.dataset.filterSide, value);
        });
        return params;
    }

    function setBusy(busy) {
        clearButton.disabled = busy;
        if (window.CEFLoading && typeof window.CEFLoading.startButton === "function") {
            if (busy) window.CEFLoading.startButton(applyButton);
            else window.CEFLoading.restoreButton(applyButton);
            return;
        }
        applyButton.disabled = busy;
        var label = applyButton.querySelector("span");
        if (label) label.textContent = busy ? "Analizando…" : "Aplicar";
    }

    function setStatus(message, mode) {
        statusRoot.replaceChildren();
        if (!message) return;
        var card = document.createElement("div");
        card.className = "cef-metricas-status-card" + (mode === "error" ? " is-error" : "");
        if (mode === "loading") {
            var spinner = document.createElement("span");
            spinner.className = "spinner-border spinner-border-sm";
            spinner.setAttribute("aria-hidden", "true");
            card.appendChild(spinner);
        } else if (mode === "error") {
            var icon = document.createElement("i");
            icon.className = "fa-solid fa-triangle-exclamation";
            icon.setAttribute("aria-hidden", "true");
            card.appendChild(icon);
        }
        var text = document.createElement("span");
        text.textContent = message;
        card.appendChild(text);
        statusRoot.appendChild(card);
    }

    function announceStatus(message) {
        statusRoot.replaceChildren();
        var announcement = document.createElement("span");
        announcement.className = "visually-hidden";
        announcement.textContent = message;
        statusRoot.appendChild(announcement);
    }

    function invalidatePendingRequest() {
        requestVersion += 1;
        if (requestController) requestController.abort();
        requestController = null;
        setBusy(false);
        if (lastResult) {
            setStatus("Hay cambios sin aplicar. Presioná Aplicar para actualizar el resultado.");
            exportLink.setAttribute("aria-disabled", "true");
        } else {
            setStatus("");
        }
    }

    function numberValue(value) {
        if (value === null || value === undefined || value === "") return null;
        var numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : null;
    }

    function formatNumber(value, maximumFractionDigits) {
        var numeric = numberValue(value);
        if (numeric === null) return "No calculable";
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
        chartRoot.setAttribute("aria-label", (chartLabels[type] || "Gráfico") + " del resultado de métricas");
        if (data.omitted) {
            chartBadge.textContent = "Refiná los filtros";
            renderChartEmpty(data.message);
            return;
        }
        if (type === "kpi" || (!groupSelect.value && !data.labels.length)) {
            renderChartEmpty("El total se representa en el indicador principal.");
            return;
        }
        if (chartIsEmpty(data)) {
            renderChartEmpty();
            return;
        }
        if (type === "doughnut") renderDonut(data);
        else renderCartesian(data, type);
    }

    function renderTable(result) {
        tableRoot.replaceChildren();
        var tableData = result.table || result.tabla || {};
        var columns = asList(tableData.columns || tableData.columnas);
        var rows = Array.isArray(tableData.rows || tableData.filas) ? (tableData.rows || tableData.filas) : [];
        if (!rows.length || !columns.length) {
            var empty = document.createElement("div");
            empty.className = "cef-metricas-help";
            empty.textContent = "Sin datos para mostrar en la tabla.";
            tableRoot.appendChild(empty);
            return;
        }
        var section = document.createElement("div");
        section.className = "cef-table-section";
        section.setAttribute("data-cef-table-root", "");

        var toolsBar = document.createElement("div");
        toolsBar.className = "cef-tools";
        var toolsLeft = document.createElement("div");
        toolsLeft.className = "cef-tools-left";
        var showLabel = document.createElement("span");
        showLabel.className = "cef-tools-label";
        showLabel.textContent = "Mostrar";
        var pageSize = document.createElement("select");
        pageSize.setAttribute("data-cef-page-size", "");
        [10, 25, 50].forEach(function (size) {
            var option = document.createElement("option");
            option.value = String(size);
            option.textContent = String(size);
            pageSize.appendChild(option);
        });
        var rowsLabel = document.createElement("span");
        rowsLabel.className = "cef-tools-label";
        rowsLabel.textContent = "filas";
        toolsLeft.append(showLabel, pageSize, rowsLabel);

        var toolsRight = document.createElement("div");
        toolsRight.className = "cef-tools-right";
        var searchWrap = document.createElement("div");
        searchWrap.className = "cef-search-wrap";
        var searchIcon = document.createElement("i");
        searchIcon.className = "fa-solid fa-magnifying-glass";
        searchIcon.setAttribute("aria-hidden", "true");
        var search = document.createElement("input");
        search.type = "search";
        search.placeholder = "Buscar…";
        search.setAttribute("data-cef-table-search", "");
        search.setAttribute("aria-label", "Buscar en la tabla de métricas");
        var searchClear = document.createElement("button");
        searchClear.type = "button";
        searchClear.className = "cef-search-clear";
        searchClear.setAttribute("data-cef-search-clear", "");
        searchClear.setAttribute("aria-label", "Limpiar búsqueda");
        var clearIcon = document.createElement("i");
        clearIcon.className = "fa-solid fa-xmark";
        clearIcon.setAttribute("aria-hidden", "true");
        searchClear.appendChild(clearIcon);
        searchWrap.append(searchIcon, search, searchClear);
        toolsRight.appendChild(searchWrap);
        toolsBar.append(toolsLeft, toolsRight);
        section.appendChild(toolsBar);

        var tableWrap = document.createElement("div");
        tableWrap.className = "cef-table-wrap";
        var table = document.createElement("table");
        table.className = "cef-dt cef-metricas-table";
        table.setAttribute("data-cef-table", "");
        var thead = document.createElement("thead");
        var headerRow = document.createElement("tr");
        columns.forEach(function (column) {
            var th = document.createElement("th");
            th.scope = "col";
            th.textContent = itemLabel(column);
            if (["valor", "numerador", "denominador"].indexOf(itemKey(column)) !== -1) {
                th.classList.add("is-numeric");
            }
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        var tbody = document.createElement("tbody");
        rows.forEach(function (row) {
            var tr = document.createElement("tr");
            columns.forEach(function (column, index) {
                var td = document.createElement("td");
                var key = itemKey(column);
                var value = Array.isArray(row) ? row[index] : row[key];
                td.textContent = displayValue(value);
                if (["valor", "numerador", "denominador"].indexOf(key) !== -1) {
                    td.classList.add("is-numeric");
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.append(thead, tbody);
        tableWrap.appendChild(table);
        section.appendChild(tableWrap);

        var footer = document.createElement("div");
        footer.className = "cef-tfoot";
        var count = document.createElement("span");
        count.className = "cef-tfoot-count";
        count.setAttribute("data-cef-table-count", "");
        count.textContent = rows.length + " registros";
        var pagination = document.createElement("div");
        pagination.className = "cef-tfoot-pagination";
        pagination.setAttribute("data-cef-table-pagination", "");
        footer.append(count, pagination);
        section.appendChild(footer);
        tableRoot.appendChild(section);
        if (typeof window.initCefTables === "function") {
            window.initCefTables(section);
        }
    }

    function resultSummary(result) {
        var query = result.query || result.consulta || {};
        var summary = query.summary || query.resumen || result.summary || result.resumen;
        if (!summary && Array.isArray(query.filter_summary)) {
            var parts = query.filter_summary.slice();
            parts.push("Mostrado por: " + (query.agrupar ? (query.agrupar_label || query.agrupar) : "total general"));
            if (query.comparar) {
                parts.push("Comparación: " + (query.comparar_label || query.comparar));
            }
            summary = parts.join(" · ");
        }
        return String(summary || "Consulta aplicada con los filtros seleccionados.");
    }

    function renderNotes(result) {
        notesNode.replaceChildren();
        var notes = result.notes || result.notas || [];
        if (typeof notes === "string") notes = [notes];
        asList(notes).forEach(function (note) {
            var li = document.createElement("li");
            li.textContent = typeof note === "object" ? itemLabel(note) : String(note);
            notesNode.appendChild(li);
        });
    }

    function updateChartOptions(result) {
        var data = chartData(result);
        var available = data.omitted ? [] : (data.available.length ? data.available : [data.type]);
        var current = chartTypeSelect.value;
        chartTypeSelect.replaceChildren();
        var auto = document.createElement("option");
        auto.value = "auto";
        auto.textContent = "Automática (" + (chartLabels[data.type] || data.type) + ")";
        chartTypeSelect.appendChild(auto);
        available.forEach(function (type) {
            if (type === "auto" || type === "kpi") return;
            var option = document.createElement("option");
            option.value = type;
            option.textContent = chartLabels[type] || type;
            chartTypeSelect.appendChild(option);
        });
        chartTypeSelect.value = Array.prototype.some.call(chartTypeSelect.options, function (option) { return option.value === current; }) ? current : "auto";
    }

    function renderResult(result, params) {
        lastResult = result;
        lastParams = new URLSearchParams(params.toString());
        resultsRoot.hidden = false;
        summaryNode.textContent = resultSummary(result);
        announceStatus("Resultado actualizado. " + summaryNode.textContent);
        var total = result.total || result.kpi || {};
        kpiLabel.textContent = String(total.label || total.etiqueta || "Total");
        kpiValue.textContent = total.formatted !== undefined ? String(total.formatted) : formatNumber(total.value);
        var detail = total.detail || total.detalle || "";
        if (!detail && total.numerator !== undefined && total.denominator !== undefined) {
            detail = formatNumber(total.numerator) + " de " + formatNumber(total.denominator) + " registros incluidos";
        }
        if (!detail && total.unit) detail = String(total.unit);
        kpiDetail.textContent = detail;
        definitionNode.textContent = String(result.definition || result.definicion || "El indicador se calculó para el alcance seleccionado.");
        renderNotes(result);
        updateChartOptions(result);
        renderChart(result, chartTypeSelect.value);
        renderTable(result);
        exportLink.href = app.dataset.exportarUrl + "?" + params.toString();
        exportLink.setAttribute("aria-disabled", "false");
    }

    function requestMetrics(params) {
        if (requestController) requestController.abort();
        var controller = new AbortController();
        requestController = controller;
        var version = ++requestVersion;
        setBusy(true);
        setStatus("Calculando el resultado con los filtros seleccionados…", "loading");
        var url = app.dataset.consultaUrl + "?" + params.toString();
        fetch(url, {
            method: "GET",
            credentials: "same-origin",
            headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" },
            signal: controller.signal
        }).then(function (response) {
            var contentType = response.headers.get("content-type") || "";
            if (response.redirected || contentType.indexOf("application/json") === -1) {
                throw new Error("La sesión venció o la respuesta no es válida. Volvé a ingresar e intentá nuevamente.");
            }
            return response.json().then(function (payload) {
                if (!response.ok || payload.ok === false) {
                    throw new Error(payload.message || payload.mensaje || "No se pudo calcular la consulta.");
                }
                return payload;
            });
        }).then(function (payload) {
            if (version !== requestVersion) return;
            renderResult(payload, params);
        }).catch(function (error) {
            if (error && error.name === "AbortError") return;
            if (version !== requestVersion) return;
            setStatus(error && error.message ? error.message : "No se pudo calcular la consulta.", "error");
        }).finally(function () {
            if (requestController === controller) requestController = null;
            if (version === requestVersion) setBusy(false);
        });
    }

    function submitCurrent() {
        try {
            requestMetrics(buildParams());
        } catch (error) {
            setStatus(error.message, "error");
        }
    }

    areaSelect.addEventListener("change", function () {
        populateIndicators(undefined, false);
        resetChartChoice();
    });

    indicatorSelect.addEventListener("change", function () {
        renderFilters(false);
        populateDimensions();
        resetChartChoice();
    });

    groupSelect.addEventListener("change", function () {
        populateCompare("");
        resetChartChoice();
    });

    compareSelect.addEventListener("change", resetChartChoice);

    cyclesSelect.addEventListener("change", function () {
        normalizeScopeSelection(cyclesSelect);
    });

    cefsSelect.addEventListener("change", function () {
        normalizeScopeSelection(cefsSelect);
    });

    clearCyclesButton.addEventListener("click", function () {
        selectAllScope(cyclesSelect);
        invalidatePendingRequest();
    });

    clearCefsButton.addEventListener("click", function () {
        selectAllScope(cefsSelect);
        invalidatePendingRequest();
    });

    chartTypeSelect.addEventListener("change", function () {
        if (lastParams) lastParams.set("grafico", chartTypeSelect.value || "auto");
        if (lastResult) renderChart(lastResult, chartTypeSelect.value);
    });

    form.addEventListener("change", function (event) {
        if (event.target === chartTypeSelect) return;
        invalidatePendingRequest();
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        submitCurrent();
    });

    clearButton.addEventListener("click", function () {
        if (requestController) requestController.abort();
        lastResult = null;
        lastParams = null;
        resultsRoot.hidden = true;
        exportLink.href = "#";
        exportLink.setAttribute("aria-disabled", "true");
        initializeForm();
        submitCurrent();
    });

    exportLink.addEventListener("click", function (event) {
        if (exportLink.getAttribute("aria-disabled") === "true" || !lastParams) event.preventDefault();
    });

    initializeForm();
    if (!areas().length) {
        setStatus("No hay áreas de métricas configuradas.", "error");
        return;
    }
    submitCurrent();
})();
