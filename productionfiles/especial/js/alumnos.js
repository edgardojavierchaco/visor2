(function () {
    "use strict";

    var installed = false;
    var reloadChecked = false;
    var activeSearchRequest = null;
    var activeBajaRequest = null;
    var sectionGroupTableSequence = 0;

    function helpers() {
        return window.EspecialBusquedaPersonas;
    }

    function sanitizeCuilInput(input) {
        if (!input) return;
        var digits = String(input.value || "").replace(/\D/g, "").slice(0, 11);
        if (input.value !== digits) input.value = digits;
    }

    function initCuilInput(root) {
        var scope = root && root.querySelector ? root : document;
        var input = root && root.matches && root.matches("#modalBusquedaAlumno input[name='cuil']")
            ? root
            : scope.querySelector("#modalBusquedaAlumno input[name='cuil']");
        if (!input || input.dataset.especialCuilReady === "1") return;
        input.dataset.especialCuilReady = "1";
        sanitizeCuilInput(input);
        input.addEventListener("input", function () { sanitizeCuilInput(input); });
    }

    function setSearchLoading(modal, loading) {
        if (!modal) return;
        var results = modal.querySelector("[data-cef-modal-search-results]");
        modal.classList.toggle("is-searching", loading);
        if (!results) return;
        if (loading) results.setAttribute("aria-busy", "true");
        else results.removeAttribute("aria-busy");
    }

    function cancelSearch(modal) {
        if (!activeSearchRequest || (modal && activeSearchRequest.modal !== modal)) return;
        var operation = activeSearchRequest;
        operation.cancelled = true;
        operation.controller.abort();
        activeSearchRequest = null;
        setSearchLoading(operation.modal, false);
    }

    function destroyMatriculaSelects(root) {
        if (!root || !window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
        var selects = [];
        if (root.matches && root.matches("[data-especial-matricula-cue-select]")) selects.push(root);
        if (root.querySelectorAll) {
            Array.prototype.push.apply(selects, root.querySelectorAll("[data-especial-matricula-cue-select]"));
        }
        selects.forEach(function (select) {
            var $select = window.jQuery(select);
            if (!$select.data("select2")) return;
            $select.off(".especialMatricula");
            $select.select2("destroy");
        });
    }

    function resetSearchModal(modal) {
        if (!modal) return;
        cancelSearch(modal);
        setSearchLoading(modal, false);
        var input = modal.querySelector("input[name='cuil']");
        var submitButton = modal.querySelector("[data-modal-search-form] button[type='submit']");
        var results = modal.querySelector("[data-cef-modal-search-results]");
        if (input) input.value = "";
        if (submitButton) submitButton.disabled = false;
        if (!results) return;

        destroyMatriculaSelects(results);
        results.querySelectorAll("[data-cef-modal-feedback], [data-cef-modal-search-help]").forEach(function (node) {
            node.remove();
        });
        var table = results.querySelector(".cef-modal-table");
        var tbody = table ? table.querySelector("tbody") : null;
        if (!tbody) return;
        var row = document.createElement("tr");
        var cell = document.createElement("td");
        var emptyState = document.createElement("div");
        var icon = document.createElement("i");
        cell.colSpan = table.querySelectorAll("thead th").length || 1;
        emptyState.className = "cef-modal-msg";
        icon.className = "fa-solid fa-id-card";
        icon.setAttribute("aria-hidden", "true");
        icon.style.color = "#bfdbfe";
        emptyState.appendChild(icon);
        emptyState.appendChild(document.createTextNode("Ingrese CUIL para buscar una persona."));
        cell.appendChild(emptyState);
        row.appendChild(cell);
        tbody.replaceChildren(row);
    }

    function openSearchModal(modal) {
        if (!modal) return;
        resetSearchModal(modal);
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        helpers().focusSearchInput(modal, "input[name='cuil']");
    }

    function closeSearchModal(modal) {
        if (!modal) return;
        resetSearchModal(modal);
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        if (modal.dataset.volverUrl && window.history && window.history.replaceState) {
            window.history.replaceState({}, "", modal.dataset.volverUrl);
        }
    }

    function replaceAlumnoModal(modal, html, historyUrl) {
        return helpers().replaceModalDialog(modal, html, {
            dialogSelector: ".cef-modal",
            historyUrl: historyUrl,
            focusSelector: "input[name='cuil']"
        });
    }

    function showAlumnoFeedback(modal, message, level) {
        var results = modal && modal.querySelector("[data-cef-modal-search-results]");
        if (!results || !message) return;
        results.querySelectorAll("[data-cef-modal-feedback]").forEach(function (node) {
            node.remove();
        });
        var feedback = document.createElement("div");
        feedback.className = "alert alert-" + (level === "success" ? "success" : "danger") + " mb-3";
        feedback.setAttribute("data-cef-modal-feedback", "true");
        feedback.setAttribute("role", "alert");
        feedback.textContent = message;
        results.insertBefore(feedback, results.firstChild);
    }

    function handleAlumnoJson(modal, data) {
        if (!data || typeof data !== "object") return false;
        var replaced = false;
        if (Array.isArray(data.fragments)) {
            data.fragments.forEach(function (fragment) {
                if (!fragment || !fragment.selector || typeof fragment.html !== "string") return;
                replaced = Boolean(helpers().replaceFragment(fragment.selector, fragment.html)) || replaced;
            });
        }
        if (data.fragment_html) {
            replaced = Boolean(helpers().replaceFragment(data.fragment_selector, data.fragment_html));
        }
        if (data.modal_html) {
            replaced = replaceAlumnoModal(modal, data.modal_html, window.location.href) || replaced;
        }
        if (data.close_modal) {
            if (modal.id === "modalBusquedaAlumno") resetSearchModal(modal);
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
        }
        if (!data.ok) showAlumnoFeedback(modal, data.message, "error");
        if (data.reload_page) {
            window.location.reload();
        }
        return true;
    }

    function submitModalForm(event) {
        var form = event.target.closest("[data-modal-search-form], [data-modal-post-form], [data-especial-baja-form]");
        if (!form || event.defaultPrevented) return;
        var modal = form.closest("#modalBusquedaAlumno, #modalBajaAlumnoEspecial");
        if (!modal) return;
        event.preventDefault();

        var method = (form.getAttribute("method") || "get").toLowerCase();
        var isSearch = method === "get" && modal.id === "modalBusquedaAlumno";
        var operation = null;
        var submitButton = form.querySelector("button[type='submit']");
        if (submitButton) submitButton.disabled = true;
        var request = {
            credentials: "same-origin",
            headers: { "Accept": "text/html", "X-Requested-With": "XMLHttpRequest" }
        };
        if (isSearch) {
            sanitizeCuilInput(form.querySelector("input[name='cuil']"));
            cancelSearch();
            operation = { cancelled: false, controller: new AbortController(), modal: modal };
            activeSearchRequest = operation;
            request.signal = operation.controller.signal;
            setSearchLoading(modal, true);
        }
        var targetUrl = method === "get" ? helpers().buildFormUrl(form) : form.getAttribute("action");
        if (method !== "get") {
            request.method = "POST";
            request.body = new FormData(form);
        }

        helpers().fetchRequest(targetUrl, request, isSearch)
            .then(function (response) {
                return helpers().parseResponse(response, "La operación del modal devolvió un error HTTP.");
            })
            .then(function (result) {
                if (isSearch && (operation.cancelled || activeSearchRequest !== operation)) return;
                if (result.json) {
                    handleAlumnoJson(modal, result.json);
                    return;
                }
                if (result.redirected && helpers().replacePanel(result.html)) {
                    if (modal.id === "modalBusquedaAlumno") resetSearchModal(modal);
                    modal.classList.remove("is-open");
                    modal.setAttribute("aria-hidden", "true");
                    if (result.url) window.history.replaceState({}, "", result.url);
                    return;
                }
                var historyUrl = method === "get" && modal.id === "modalBusquedaAlumno"
                    ? modal.dataset.volverUrl || window.location.href
                    : method === "get" ? targetUrl : window.location.href;
                if (!replaceAlumnoModal(modal, result.html, historyUrl)) {
                    showAlumnoFeedback(
                        modal,
                        "No se pudo actualizar el resultado de la inscripción.",
                        "error"
                    );
                }
            })
            .catch(function (error) {
                if (
                    isSearch
                    && (operation.cancelled || activeSearchRequest !== operation || (error && error.name === "AbortError"))
                ) return;
                showAlumnoFeedback(
                    modal,
                    error && error.message
                        ? error.message
                        : "No se pudo completar la inscripción.",
                    "error"
                );
            })
            .finally(function () {
                if (submitButton) submitButton.disabled = false;
                if (isSearch && activeSearchRequest === operation) {
                    activeSearchRequest = null;
                    setSearchLoading(modal, false);
                }
            });
    }

    function clearBajaLoading(modal) {
        if (!modal) return;
        modal.removeAttribute("aria-busy");
        var body = modal.querySelector(".cef-modal-body");
        if (body) body.replaceChildren();
    }

    function showBajaLoading(modal) {
        var body = modal ? modal.querySelector(".cef-modal-body") : null;
        if (!body) return false;
        body.replaceChildren();
        var status = document.createElement("div");
        status.className = "especial-partial-loading";
        status.setAttribute("role", "status");
        status.setAttribute("aria-live", "polite");
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("aria-hidden", "true");
        status.appendChild(spinner);
        status.appendChild(document.createTextNode("Cargando..."));
        body.appendChild(status);
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        modal.setAttribute("aria-busy", "true");
        return true;
    }

    function cancelBaja(modal) {
        if (!activeBajaRequest || (modal && activeBajaRequest.modal !== modal)) return;
        var operation = activeBajaRequest;
        operation.cancelled = true;
        operation.controller.abort();
        activeBajaRequest = null;
        clearBajaLoading(operation.modal);
    }

    function openBaja(trigger) {
        if (activeBajaRequest) return;
        if (window.EspecialDropdowns && typeof window.EspecialDropdowns.closeForElement === "function") {
            window.EspecialDropdowns.closeForElement(trigger);
        }
        var modal = document.getElementById("modalBajaAlumnoEspecial");
        var url = new URL(trigger.href, window.location.href);
        if (!modal || url.origin !== window.location.origin || !showBajaLoading(modal)) {
            window.location.href = url.toString();
            return;
        }
        var operation = {
            cancelled: false,
            controller: new AbortController(),
            historyUrl: modal.dataset.volverUrl || window.location.href,
            modal: modal,
            url: url.toString()
        };
        activeBajaRequest = operation;
        helpers().fetchRequest(operation.url, {
            credentials: "same-origin",
            signal: operation.controller.signal,
            headers: { "Accept": "text/html", "X-Requested-With": "XMLHttpRequest" }
        })
            .then(function (response) { return helpers().parseResponse(response, "No se pudo cargar la baja del alumno."); })
            .then(function (result) {
                if (operation.cancelled || activeBajaRequest !== operation) return;
                if (!replaceAlumnoModal(modal, result.html, operation.historyUrl)) {
                    throw new Error("La respuesta no contiene el modal de baja.");
                }
            })
            .catch(function (error) {
                if (operation.cancelled || activeBajaRequest !== operation) return;
                if (error && error.name === "AbortError") {
                    activeBajaRequest = null;
                    clearBajaLoading(modal);
                    return;
                }
                activeBajaRequest = null;
                clearBajaLoading(modal);
                window.location.href = operation.url;
            })
            .finally(function () {
                if (activeBajaRequest !== operation) return;
                activeBajaRequest = null;
                modal.removeAttribute("aria-busy");
            });
    }

    function closeModal(modal) {
        if (!modal) return;
        if (modal.id === "modalBusquedaAlumno") closeSearchModal(modal);
        else {
            if (modal.id === "modalBajaAlumnoEspecial") cancelBaja(modal);
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
            if (modal.dataset.volverUrl) window.history.replaceState({}, "", modal.dataset.volverUrl);
        }
    }

    function alumnoSectionTables(root) {
        var scope = root && root.querySelectorAll ? root : document;
        var tables = [];
        if (root && root.matches && root.matches("table[data-cef-alumnos-seccion-groups]")) {
            tables.push(root);
        }
        if (scope.querySelectorAll) {
            Array.prototype.push.apply(
                tables,
                scope.querySelectorAll("table[data-cef-alumnos-seccion-groups]")
            );
        }
        return tables;
    }

    function buildAlumnoSectionGroups(table) {
        var groups = [];
        var rows = table.querySelectorAll(
            "tbody tr[data-cef-alumno-seccion-header], tbody tr[data-cef-alumno-seccion-row]"
        );

        Array.prototype.forEach.call(rows, function (row) {
            var key = row.getAttribute("data-cef-table-group-key") || "";
            var group = groups.filter(function (candidate) { return candidate.key === key; })[0];
            if (!group) {
                group = {
                    key: key,
                    id: "grupo-" + (groups.length + 1),
                    header: null,
                    rows: []
                };
                groups.push(group);
            }
            row.dataset.cefAlumnoSeccionId = group.id;
            if (row.hasAttribute("data-cef-alumno-seccion-header")) group.header = row;
            else group.rows.push(row);
        });

        return groups.filter(function (group) { return group.header; });
    }

    function setAlumnoSectionArrow(toggle, expanded) {
        var arrow = toggle.querySelector("[data-cef-alumno-seccion-arrow]");
        if (!arrow) return;
        var icon = arrow.querySelector("i") || arrow;
        icon.classList.toggle("fa-chevron-right", !expanded);
        icon.classList.toggle("fa-chevron-down", expanded);
    }

    function updateAlumnoSectionAccessibility(table, group) {
        var toggle = group.header.querySelector("[data-cef-alumno-seccion-toggle]");
        if (!toggle) return;

        var baseId = "cef-alumno-seccion-" + table._cefAlumnoSectionPrefix + "-" + group.id;
        group.header.id = baseId + "-encabezado";
        toggle.id = baseId + "-toggle";
        var controls = group.rows.map(function (row, index) {
            row.id = baseId + "-fila-" + (index + 1);
            return row.id;
        });
        if (controls.length) toggle.setAttribute("aria-controls", controls.join(" "));

        var count = group.header.querySelector("[data-cef-alumno-seccion-count]");
        if (count) {
            var total = group.rows.length;
            count.textContent = " · " + total + (total === 1 ? " alumno" : " alumnos");
        }
    }

    function setAlumnoSectionState(group, expanded) {
        var toggle = group.header.querySelector("[data-cef-alumno-seccion-toggle]");
        if (toggle) {
            toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
            setAlumnoSectionArrow(toggle, expanded);
        }
        group.rows.forEach(function (row) {
            row.classList.toggle("oculta-por-seccion", !expanded);
        });
    }

    function refreshAlumnoSectionTable(table, reset) {
        var groups = buildAlumnoSectionGroups(table);
        var state = table._cefAlumnoSectionState || {};
        table._cefAlumnoSectionGroups = groups;
        if (reset) state = {};

        groups.forEach(function (group) {
            state[group.id] = Boolean(state[group.id]);
            updateAlumnoSectionAccessibility(table, group);
            setAlumnoSectionState(group, state[group.id]);
        });
        table._cefAlumnoSectionState = state;
    }

    function resetAlumnoSectionTable(table) {
        refreshAlumnoSectionTable(table, true);
    }

    function toggleAlumnoSection(table, sectionId) {
        var groups = table._cefAlumnoSectionGroups || [];
        var group = groups.filter(function (candidate) {
            return candidate.id === sectionId;
        })[0];
        if (!group) return;

        var state = table._cefAlumnoSectionState || {};
        state[group.id] = !state[group.id];
        table._cefAlumnoSectionState = state;
        setAlumnoSectionState(group, state[group.id]);
    }

    function bindAlumnoSectionTable(table) {
        var root = table.closest(".cef-panel-body, .cef-panel") || document;
        var pagination = root.querySelector("[data-cef-table-pagination]");
        if (pagination) pagination.addEventListener("click", function () { resetAlumnoSectionTable(table); });

        if (window.jQuery && window.jQuery.fn) {
            window.jQuery(table)
                .off("draw.dt.cefAlumnoSectionGroups")
                .on("draw.dt.cefAlumnoSectionGroups", function () {
                    resetAlumnoSectionTable(table);
                });
        }
    }

    function initAlumnoSectionTable(table) {
        if (!table || table.dataset.cefAlumnoSectionReady === "1") return;
        sectionGroupTableSequence += 1;
        table._cefAlumnoSectionPrefix = "tabla-" + sectionGroupTableSequence;
        table._cefAlumnoSectionState = {};
        table.dataset.cefAlumnoSectionReady = "1";
        bindAlumnoSectionTable(table);
        resetAlumnoSectionTable(table);
    }

    function initAlumnoSectionTables(root) {
        alumnoSectionTables(root).forEach(initAlumnoSectionTable);
    }

    function installExpansion() {
        document.addEventListener("click", function (event) {
            var toggle = event.target.closest("[data-cef-alumno-secciones-toggle]");
            if (!toggle) return;
            var secciones = toggle.closest(".cef-alumno-secciones");
            if (!secciones) return;
            event.preventDefault();
            var expanded = toggle.getAttribute("aria-expanded") === "true";
            secciones.querySelectorAll("[data-cef-alumno-seccion-adicional]").forEach(function (seccion) {
                seccion.hidden = expanded;
            });
            toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
            if (expanded) {
                var restantes = toggle.getAttribute("data-cef-alumno-secciones-restantes");
                toggle.textContent = restantes === "1" ? "+ 1 sección más" : "+ " + restantes + " secciones más";
            } else {
                toggle.textContent = "Mostrar menos";
            }
        });
    }

    function matriculaEditors(root) {
        var scope = root && root.querySelectorAll ? root : document;
        var editors = [];
        if (root && root.matches && root.matches("[data-especial-matricula-editor]")) editors.push(root);
        Array.prototype.push.apply(editors, scope.querySelectorAll("[data-especial-matricula-editor]"));
        return editors;
    }

    function syncMatriculaAlta(root) {
        var scope = root && root.querySelectorAll ? root : document;
        if (root && root.closest && root.closest("tr")) scope = root.closest("tr");
        var buttons = [];
        if (scope.matches && scope.matches("[data-especial-matricula-alta-submit]")) buttons.push(scope);
        if (scope.querySelectorAll) {
            Array.prototype.push.apply(
                buttons,
                scope.querySelectorAll("[data-especial-matricula-alta-submit]")
            );
        }
        buttons.forEach(function (button) {
            if (!button.hasAttribute("data-especial-matricula-required")) return;
            var row = button.closest("tr");
            var cueSelect = row && row.querySelector("[data-especial-matricula-cue-select]");
            if (!cueSelect) return;
            var cue = String(cueSelect.value || "").replace(/\D/g, "");
            var destino = String(cueSelect.dataset.currentCue || "").replace(/\D/g, "");
            button.disabled = cue.length !== 9 || !destino || cue === destino;
        });
    }

    function matriculaCueParts(data) {
        var cueanexo = String(data && data.id || "").trim();
        var text = String(data && data.text || "").trim();
        var separator = " — ";
        var separatorIndex = text.indexOf(separator);
        var nombre = separatorIndex >= 0
            ? text.slice(separatorIndex + separator.length).trim()
            : "";
        if (!nombre && text && text !== cueanexo) nombre = text;
        return { cueanexo: cueanexo, nombre: nombre };
    }

    function renderMatriculaCue(data, selection) {
        var parts = matriculaCueParts(data);
        var label = document.createElement("span");
        label.className = "cef-matricula-compartida-label" + (selection ? " is-selection" : "");

        var cue = document.createElement("span");
        cue.className = "cef-matricula-compartida-cue";
        cue.textContent = parts.cueanexo;
        label.appendChild(cue);

        if (parts.nombre) {
            var separator = document.createElement("span");
            separator.className = "cef-matricula-compartida-separator";
            separator.setAttribute("aria-hidden", "true");
            separator.textContent = "—";
            label.appendChild(separator);

            var nombre = document.createElement("span");
            nombre.className = "cef-matricula-compartida-name";
            nombre.title = parts.nombre;
            nombre.textContent = parts.nombre;
            label.appendChild(nombre);
        }
        return label;
    }

    function renderMatriculaResult(data) {
        if (data.loading) return data.text;
        return renderMatriculaCue(data, false);
    }

    function renderMatriculaSelection(data) {
        if (!data.id) return data.text;
        return renderMatriculaCue(data, true);
    }

    function normalizeMatriculaSearchTerm(term) {
        var normalized = String(term || "").trim();
        if (/^[\d\s.-]+$/.test(normalized)) {
            return normalized.replace(/[.\s-]/g, "").slice(0, 9);
        }
        return normalized;
    }

    function preventMatriculaNumericOverflow(event) {
        var input = event && event.currentTarget;
        var inserted = String(event && event.data || "");
        if (!input || !/^\d$/.test(inserted) || !/^\d*$/.test(input.value)) return;
        var start = input.selectionStart == null ? input.value.length : input.selectionStart;
        var end = input.selectionEnd == null ? start : input.selectionEnd;
        var nextValue = input.value.slice(0, start) + inserted + input.value.slice(end);
        if (nextValue.length > 9) event.preventDefault();
    }

    function sanitizeMatriculaSearchInput(input) {
        if (!input) return;
        var value = String(input.value || "");
        if (/^\d+$/.test(value) && value.length > 9) {
            value = value.slice(0, 9);
            input.value = value;
        }
        if (/^\d+$/.test(value)) input.setAttribute("inputmode", "numeric");
        else input.removeAttribute("inputmode");
    }

    function centerMatriculaDropdown(select) {
        var fieldContainer = select && select.nextElementSibling;
        var dropdown = document.querySelector(
            ".cef-matricula-compartida-dropdown.select2-dropdown"
        );
        if (!fieldContainer || !fieldContainer.classList.contains("select2") || !dropdown) return;

        dropdown.style.transform = "none";
        var fieldRect = fieldContainer.getBoundingClientRect();
        var dropdownRect = dropdown.getBoundingClientRect();
        var viewportPadding = 16;
        var centeredLeft = fieldRect.left + (fieldRect.width - dropdownRect.width) / 2;
        var maxLeft = window.innerWidth - viewportPadding - dropdownRect.width;
        var clampedLeft = Math.min(Math.max(centeredLeft, viewportPadding), maxLeft);
        dropdown.style.transform = "translateX(" + Math.round(clampedLeft - dropdownRect.left) + "px)";
    }

    function initMatricula(root) {
        var editors = matriculaEditors(root);
        syncMatriculaAlta(root);
        if (!window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
        editors.forEach(function (editor) {
            var cueSelect = editor.querySelector("[data-especial-matricula-cue-select]");
            if (!cueSelect) return;
            var $cueSelect = window.jQuery(cueSelect);
            if ($cueSelect.data("select2")) return;
            var dropdownParent = cueSelect.closest(".cef-overlay");
            if (!dropdownParent) dropdownParent = cueSelect.closest(".cef-modal");
            var searchState = {
                hasResults: false,
                lastResults: [],
                lastTerm: "",
                lastPage: 1,
                lastMore: false,
                lastCacheKey: "",
                selectedId: String(cueSelect.value || "").trim(),
                openingWithCache: false,
                restoreLastTerm: false
            };
            var boundSearchField = null;
            var suppressClearOpen = false;
            var onSearchBeforeInput = function (event) {
                preventMatriculaNumericOverflow(event);
            };
            var onSearchInput = function (event) {
                var input = event.currentTarget;
                sanitizeMatriculaSearchInput(input);
                if (searchState.selectedId && String(input.value || "") !== searchState.selectedId) {
                    searchState.selectedId = "";
                }
            };
            $cueSelect.select2({
                width: "100%",
                allowClear: true,
                minimumInputLength: 0,
                minimumResultsForSearch: 0,
                placeholder: "Buscar CUE-Anexo...",
                dropdownParent: dropdownParent ? window.jQuery(dropdownParent) : undefined,
                dropdownCssClass: "cef-matricula-compartida-dropdown",
                templateResult: renderMatriculaResult,
                templateSelection: renderMatriculaSelection,
                ajax: {
                    url: cueSelect.dataset.autocompleteUrl,
                    dataType: "json",
                    delay: 250,
                    data: function (params) {
                        return {
                            q: normalizeMatriculaSearchTerm(params.term),
                            page: params.page || 1,
                            cueanexo: cueSelect.dataset.currentCue || ""
                        };
                    },
                    transport: function (options, success, failure) {
                        var term = normalizeMatriculaSearchTerm(options.data && options.data.q);
                        var page = parseInt(options.data && options.data.page, 10) || 1;
                        if (searchState.openingWithCache && searchState.hasResults && page === 1) {
                            term = searchState.lastTerm;
                        }
                        searchState.openingWithCache = false;
                        options.data = options.data || {};
                        options.data.q = term;
                        options.data.page = page;
                        var cacheKey = term + "|" + page;

                        if (searchState.hasResults && searchState.lastCacheKey === cacheKey) {
                            success({
                                results: searchState.lastResults.slice(),
                                pagination: { more: searchState.lastMore }
                            });
                            return { abort: function () {} };
                        }
                        searchState.hasResults = false;
                        searchState.lastResults = [];

                        var request = window.jQuery.ajax(options);
                        request.done(function (data) {
                            var results = data && Array.isArray(data.results) ? data.results.slice() : [];
                            searchState.lastTerm = term;
                            searchState.lastPage = page;
                            searchState.lastResults = results;
                            searchState.lastMore = Boolean(data && data.pagination && data.pagination.more);
                            searchState.lastCacheKey = cacheKey;
                            searchState.hasResults = true;
                            success({
                                results: results,
                                pagination: { more: searchState.lastMore }
                            });
                        });
                        request.fail(failure);
                        return request;
                    },
                    processResults: function (data) {
                        return {
                            results: Array.isArray(data.results) ? data.results : [],
                            pagination: data.pagination || { more: false }
                        };
                    }
                },
                language: {
                    noResults: function () { return "No se encontraron establecimientos"; },
                    errorLoading: function () { return "No se pudo consultar el padrón de establecimientos."; },
                    removeAllItems: function () { return "Limpiar selección"; },
                    searching: function () { return "Buscando..."; }
                }
            });
            $cueSelect.on("change.especialMatricula", function () {
                syncMatriculaAlta(editor);
            });
            $cueSelect.on("select2:select.especialMatricula", function (event) {
                var data = event.params && event.params.data;
                searchState.selectedId = data && data.id ? String(data.id).trim() : "";
                syncMatriculaAlta(editor);
            });
            $cueSelect.on("select2:clear.especialMatricula", function () {
                searchState.selectedId = "";
                syncMatriculaAlta(editor);
                var select2 = $cueSelect.data("select2");
                suppressClearOpen = !select2 || !select2.isOpen();
            });
            $cueSelect.on("select2:opening.especialMatricula", function (event) {
                if (suppressClearOpen) {
                    suppressClearOpen = false;
                    event.preventDefault();
                    return;
                }
                searchState.openingWithCache = searchState.hasResults;
                searchState.restoreLastTerm = searchState.hasResults || Boolean(searchState.selectedId);
            });
            $cueSelect.on("select2:open.especialMatricula", function () {
                var searchField = document.querySelector(".cef-matricula-compartida-dropdown .select2-search__field");
                if (!searchField) return;
                if (searchState.restoreLastTerm) {
                    searchField.value = searchState.selectedId || searchState.lastTerm;
                }
                searchField.setAttribute("placeholder", "Buscar...");
                sanitizeMatriculaSearchInput(searchField);
                if (boundSearchField !== searchField) {
                    if (boundSearchField) {
                        boundSearchField.removeEventListener("beforeinput", onSearchBeforeInput, true);
                        boundSearchField.removeEventListener("input", onSearchInput, true);
                    }
                    boundSearchField = searchField;
                    boundSearchField.addEventListener("beforeinput", onSearchBeforeInput, true);
                    boundSearchField.addEventListener("input", onSearchInput, true);
                }
                centerMatriculaDropdown(cueSelect);
                searchState.restoreLastTerm = false;
            });
            syncMatriculaAlta(editor);
        });
    }

    function checkReloadModals() {
        if (reloadChecked) return;
        reloadChecked = true;
        var entries = window.performance && window.performance.getEntriesByType
            ? window.performance.getEntriesByType("navigation") : [];
        if (!entries.length || entries[0].type !== "reload") return;
        var searchModal = document.getElementById("modalBusquedaAlumno");
        if (searchModal && searchModal.classList.contains("is-open")) closeSearchModal(searchModal);
        var bajaModal = document.getElementById("modalBajaAlumnoEspecial");
        if (!bajaModal || !bajaModal.classList.contains("is-open")) return;
        var url = new URL(window.location.href);
        if (!url.searchParams.has("abrir_modal_baja")) return;
        url.searchParams.delete("abrir_modal_baja");
        url.searchParams.delete("alumno_banco_id");
        bajaModal.classList.remove("is-open");
        bajaModal.setAttribute("aria-hidden", "true");
        bajaModal.removeAttribute("aria-busy");
        var body = bajaModal.querySelector(".cef-modal-body");
        if (body) body.replaceChildren();
        window.history.replaceState({}, "", url.toString());
    }

    function install() {
        if (installed) return;
        installed = true;
        installExpansion();
        document.addEventListener("click", function (event) {
            var toggle = event.target.closest("[data-cef-alumno-seccion-toggle]");
            if (!toggle) return;
            var table = toggle.closest("table[data-cef-alumnos-seccion-groups]");
            if (!table) return;
            if (table.dataset.cefAlumnoSectionReady !== "1") initAlumnoSectionTable(table);
            event.preventDefault();
            toggleAlumnoSection(table, toggle.closest("tr").dataset.cefAlumnoSeccionId);
        });
        document.addEventListener("click", function (event) {
            var opener = event.target.closest("[data-open-personas-modal]");
            if (opener && !event.defaultPrevented) {
                var searchModal = document.getElementById("modalBusquedaAlumno");
                if (searchModal) {
                    event.preventDefault();
                    openSearchModal(searchModal);
                }
                return;
            }
            var bajaTrigger = event.target.closest("[data-especial-baja-open]");
            if (bajaTrigger) {
                event.preventDefault();
                openBaja(bajaTrigger);
                return;
            }
            var closeTrigger = event.target.closest("[data-modal-close]");
            if (closeTrigger) {
                var modal = closeTrigger.closest(".cef-overlay");
                if (modal) {
                    event.preventDefault();
                    closeModal(modal);
                }
                return;
            }
            var overlay = event.target.closest(".cef-overlay");
            if (overlay && event.target === overlay) closeModal(overlay);
        });
        document.addEventListener("submit", submitModalForm);
        document.addEventListener("click", function (event) {
            var useLast = event.target.closest("[data-especial-matricula-use-last]");
            if (!useLast) return;
            var cell = useLast.closest("td");
            var select = cell && cell.querySelector("[data-especial-matricula-cue-select]");
            if (!select) return;
            event.preventDefault();
            var cue = String(useLast.dataset.cue || "").trim();
            var label = String(useLast.dataset.label || cue).trim();
            if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2 && window.jQuery(select).data("select2")) {
                window.jQuery(select).append(new Option(label, cue, true, true)).trigger("change");
            } else {
                select.value = cue;
                select.dispatchEvent(new Event("change", { bubbles: true }));
            }
        });
        document.addEventListener("change", function (event) {
            var cue = event.target.matches("[data-especial-matricula-cue-select]");
            if (!cue) return;
            var editor = event.target.closest("[data-especial-matricula-editor]");
            syncMatriculaAlta(editor || event.target);
        });
        document.addEventListener("focusin", function (event) {
            if (event.target.matches("[data-especial-matricula-cue-select]")) {
                initMatricula(event.target.closest("[data-especial-matricula-editor]"));
            }
        });
        var onWindowLoad = function () {
            initMatricula(document);
            checkReloadModals();
        };
        if (document.readyState === "complete") onWindowLoad();
        else window.addEventListener("load", onWindowLoad, { once: true });
    }

    function init(root) {
        initCuilInput(root);
        initMatricula(root);
        initAlumnoSectionTables(root);
    }

    function rootOwnsModal(root, modal) {
        if (!root || !modal) return false;
        return root === modal
            || (root.contains && root.contains(modal))
            || (modal.contains && modal.contains(root));
    }

    function destroy(root) {
        if (activeSearchRequest && rootOwnsModal(root, activeSearchRequest.modal)) cancelSearch();
        if (activeBajaRequest && rootOwnsModal(root, activeBajaRequest.modal)) cancelBaja();
        destroyMatriculaSelects(root);
    }

    window.EspecialAlumnos = { install: install, init: init, destroy: destroy };
})();
