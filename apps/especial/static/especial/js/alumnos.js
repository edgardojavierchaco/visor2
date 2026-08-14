(function () {
    "use strict";

    var installed = false;
    var reloadChecked = false;
    var activeSearchRequest = null;
    var activeBajaRequest = null;

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

    function handleAlumnoJson(modal, data) {
        if (!data || typeof data !== "object") return false;
        var replaced = false;
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
        return replaced;
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
                    if (!handleAlumnoJson(modal, result.json)) HTMLFormElement.prototype.submit.call(form);
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
                    HTMLFormElement.prototype.submit.call(form);
                }
            })
            .catch(function (error) {
                if (
                    isSearch
                    && (operation.cancelled || activeSearchRequest !== operation || (error && error.name === "AbortError"))
                ) return;
                HTMLFormElement.prototype.submit.call(form);
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

    function updateMatriculaSave(editor) {
        if (!editor) return;
        var form = editor.querySelector("[data-especial-matricula-update-form]");
        var saveButton = form && form.querySelector("[data-especial-matricula-save]");
        if (!form || !saveButton) return;
        var cueSelect = form.querySelector("[data-especial-matricula-cue-select]");
        var currentCue = cueSelect ? String(cueSelect.value || "").trim() : "";
        var initialCue = String(form.dataset.initialCue || "").trim();
        saveButton.hidden = currentCue === initialCue;
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
            var row = button.closest("tr");
            var cueSelect = row && row.querySelector("[data-especial-matricula-cue-select]");
            if (!cueSelect) return;
            button.disabled = !String(cueSelect.value || "").trim();
        });
    }

    function initMatricula(root) {
        var editors = matriculaEditors(root);
        editors.forEach(function (editor) {
            updateMatriculaSave(editor);
        });
        syncMatriculaAlta(root);
        if (!window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
        editors.forEach(function (editor) {
            var cueSelect = editor.querySelector("[data-especial-matricula-cue-select]");
            if (!cueSelect) return;
            var $cueSelect = window.jQuery(cueSelect);
            if ($cueSelect.data("select2")) return;
            var dropdownParent = cueSelect.closest(".cef-modal");
            $cueSelect.select2({
                width: "100%",
                allowClear: false,
                minimumInputLength: 0,
                minimumResultsForSearch: 0,
                placeholder: "Buscar CUE-Anexo o establecimiento",
                dropdownParent: dropdownParent ? window.jQuery(dropdownParent) : undefined,
                dropdownCssClass: "cef-matricula-compartida-dropdown",
                ajax: {
                    url: cueSelect.dataset.autocompleteUrl,
                    dataType: "json",
                    delay: 250,
                    data: function (params) {
                        return { q: params.term || "", cueanexo: cueSelect.dataset.currentCue || "" };
                    },
                    processResults: function (data) {
                        return { results: Array.isArray(data.results) ? data.results : [] };
                    }
                },
                language: {
                    noResults: function () { return "No se encontraron CUE-Anexos."; },
                    searching: function () { return "Buscando..."; }
                }
            });
            $cueSelect.on("change.especialMatricula", function () {
                updateMatriculaSave(editor);
                syncMatriculaAlta(editor);
            });
            $cueSelect.on("select2:open.especialMatricula", function () {
                var searchField = document.querySelector(".select2-container--open .select2-search__field");
                if (searchField) searchField.setAttribute("placeholder", "Buscar...");
            });
            updateMatriculaSave(editor);
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
        document.addEventListener("change", function (event) {
            var cue = event.target.matches("[data-especial-matricula-cue-select]");
            if (!cue) return;
            var editor = event.target.closest("[data-especial-matricula-editor]");
            updateMatriculaSave(editor);
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
