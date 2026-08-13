(function () {
    "use strict";

    var installed = false;

    function helpers() {
        return window.EspecialBusquedaPersonas;
    }

    function openSearchModal(modal) {
        if (!modal) return;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        helpers().focusSearchInput(modal, "input[name='cuil']");
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        if (modal.dataset.volverUrl && window.history && window.history.replaceState) {
            window.history.replaceState({}, "", modal.dataset.volverUrl);
        }
    }

    function replaceSearchModal(modal, html, historyUrl) {
        return helpers().replaceModalDialog(modal, html, {
            dialogSelector: ".cef-docente-modal",
            historyUrl: historyUrl,
            focusSelector: "input[name='cuil']"
        });
    }

    function handleSearchJson(modal, data) {
        if (!data || typeof data !== "object") return false;
        var replaced = false;
        if (data.fragment_html) {
            replaced = Boolean(helpers().replaceFragment(data.fragment_selector, data.fragment_html));
        }
        if (data.modal_html) {
            replaced = replaceSearchModal(modal, data.modal_html, window.location.href) || replaced;
        }
        if (data.close_modal) closeModal(modal);
        return replaced;
    }

    function submitSearchModal(event) {
        var form = event.target.closest("[data-docente-modal-search-form], [data-docente-modal-post-form]");
        if (!form || event.defaultPrevented) return;
        var modal = form.closest("#modalBusquedaDocente");
        if (!modal) return;
        event.preventDefault();
        var method = (form.getAttribute("method") || "get").toLowerCase();
        var targetUrl = method === "get" ? helpers().buildFormUrl(form) : form.getAttribute("action");
        var submitButton = form.querySelector("button[type='submit']");
        if (submitButton) submitButton.disabled = true;
        var request = {
            credentials: "same-origin",
            headers: { "Accept": "text/html", "X-Requested-With": "XMLHttpRequest" }
        };
        if (method !== "get") {
            request.method = "POST";
            request.body = new FormData(form);
        }

        helpers().fetchRequest(targetUrl, request)
            .then(function (response) {
                return helpers().parseResponse(response, method === "get" ? "No se pudo buscar." : "No se pudo guardar.");
            })
            .then(function (result) {
                if (result.json) {
                    if (!handleSearchJson(modal, result.json)) HTMLFormElement.prototype.submit.call(form);
                    return;
                }
                if (result.redirected && helpers().replacePanel(result.html)) {
                    if (result.url && window.history && window.history.replaceState) {
                        window.history.replaceState({}, "", result.url);
                    }
                    closeModal(modal);
                    return;
                }
                var historyUrl = method === "get" ? targetUrl : window.location.href;
                if (!replaceSearchModal(modal, result.html, historyUrl)) {
                    if (method === "get") window.location.href = targetUrl;
                    else HTMLFormElement.prototype.submit.call(form);
                }
            })
            .catch(function () {
                if (method === "get") window.location.href = targetUrl;
                else HTMLFormElement.prototype.submit.call(form);
            })
            .finally(function () {
                if (submitButton) submitButton.disabled = false;
            });
    }

    function setValue(modal, selector, value) {
        var node = modal.querySelector(selector);
        if (node) node.value = value || "";
    }

    function setText(modal, selector, value) {
        var node = modal.querySelector(selector);
        if (node) node.textContent = value || "";
    }

    function closeAssignmentModal() {
        closeModal(document.getElementById("modalAsignarProfesorGrupo"));
    }

    function openAssignmentModal(trigger) {
        if (
            !trigger
            || trigger.classList.contains("disabled")
            || trigger.getAttribute("aria-disabled") === "true"
            || !trigger.dataset.grupoId
        ) return;
        var modal = document.getElementById("modalAsignarProfesorGrupo");
        if (!modal) return;
        if (window.EspecialDropdowns) window.EspecialDropdowns.closeAll();
        setValue(modal, "[data-cef-asignar-seccion-id]", trigger.dataset.grupoId);
        setValue(modal, "[data-cef-asignar-docente-cuil]", trigger.dataset.docenteCuil);
        setText(modal, "[data-cef-asignar-grupo-label]", trigger.dataset.grupoLabel);
        setText(
            modal,
            "[data-cef-asignar-docente-label]",
            (trigger.dataset.docenteNombre || "Profesor") + " - " + trigger.dataset.docenteCuil
        );
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
    }

    function replaceAssignmentModal(html) {
        var modal = document.getElementById("modalAsignarProfesorGrupo");
        return helpers().replaceModalDialog(modal, html, {
            dialogSelector: ".cef-docente-modal",
            focusSelector: null
        });
    }

    function submitAssignment(event) {
        var form = event.target.closest("[data-cef-asignar-grupo-form]");
        if (!form || event.defaultPrevented) return;
        event.preventDefault();
        var submitButton = form.querySelector("button[type='submit']");
        if (submitButton) submitButton.disabled = true;
        helpers().fetchRequest(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin"
        })
            .then(function (response) {
                if (!response.ok) throw new Error("No se pudo asignar el docente.");
                var contentType = response.headers.get("content-type") || "";
                if (contentType.indexOf("application/json") === -1) {
                    return response.text().then(function (html) {
                        return { fallbackHtml: html, redirected: response.redirected, url: response.url };
                    });
                }
                return response.json();
            })
            .then(function (data) {
                if (data && data.fallbackHtml) {
                    if (data.redirected && helpers().replacePanel(data.fallbackHtml)) {
                        closeAssignmentModal();
                        if (data.url) window.history.replaceState({}, "", data.url);
                        return;
                    }
                    HTMLFormElement.prototype.submit.call(form);
                    return;
                }
                if (data && data.fragment_html && data.fragment_selector) {
                    var target = helpers().replaceFragment(data.fragment_selector, data.fragment_html);
                    if (!target) {
                        HTMLFormElement.prototype.submit.call(form);
                        return;
                    }
                    if (data.close_modal) closeAssignmentModal();
                    else if (data.modal_html) replaceAssignmentModal(data.modal_html);
                    return;
                }
                if (data && data.modal_html && replaceAssignmentModal(data.modal_html)) return;
                HTMLFormElement.prototype.submit.call(form);
            })
            .catch(function () {
                HTMLFormElement.prototype.submit.call(form);
            })
            .finally(function () {
                if (submitButton) submitButton.disabled = false;
            });
    }

    function install() {
        if (installed) return;
        installed = true;
        document.addEventListener("click", function (event) {
            var opener = event.target.closest("[data-open-docentes-modal]");
            if (opener && !event.defaultPrevented) {
                var searchModal = document.getElementById("modalBusquedaDocente");
                if (searchModal) {
                    event.preventDefault();
                    openSearchModal(searchModal);
                }
                return;
            }
            var assignmentTrigger = event.target.closest("[data-cef-asignar-grupo-open]");
            if (assignmentTrigger) {
                event.preventDefault();
                openAssignmentModal(assignmentTrigger);
                return;
            }
            var closeSearch = event.target.closest("[data-docente-modal-close]");
            if (closeSearch) {
                var docenteModal = closeSearch.closest(".cef-docente-overlay");
                if (docenteModal) {
                    event.preventDefault();
                    closeModal(docenteModal);
                }
                return;
            }
            var closeAssignment = event.target.closest("[data-cef-asignar-grupo-close]");
            if (closeAssignment) {
                event.preventDefault();
                closeAssignmentModal();
                return;
            }
            var overlay = event.target.closest(".cef-docente-overlay");
            if (overlay && event.target === overlay) {
                if (overlay.id === "modalAsignarProfesorGrupo") closeAssignmentModal();
                else closeModal(overlay);
            }
        });
        document.addEventListener("submit", function (event) {
            if (event.target.closest("[data-cef-asignar-grupo-form]")) submitAssignment(event);
            else submitSearchModal(event);
        });
    }

    function init(root) {
        var scope = root && root.querySelector ? root : document;
        var modal = root && root.matches && root.matches("#modalBusquedaDocente")
            ? root : scope.querySelector("#modalBusquedaDocente");
        if (modal && modal.classList.contains("is-open")) {
            helpers().focusSearchInput(modal, "input[name='cuil']");
        }
    }

    window.EspecialDocentes = { install: install, init: init };
})();
