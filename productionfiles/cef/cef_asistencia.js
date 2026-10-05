(function () {
    "use strict";

    var loadingDelay = 200;
    var currentRequest = null;
    var requestVersion = 0;

    function workspace() {
        return document.querySelector("[data-cef-asistencia-workspace]");
    }

    function hasUnsavedChanges() {
        var target = workspace();
        return Boolean(target && target.dataset.cefAsistenciaDirty === "true");
    }

    function confirmNavigation() {
        return !hasUnsavedChanges() || window.confirm(
            "Hay cambios de asistencia sin guardar. ¿Querés cambiar de fecha igualmente?"
        );
    }

    function showLoading(target) {
        if (!target) return;
        var currentHeight = Math.ceil(target.getBoundingClientRect().height);
        if (window.CEFSelects) window.CEFSelects.destroy(target);
        var loading = document.createElement("div");
        var spinner = document.createElement("span");
        var label = document.createElement("span");
        loading.className = "cef-inline-loading cef-partial-loading";
        loading.setAttribute("role", "status");
        loading.setAttribute("aria-live", "polite");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("aria-hidden", "true");
        label.textContent = "Cargando asistencia...";
        loading.appendChild(spinner);
        loading.appendChild(label);
        if (currentHeight > 144) loading.style.minHeight = currentHeight + "px";
        target.replaceChildren(loading);
        target.setAttribute("aria-busy", "true");
    }

    function runInitializers(target) {
        if (typeof window.initCefSelects === "function") {
            window.initCefSelects(target);
        }
        if (typeof window.initCefTables === "function") {
            window.initCefTables(target);
        }
        updateProgress(target);
    }

    function loadDate(targetUrl) {
        var target = workspace();
        if (!target) {
            window.location.assign(targetUrl);
            return;
        }

        if (currentRequest) currentRequest.abort();
        currentRequest = new AbortController();
        requestVersion += 1;
        var version = requestVersion;
        var loadingTimer = window.setTimeout(function () {
            if (version === requestVersion) showLoading(target);
        }, loadingDelay);

        fetch(targetUrl, {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "X-Cef-Asistencia-Fragment": "workspace",
                "X-Requested-With": "XMLHttpRequest"
            },
            signal: currentRequest.signal,
            cache: "no-store"
        })
            .then(function (response) {
                if (!response.ok || response.headers.get("X-Cef-Asistencia-Fragment") !== "workspace") {
                    throw new Error("Respuesta parcial inválida");
                }
                return response.text();
            })
            .then(function (html) {
                if (version !== requestVersion) return;
                window.clearTimeout(loadingTimer);
                target.innerHTML = html;
                target.removeAttribute("aria-busy");
                target.dataset.cefAsistenciaDirty = "false";
                runInitializers(target);
                window.history.replaceState(window.history.state, "", targetUrl);
            })
            .catch(function (error) {
                window.clearTimeout(loadingTimer);
                if (error.name === "AbortError") return;
                window.location.assign(targetUrl);
            });
    }

    function formUrl(form) {
        var url = new URL(form.action, window.location.href);
        new FormData(form).forEach(function (value, key) {
            if (value !== "") url.searchParams.set(key, value);
        });
        return url.toString();
    }

    function showTab(name, moveFocus) {
        var target = workspace();
        if (!target) return;
        target.querySelectorAll("[data-cef-asistencia-tab]").forEach(function (tab) {
            var selected = tab.dataset.cefAsistenciaTab === name;
            tab.setAttribute("aria-selected", selected ? "true" : "false");
            tab.tabIndex = selected ? 0 : -1;
            if (selected && moveFocus) tab.focus();
        });
        target.querySelectorAll("[data-cef-asistencia-panel]").forEach(function (panel) {
            panel.hidden = panel.dataset.cefAsistenciaPanel !== name;
        });
    }

    function updateProgress(root) {
        var target = root || workspace();
        if (!target) return;
        var progress = target.querySelector("[data-cef-asistencia-progress]");
        var selects = target.querySelectorAll("[data-cef-asistencia-guardado] select[name^='asistencia_']");
        if (!progress || !selects.length) return;
        var selected = Array.prototype.filter.call(selects, function (select) {
            return Boolean(select.value);
        }).length;
        var pending = selects.length - selected;
        var form = target.querySelector("[data-cef-asistencia-guardado]");
        var validationAttempted = Boolean(
            form && form.dataset.cefAsistenciaValidationAttempted === "true"
        );
        progress.classList.toggle("is-complete", pending === 0);
        progress.classList.toggle("has-missing", validationAttempted && pending > 0);
        progress.textContent = pending === 0
            ? "Todo listo para guardar."
            : "Falta seleccionar " + pending + " alumno" + (pending === 1 ? "." : "s.");
    }

    function syncMissingAttendance(select, force) {
        if (!select) return;
        var missing = !select.value && force;
        select.classList.toggle("cef-asistencia-select-missing", missing);
        select.setAttribute("aria-invalid", missing ? "true" : "false");
        var cell = select.closest("td");
        if (cell) cell.classList.toggle("cef-asistencia-missing", missing);
    }

    function validateMissingAttendances(form) {
        if (!form) return;
        form.dataset.cefAsistenciaValidationAttempted = "true";
        form.querySelectorAll("select[name^='asistencia_']").forEach(function (select) {
            syncMissingAttendance(select, !select.value);
        });
        updateProgress(workspace());
    }

    document.addEventListener("invalid", function (event) {
        if (!event.target.matches("[data-cef-asistencia-guardado] select[name^='asistencia_']")) {
            return;
        }
        var form = event.target.form;
        validateMissingAttendances(form);
    }, true);

    document.addEventListener("submit", function (event) {
        var dateForm = event.target.closest("[data-cef-asistencia-fecha]");
        if (dateForm) {
            event.preventDefault();
            if (!dateForm.reportValidity() || !confirmNavigation()) return;
            loadDate(formUrl(dateForm));
            return;
        }

        if (event.target.matches("[data-cef-asistencia-guardado]")) {
            var target = workspace();
            if (target) target.dataset.cefAsistenciaDirty = "false";
        }
    });

    document.addEventListener("change", function (event) {
        if (event.target.matches("[data-cef-asistencia-guardado] select[name^='asistencia_']")) {
            var target = workspace();
            var form = event.target.form;
            var validationAttempted = Boolean(
                form && form.dataset.cefAsistenciaValidationAttempted === "true"
            );
            syncMissingAttendance(event.target, validationAttempted);
            if (target) target.dataset.cefAsistenciaDirty = "true";
            updateProgress(target);
        }
    });

    document.addEventListener("keydown", function (event) {
        var tab = event.target.closest("[data-cef-asistencia-tab]");
        if (!tab || (event.key !== "ArrowLeft" && event.key !== "ArrowRight")) return;
        var tabs = Array.prototype.slice.call(tab.parentElement.querySelectorAll("[data-cef-asistencia-tab]"));
        var currentIndex = tabs.indexOf(tab);
        var nextIndex = event.key === "ArrowRight"
            ? (currentIndex + 1) % tabs.length
            : (currentIndex - 1 + tabs.length) % tabs.length;
        event.preventDefault();
        showTab(tabs[nextIndex].dataset.cefAsistenciaTab, true);
    });

    document.addEventListener("click", function (event) {
        var tab = event.target.closest("[data-cef-asistencia-tab]");
        if (tab) {
            showTab(tab.dataset.cefAsistenciaTab);
            return;
        }

        var dateToggle = event.target.closest("[data-cef-asistencia-fecha-toggle]");
        if (dateToggle) {
            var dateWorkspace = workspace();
            var dateEdit = dateWorkspace
                ? dateWorkspace.querySelector("[data-cef-asistencia-fecha-edit]")
                : null;
            if (!dateEdit) return;
            var willOpen = dateEdit.hidden;
            dateEdit.hidden = !willOpen;
            dateToggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
            if (willOpen) {
                var dateInput = dateEdit.querySelector("input[name='fecha']");
                if (dateInput) dateInput.focus();
            }
            return;
        }

        var auditToggle = event.target.closest("[data-cef-asistencia-audit-toggle]");
        if (auditToggle) {
            var auditWorkspace = workspace();
            var auditPanel = auditWorkspace
                ? auditWorkspace.querySelector("[data-cef-asistencia-audit-panel]")
                : null;
            if (!auditPanel) return;
            var openingAudit = auditPanel.hidden;
            auditPanel.hidden = !openingAudit;
            auditToggle.setAttribute("aria-expanded", openingAudit ? "true" : "false");
            var auditLabel = auditToggle.querySelector("[data-cef-asistencia-audit-label]");
            if (auditLabel) {
                auditLabel.textContent = openingAudit
                    ? "Ocultar historial de modificaciones"
                    : "Ver historial de modificaciones";
            }
            return;
        }

        var dateLink = event.target.closest("[data-cef-asistencia-fecha-link]");
        if (!dateLink || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        event.preventDefault();
        if (!confirmNavigation()) return;
        loadDate(dateLink.href);
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            updateProgress(document);
        });
    } else {
        updateProgress(document);
    }
})();
