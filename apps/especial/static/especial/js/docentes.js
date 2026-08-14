(function () {
    "use strict";

    var installed = false;
    var activeBajaRequest = null;
    var previousBodyOverflow = null;

    function syncDocenteModalScroll() {
        var hasOpenModal = Boolean(document.querySelector(
            ".cef-docente-overlay.is-open, .cef-overlay.is-open"
        ));
        if (hasOpenModal && previousBodyOverflow === null) {
            previousBodyOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";
        } else if (!hasOpenModal && previousBodyOverflow !== null) {
            document.body.style.overflow = previousBodyOverflow;
            previousBodyOverflow = null;
        }
    }

    function helpers() {
        return window.EspecialBusquedaPersonas;
    }

    function openSearchModal(modal) {
        if (!modal) return;
        closeInteractiveModals();
        var input = modal.querySelector("input[name='cuil']");
        if (input && !input.value) {
            modal.querySelectorAll("[data-cef-modal-feedback], .cef-error").forEach(function (node) {
                node.remove();
            });
        }
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        syncDocenteModalScroll();
        helpers().focusSearchInput(modal, "input[name='cuil']");
    }

    function closeModal(modal) {
        if (!modal) return;
        if (modal.id === "modalBajaDocenteEspecial" && activeBajaRequest && activeBajaRequest.modal === modal) {
            activeBajaRequest.cancelled = true;
            activeBajaRequest.controller.abort();
            restoreBajaTrigger(activeBajaRequest.trigger);
            activeBajaRequest = null;
        }
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        modal.removeAttribute("aria-busy");
        syncDocenteModalScroll();
        if (modal.dataset.volverUrl && window.history && window.history.replaceState) {
            window.history.replaceState({}, "", modal.dataset.volverUrl);
        }
    }

    function focusDocenteBajaDestination() {
        var input = document.querySelector("#modalBajaDocenteEspecial [name='cueanexo_destino']");
        if (input) {
            input.focus();
            input.select();
        }
    }

    function closeDocenteBajaError() {
        var errorModal = document.getElementById("modalBajaDocenteEspecialError");
        if (!errorModal) return;
        closeModal(errorModal);
        focusDocenteBajaDestination();
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

    function openAssignmentsModal(trigger) {
        if (!trigger) return;
        var modal = document.getElementById(trigger.getAttribute("data-cef-asignaciones-modal-open"));
        if (!modal) return;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        syncDocenteModalScroll();
        var closeButton = modal.querySelector("[data-cef-asignaciones-modal-close]");
        if (closeButton) closeButton.focus();
    }

    function closeAssignmentsModal(modal) {
        closeModal(modal || document.querySelector(".cef-docente-overlay.is-open[data-cef-asignaciones-modal]"));
    }

    function closeOpenAssignmentsModal() {
        closeAssignmentsModal(document.querySelector(".cef-docente-overlay.is-open[data-cef-asignaciones-modal]"));
    }

    function closeInteractiveModals() {
        document.querySelectorAll(
            ".cef-docente-overlay.is-open, .cef-overlay.is-open"
        ).forEach(function (modal) {
            closeModal(modal);
        });
        syncDocenteModalScroll();
    }

    function syncDocenteBajaTransfer(modal) {
        if (!modal) return;
        var motivo = modal.querySelector("[name='motivo_baja']");
        var fields = modal.querySelector("[data-docente-traslado-fields]");
        if (fields) fields.hidden = !motivo || motivo.value !== "traslado";
    }

    function scheduleRoleNoChangeToast(modal) {
        var toast = modal && modal.querySelector("[data-cef-role-no-change]");
        if (!toast) return;
        window.setTimeout(function () {
            if (toast.isConnected) toast.remove();
        }, 5000);
    }

    function showRoleNoChangeToast(roleForm, roleSelect) {
        var modal = roleForm.closest("[data-cef-asignaciones-modal]");
        if (!modal) return;
        var oldToast = modal.querySelector("[data-cef-role-no-change]");
        if (oldToast) oldToast.remove();
        var toast = document.createElement("div");
        toast.className = "cef-role-no-change-toast";
        toast.setAttribute("role", "status");
        toast.setAttribute("data-cef-role-no-change", "");
        var icon = document.createElement("i");
        icon.className = "fa-solid fa-circle-info";
        icon.setAttribute("aria-hidden", "true");
        var text = document.createElement("span");
        var option = roleSelect.options[roleSelect.selectedIndex];
        text.textContent = "No se editó nada: el rol ya era "
            + (option ? option.textContent.trim() : "el rol actual") + ".";
        var close = document.createElement("button");
        close.type = "button";
        close.className = "cef-role-no-change-close";
        close.setAttribute("aria-label", "Cerrar");
        close.setAttribute("data-cef-role-no-change-close", "");
        close.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';
        toast.appendChild(icon);
        toast.appendChild(text);
        toast.appendChild(close);
        var dialog = modal.querySelector(".cef-docente-modal");
        if (dialog) dialog.appendChild(toast);
        scheduleRoleNoChangeToast(modal);
    }

    function restoreBajaTrigger(trigger) {
        if (!trigger || !trigger.isConnected) return;
        trigger.removeAttribute("aria-disabled");
        trigger.removeAttribute("data-docente-baja-loading");
        trigger.classList.remove("disabled");
    }

    function showDocenteBajaLoading(modal) {
        var body = modal && modal.querySelector("[data-docente-baja-content]");
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
        syncDocenteModalScroll();
        return true;
    }

    function showDocenteBajaError(modal, message) {
        var body = modal && modal.querySelector("[data-docente-baja-content]");
        if (!body) return;
        body.replaceChildren();
        var alert = document.createElement("div");
        alert.className = "alert alert-danger mb-0";
        alert.setAttribute("role", "alert");
        alert.textContent = message || "No se pudo cargar la baja del docente.";
        body.appendChild(alert);
        modal.removeAttribute("aria-busy");
    }

    function openDocenteBaja(trigger) {
        if (!trigger || activeBajaRequest) return;
        if (window.EspecialDropdowns && typeof window.EspecialDropdowns.closeForElement === "function") {
            window.EspecialDropdowns.closeForElement(trigger);
        }
        var modal = document.getElementById("modalBajaDocenteEspecial");
        var url = new URL(trigger.href, window.location.href);
        if (!modal || url.origin !== window.location.origin) {
            window.location.href = url.toString();
            return;
        }
        closeInteractiveModals();
        if (!showDocenteBajaLoading(modal)) return;
        trigger.setAttribute("aria-disabled", "true");
        trigger.setAttribute("data-docente-baja-loading", "true");
        trigger.classList.add("disabled");
        var operation = {
            cancelled: false,
            controller: new AbortController(),
            modal: modal,
            trigger: trigger,
            url: url.toString()
        };
        activeBajaRequest = operation;
        fetch(operation.url, {
            credentials: "same-origin",
            signal: operation.controller.signal,
            headers: { "Accept": "text/html", "X-Requested-With": "XMLHttpRequest" }
        })
            .then(function (response) {
                return response.text().then(function (body) {
                    if (!response.ok) {
                        var httpError = new Error("No se pudo cargar la baja del docente.");
                        httpError.status = response.status;
                        httpError.body = body;
                        throw httpError;
                    }
                    return body;
                });
            })
            .then(function (html) {
                if (operation.cancelled || activeBajaRequest !== operation) return;
                if (!html || !html.trim()) throw new Error("La respuesta de baja llegó vacía.");
                var parsed = new DOMParser().parseFromString(html, "text/html");
                var nextModal = parsed.querySelector("#modalBajaDocenteEspecial");
                if (!nextModal) throw new Error("La respuesta no contiene el modal de baja.");
                if (!nextModal.querySelector("[data-docente-baja-content]")) {
                    throw new Error("La respuesta de baja no contiene el cuerpo del modal.");
                }
                modal.replaceWith(nextModal);
                modal = nextModal;
                operation.modal = modal;
                modal.classList.add("is-open");
                modal.setAttribute("aria-hidden", "false");
                modal.removeAttribute("aria-busy");
                syncDocenteBajaTransfer(modal);
            })
            .catch(function (error) {
                if (operation.cancelled || activeBajaRequest !== operation) return;
                activeBajaRequest = null;
                if (error && error.name === "AbortError") return;
                console.error("No se pudo cargar la baja del docente.", error);
                showDocenteBajaError(modal, "No se pudieron cargar los datos del docente.");
                restoreBajaTrigger(operation.trigger);
            })
            .finally(function () {
                if (activeBajaRequest !== operation) return;
                activeBajaRequest = null;
                modal.removeAttribute("aria-busy");
                restoreBajaTrigger(operation.trigger);
            });
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
        closeOpenAssignmentsModal();
        if (window.EspecialDropdowns) window.EspecialDropdowns.closeAll();
        var form = modal.querySelector("[data-cef-asignar-grupo-form]");
        if (form) {
            form.reset();
            var roleField = form.querySelector("[name='rol']");
            if (roleField) {
                if (!roleField.querySelector("option[value='']")) {
                    var emptyRole = document.createElement("option");
                    emptyRole.value = "";
                    emptyRole.textContent = "---------";
                    roleField.insertBefore(emptyRole, roleField.firstChild);
                }
                roleField.value = "";
            }
        }
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
            var bajaOpener = event.target.closest("[data-docente-baja-open]");
            if (bajaOpener) {
                event.preventDefault();
                openDocenteBaja(bajaOpener);
                return;
            }
            var opener = event.target.closest("[data-open-docentes-modal]");
            if (opener && !event.defaultPrevented) {
                var searchModal = document.getElementById("modalBusquedaDocente");
                if (searchModal) {
                    event.preventDefault();
                    closeInteractiveModals();
                    if (window.EspecialDropdowns) window.EspecialDropdowns.closeAll();
                    openSearchModal(searchModal);
                }
                return;
            }
            var assignmentsOpener = event.target.closest("[data-cef-asignaciones-modal-open]");
            if (assignmentsOpener) {
                event.preventDefault();
                closeAssignmentModal();
                if (window.EspecialDropdowns) window.EspecialDropdowns.closeAll();
                var assignmentsModal = document.getElementById(assignmentsOpener.getAttribute("data-cef-asignaciones-modal-open"));
                if (assignmentsModal && assignmentsModal.classList.contains("is-open")) {
                    closeAssignmentsModal(assignmentsModal);
                    return;
                }
                openAssignmentsModal(assignmentsOpener);
                return;
            }
            var sectionsToggle = event.target.closest("[data-cef-secciones-toggle]");
            if (sectionsToggle) {
                event.preventDefault();
                var sectionsWrap = sectionsToggle.closest(".docentes-secciones-wrap");
                var sectionsList = sectionsWrap && sectionsWrap.querySelector(".docentes-secciones-list");
                if (!sectionsList) return;
                var collapsed = sectionsList.classList.toggle("is-collapsed");
                sectionsToggle.textContent = collapsed
                    ? sectionsToggle.getAttribute("data-more-label")
                    : "Mostrar menos";
                return;
            }
            var assignmentTrigger = event.target.closest("[data-cef-asignar-grupo-open]");
            if (assignmentTrigger) {
                event.preventDefault();
                openAssignmentModal(assignmentTrigger);
                return;
            }
            var closeAssignments = event.target.closest("[data-cef-asignaciones-modal-close]");
            if (closeAssignments) {
                event.preventDefault();
                closeAssignmentsModal(closeAssignments.closest(".cef-docente-overlay"));
                return;
            }
            var closeDocenteBaja = event.target.closest("[data-docente-baja-modal-close]");
            if (closeDocenteBaja) {
                event.preventDefault();
                closeModal(closeDocenteBaja.closest("#modalBajaDocenteEspecial"));
                return;
            }
            var closeDocenteBajaErrorButton = event.target.closest("[data-docente-baja-error-close]");
            if (closeDocenteBajaErrorButton) {
                event.preventDefault();
                closeDocenteBajaError();
                return;
            }
            var closeRoleNoChange = event.target.closest("[data-cef-role-no-change-close]");
            if (closeRoleNoChange) {
                event.preventDefault();
                var roleToast = closeRoleNoChange.closest("[data-cef-role-no-change]");
                if (roleToast) roleToast.remove();
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
                return;
            }
            var bajaOverlay = event.target.closest("#modalBajaDocenteEspecial");
            if (bajaOverlay && event.target === bajaOverlay) {
                closeModal(bajaOverlay);
                return;
            }
            var bajaErrorOverlay = event.target.closest("#modalBajaDocenteEspecialError");
            if (bajaErrorOverlay && event.target === bajaErrorOverlay) {
                closeDocenteBajaError();
            }
        });
        document.addEventListener("submit", function (event) {
            var roleForm = event.target.closest("[data-cef-asignacion-role-form]");
            if (roleForm) {
                var roleSelect = roleForm.querySelector("[name='rol']");
                if (roleSelect && roleSelect.value === roleSelect.getAttribute("data-rol-original")) {
                    event.preventDefault();
                    showRoleNoChangeToast(roleForm, roleSelect);
                    return;
                }
            }
            if (event.target.closest("[data-cef-asignar-grupo-form]")) submitAssignment(event);
            else submitSearchModal(event);
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" || event.key === "Esc") {
                var bajaErrorModal = document.getElementById("modalBajaDocenteEspecialError");
                if (bajaErrorModal && bajaErrorModal.classList.contains("is-open")) {
                    closeDocenteBajaError();
                    return;
                }
                closeInteractiveModals();
                if (window.EspecialDropdowns) window.EspecialDropdowns.closeAll();
            }
        });
        document.addEventListener("change", function (event) {
            if (!event.target.matches("#modalBajaDocenteEspecial [name='motivo_baja']")) return;
            syncDocenteBajaTransfer(event.target.closest("#modalBajaDocenteEspecial"));
        });
        document.addEventListener("input", function (event) {
            if (!event.target.matches("#modalBajaDocenteEspecial [name='cueanexo_destino']")) return;
            event.target.value = event.target.value.replace(/[^0-9]/g, "").slice(0, 9);
        });
        document.addEventListener("paste", function (event) {
            if (!event.target.matches("#modalBajaDocenteEspecial [name='cueanexo_destino']")) return;
            event.preventDefault();
            var pasted = (event.clipboardData || window.clipboardData).getData("text");
            var numeric = pasted.replace(/[^0-9]/g, "").slice(0, 9);
            var input = event.target;
            var start = input.selectionStart;
            var end = input.selectionEnd;
            input.value = (input.value.slice(0, start) + numeric + input.value.slice(end)).slice(0, 9);
            input.dispatchEvent(new Event("input", { bubbles: true }));
        });
    }

    function init(root) {
        var scope = root && root.querySelector ? root : document;
        syncDocenteModalScroll();
        var modal = root && root.matches && root.matches("#modalBusquedaDocente")
            ? root : scope.querySelector("#modalBusquedaDocente");
        if (modal && modal.classList.contains("is-open")) {
            helpers().focusSearchInput(modal, "input[name='cuil']");
        }
        var bajaModal = scope.querySelector("#modalBajaDocenteEspecial");
        if (bajaModal && bajaModal.classList.contains("is-open")) {
            syncDocenteBajaTransfer(bajaModal);
        }
        var bajaErrorModal = scope.querySelector("#modalBajaDocenteEspecialError.is-open");
        if (bajaErrorModal) {
            var errorClose = bajaErrorModal.querySelector("[data-docente-baja-error-close]");
            if (errorClose) errorClose.focus();
        }
        scheduleRoleNoChangeToast(scope.querySelector("[data-cef-asignaciones-modal].is-open"));
    }

    window.EspecialDocentes = {
        install: install,
        init: init,
        closeModalsForDropdown: closeInteractiveModals
    };
})();
