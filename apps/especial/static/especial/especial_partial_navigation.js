(function () {
    "use strict";

    var SECTION_LINK_SELECTOR = "[data-especial-section-link]";
    var REGION_SELECTOR = "[data-especial-content-region]";
    var SUPPORTED_SECTIONS = ["alumnos", "docentes", "cueanexo", "secciones", "ciclos"];
    var requestSequence = 0;
    var activeRequest = null;

    function isSupportedSection(section) {
        return SUPPORTED_SECTIONS.indexOf(section) !== -1;
    }

    function findRegion(root) {
        if (!root) return null;
        if (root.matches && root.matches(REGION_SELECTOR)) return root;
        return root.querySelector ? root.querySelector(REGION_SELECTOR) : null;
    }

    function compatibleShell() {
        var region = findRegion(document);
        var nav = document.querySelector("nav.cef-module-nav");
        var contextForm = document.querySelector("[data-especial-context-selector]");
        var header = document.querySelector("[data-especial-shell-header]");
        return Boolean(
            region
            && nav
            && contextForm
            && contextForm.querySelector("#id_contexto_cueanexo")
            && contextForm.querySelector("#id_contexto_ciclo")
            && header
            && header.querySelector(".especial-module-hero h1")
            && header.querySelector(".especial-module-hero p")
        );
    }

    function findSectionForUrl(url) {
        var links = document.querySelectorAll(SECTION_LINK_SELECTOR);
        for (var i = 0; i < links.length; i += 1) {
            var linkUrl = new URL(links[i].href, window.location.href);
            if (linkUrl.origin === url.origin && linkUrl.pathname === url.pathname) {
                return links[i].dataset.especialSection;
            }
        }
        return "";
    }

    function isModifiedClick(event) {
        return event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;
    }

    function setLoading(region) {
        region.setAttribute("aria-busy", "true");
        region.replaceChildren();

        var status = document.createElement("div");
        status.className = "especial-partial-loading";
        status.setAttribute("role", "status");
        status.setAttribute("aria-live", "polite");

        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("aria-hidden", "true");
        status.appendChild(spinner);
        status.appendChild(document.createTextNode("Cargando..."));
        region.appendChild(status);
    }

    function setReady(region) {
        region.setAttribute("aria-busy", "false");
    }

    function updateNavbar(section) {
        var nav = document.querySelector("nav.cef-module-nav");
        if (!nav) return;
        nav.querySelectorAll(".nav-link").forEach(function (link) {
            link.classList.remove("active");
            link.removeAttribute("aria-current");
        });
        var activeLink = nav.querySelector(SECTION_LINK_SELECTOR + "[data-especial-section='" + section + "']");
        if (activeLink) {
            activeLink.classList.add("active");
            activeLink.setAttribute("aria-current", "page");
        }
    }

    function updateHeader(region) {
        var title = region.dataset.especialTitle || "";
        var subtitle = region.dataset.especialSubtitle || "";
        var titleNode = document.querySelector(".especial-module-hero h1");
        var subtitleNode = document.querySelector(".especial-module-hero p");

        if (titleNode && title) titleNode.textContent = title;
        if (subtitleNode && subtitle) subtitleNode.textContent = subtitle;
        if (title) document.title = title;
    }

    function invokeTableInitializers(root) {
        var initializers = [
            "initCefAlumnosTable",
            "initCefProfesoresTable",
            "initCefInscripcionTable",
            "initCefDocentesGrupoTable"
        ];
        initializers.forEach(function (name) {
            if (typeof window[name] === "function") window[name](root);
        });
    }

    function buildFormUrl(form) {
        var url = new URL(form.getAttribute("action"), window.location.href);
        new FormData(form).forEach(function (value, key) {
            url.searchParams.set(key, value);
        });
        return url.toString();
    }

    function replaceModalDialog(modal, html, url) {
        var responseDocument = new DOMParser().parseFromString(html, "text/html");
        var incomingModal = responseDocument.getElementById(modal.id);
        var currentDialog = modal.querySelector(".cef-modal, .cef-docente-modal");
        var incomingDialog = incomingModal ? incomingModal.querySelector(".cef-modal, .cef-docente-modal") : null;
        if (!currentDialog || !incomingDialog) return false;
        var nodes = [];
        incomingDialog.childNodes.forEach(function (node) {
            if (node.nodeType === 1 && node.tagName === "SCRIPT") return;
            nodes.push(document.importNode(node, true));
        });
        currentDialog.replaceChildren.apply(currentDialog, nodes);
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        if (url) window.history.replaceState({}, "", url);
        var input = modal.querySelector("input[name='cuil']");
        if (input) input.focus();
        return true;
    }

    function replaceFragmentContent(selector, html) {
        var current = selector ? document.querySelector(selector) : null;
        if (!current || typeof html !== "string") return false;
        var template = document.createElement("template");
        template.innerHTML = html;
        template.content.querySelectorAll("script").forEach(function (script) { script.remove(); });
        current.replaceChildren(template.content.cloneNode(true));
        invokeTableInitializers(current);
        return true;
    }

    function replacePanelFromHtml(html) {
        var responseDocument = new DOMParser().parseFromString(html, "text/html");
        var incomingPanel = responseDocument.querySelector(".cef-panel");
        var currentPanel = document.querySelector(".cef-panel");
        if (!incomingPanel || !currentPanel) return false;
        currentPanel.replaceWith(document.importNode(incomingPanel, true));
        invokeTableInitializers(document);
        return true;
    }

    function handleModalJson(modal, data) {
        if (!data || typeof data !== "object") return false;
        var replaced = false;
        if (data.fragment_html) {
            replaced = replaceFragmentContent(data.fragment_selector, data.fragment_html);
        }
        if (data.modal_html) {
            replaced = replaceModalDialog(modal, data.modal_html, window.location.href) || replaced;
        }
        if (data.close_modal) {
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
        }
        return replaced;
    }

    function installModalForms() {
        if (window.especialModalFormsReady) return;
        window.especialModalFormsReady = true;

        document.addEventListener("submit", function (event) {
            var form = event.target.closest(
                "[data-modal-search-form], [data-docente-modal-search-form], "
                + "[data-modal-post-form], [data-docente-modal-post-form], "
                + "[data-especial-baja-form]"
            );
            if (!form) return;
            var modal = form.closest("#modalBusquedaAlumno, #modalBusquedaDocente, #modalBajaAlumnoEspecial");
            if (!modal) return;

            event.preventDefault();
            var method = (form.getAttribute("method") || "get").toLowerCase();
            var submitButton = form.querySelector("button[type='submit']");
            if (submitButton) submitButton.disabled = true;
            var request = {
                credentials: "same-origin",
                headers: {
                    "Accept": "text/html",
                    "X-Requested-With": "XMLHttpRequest"
                }
            };
            var targetUrl = form.getAttribute("action");
            if (method === "get") {
                targetUrl = buildFormUrl(form);
            } else {
                request.method = "POST";
                request.body = new FormData(form);
            }

            fetch(targetUrl, request)
                .then(function (response) {
                    if (!response.ok) throw new Error("La operacion del modal devolvio un error HTTP.");
                    var contentType = response.headers.get("content-type") || "";
                    if (contentType.indexOf("application/json") !== -1) {
                        return response.json().then(function (data) {
                            return { json: data };
                        });
                    }
                    return response.text().then(function (html) {
                        return { html: html, redirected: response.redirected, url: response.url };
                    });
                })
                .then(function (result) {
                    if (result.json) {
                        if (!handleModalJson(modal, result.json)) {
                            HTMLFormElement.prototype.submit.call(form);
                        }
                        return;
                    }
                    if (result.redirected && replacePanelFromHtml(result.html)) {
                        modal.classList.remove("is-open");
                        modal.setAttribute("aria-hidden", "true");
                        if (result.url) window.history.replaceState({}, "", result.url);
                        return;
                    }
                    if (!replaceModalDialog(modal, result.html, method === "get" ? targetUrl : window.location.href)) {
                        HTMLFormElement.prototype.submit.call(form);
                    }
                })
                .catch(function () {
                    HTMLFormElement.prototype.submit.call(form);
                })
                .finally(function () {
                    if (submitButton) submitButton.disabled = false;
                });
        });
    }

    function installDropdown(config) {
        if (window[config.readyFlag]) return;
        window[config.readyFlag] = true;

        function closeDropdown(dropdown) {
            if (!dropdown) return;
            var toggle = dropdown.querySelector(config.toggleSelector);
            var menu = dropdown.querySelector(config.menuSelector);
            if (toggle) toggle.setAttribute("aria-expanded", "false");
            if (menu) {
                menu.classList.remove("show");
                menu.removeAttribute("style");
            }
        }

        function closeOtherDropdowns(current) {
            document.querySelectorAll(config.dropdownSelector).forEach(function (dropdown) {
                if (dropdown !== current) closeDropdown(dropdown);
            });
        }

        function positionMenu(toggle, menu) {
            var rect = toggle.getBoundingClientRect();
            var tableWrap = toggle.closest(".cef-table-wrap");
            var bounds = tableWrap ? tableWrap.getBoundingClientRect() : {
                left: 12,
                right: window.innerWidth - 12
            };
            var menuWidth = config.menuWidth;
            var left = Math.min(rect.left, bounds.right - menuWidth - 8);
            menu.style.position = "fixed";
            menu.style.top = (rect.bottom + 4) + "px";
            menu.style.left = Math.max(bounds.left + 8, left) + "px";
            menu.style.width = menuWidth + "px";
            menu.style.zIndex = "1090";
        }

        document.addEventListener("click", function (event) {
            var toggle = event.target.closest(config.toggleSelector);
            if (toggle) {
                event.preventDefault();
                var dropdown = toggle.closest(config.dropdownSelector);
                var menu = dropdown ? dropdown.querySelector(config.menuSelector) : null;
                if (!dropdown || !menu) return;

                var willOpen = !menu.classList.contains("show");
                closeOtherDropdowns(dropdown);
                toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
                menu.classList.toggle("show", willOpen);
                if (willOpen) positionMenu(toggle, menu);
                else menu.removeAttribute("style");
                return;
            }

            if (!event.target.closest(config.menuSelector)) closeOtherDropdowns(null);
        });

        window.addEventListener("scroll", function () { closeOtherDropdowns(null); }, true);
        window.addEventListener("resize", function () { closeOtherDropdowns(null); });
    }

    function installModalTriggers() {
        if (window.especialModalTriggersReady) return;
        window.especialModalTriggersReady = true;
        var bajaOpeningRequest = null;

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

        function cancelBajaOpening(modal) {
            if (!bajaOpeningRequest || bajaOpeningRequest.modal !== modal) return;
            var operation = bajaOpeningRequest;
            operation.cancelled = true;
            operation.controller.abort();
            bajaOpeningRequest = null;
            clearBajaLoading(modal);
        }

        document.addEventListener("click", function (event) {
            var openTrigger = event.target.closest("[data-open-personas-modal], [data-open-docentes-modal]");
            if (openTrigger) {
                var modalId = openTrigger.hasAttribute("data-open-personas-modal")
                    ? "modalBusquedaAlumno"
                    : "modalBusquedaDocente";
                var modal = document.getElementById(modalId);
                if (modal) {
                    event.preventDefault();
                    modal.classList.add("is-open");
                    modal.setAttribute("aria-hidden", "false");
                    var input = modal.querySelector("input[name='cuil']");
                    if (input) input.focus();
                }
                return;
            }

            var bajaTrigger = event.target.closest("[data-especial-baja-open]");
            if (bajaTrigger) {
                event.preventDefault();
                if (bajaOpeningRequest) return;

                var bajaModal = document.getElementById("modalBajaAlumnoEspecial");
                var bajaUrl = new URL(bajaTrigger.href, window.location.href);
                if (!bajaModal || bajaUrl.origin !== window.location.origin) {
                    window.location.href = bajaUrl.toString();
                    return;
                }

                if (!showBajaLoading(bajaModal)) {
                    window.location.href = bajaUrl.toString();
                    return;
                }

                var operation = {
                    cancelled: false,
                    controller: new AbortController(),
                    historyUrl: bajaModal.dataset.volverUrl || window.location.href,
                    modal: bajaModal,
                    url: bajaUrl.toString()
                };
                bajaOpeningRequest = operation;
                fetch(operation.url, {
                    credentials: "same-origin",
                    signal: operation.controller.signal,
                    headers: {
                        "Accept": "text/html",
                        "X-Requested-With": "XMLHttpRequest"
                    }
                })
                    .then(function (response) {
                        if (!response.ok) throw new Error("No se pudo cargar la baja del alumno.");
                        return response.text();
                    })
                    .then(function (html) {
                        if (operation.cancelled || bajaOpeningRequest !== operation) return;
                        if (!replaceModalDialog(bajaModal, html, operation.historyUrl)) {
                            throw new Error("La respuesta no contiene el modal de baja.");
                        }
                    })
                    .catch(function (error) {
                        if (operation.cancelled || bajaOpeningRequest !== operation) return;
                        if (error && error.name === "AbortError") {
                            bajaOpeningRequest = null;
                            clearBajaLoading(bajaModal);
                            return;
                        }
                        bajaOpeningRequest = null;
                        clearBajaLoading(bajaModal);
                        window.location.href = operation.url;
                    })
                    .finally(function () {
                        if (bajaOpeningRequest !== operation) return;
                        bajaOpeningRequest = null;
                        bajaModal.removeAttribute("aria-busy");
                    });
                return;
            }

            var closeTrigger = event.target.closest("[data-modal-close], [data-docente-modal-close]");
            if (!closeTrigger) return;
            var currentModal = closeTrigger.closest(".cef-overlay, .cef-docente-overlay");
            if (!currentModal) return;
            event.preventDefault();
            if (currentModal.id === "modalBajaAlumnoEspecial") cancelBajaOpening(currentModal);
            currentModal.classList.remove("is-open");
            currentModal.setAttribute("aria-hidden", "true");
            if (currentModal.dataset.volverUrl) window.history.replaceState({}, "", currentModal.dataset.volverUrl);
        });

        document.addEventListener("click", function (event) {
            var modal = event.target.closest(".cef-overlay, .cef-docente-overlay");
            if (modal && event.target === modal) {
                if (modal.id === "modalBajaAlumnoEspecial") cancelBajaOpening(modal);
                modal.classList.remove("is-open");
                modal.setAttribute("aria-hidden", "true");
                if (modal.dataset.volverUrl) window.history.replaceState({}, "", modal.dataset.volverUrl);
            }
        });
    }

    function installDocenteAssignment() {
        if (window.especialDocenteAssignmentStaticReady) return;
        window.especialDocenteAssignmentStaticReady = true;

        function setValue(selector, value) {
            var node = document.querySelector(selector);
            if (node) node.value = value || "";
        }

        function setText(selector, value) {
            var node = document.querySelector(selector);
            if (node) node.textContent = value || "";
        }

        function closeModal() {
            var modal = document.getElementById("modalAsignarProfesorGrupo");
            if (!modal) return;
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
        }

        document.addEventListener("click", function (event) {
            var trigger = event.target.closest("[data-cef-asignar-grupo-open]");
            if (trigger) {
                event.preventDefault();
                if (trigger.classList.contains("disabled") || trigger.getAttribute("aria-disabled") === "true") return;
                setValue("[data-cef-asignar-seccion-id]", trigger.dataset.grupoId);
                setValue("[data-cef-asignar-docente-cuil]", trigger.dataset.docenteCuil);
                setText("[data-cef-asignar-grupo-label]", trigger.dataset.grupoLabel);
                setText("[data-cef-asignar-docente-label]", (trigger.dataset.docenteNombre || "Profesor") + " - " + trigger.dataset.docenteCuil);
                var modal = document.getElementById("modalAsignarProfesorGrupo");
                if (modal) {
                    modal.classList.add("is-open");
                    modal.setAttribute("aria-hidden", "false");
                }
                return;
            }

            var modal = document.getElementById("modalAsignarProfesorGrupo");
            if (modal && (event.target === modal || event.target.closest("[data-cef-asignar-grupo-close]"))) {
                event.preventDefault();
                closeModal();
            }
        });

        document.addEventListener("submit", function (event) {
            var form = event.target.closest("[data-cef-asignar-grupo-form]");
            if (!form) return;
            event.preventDefault();
            var submitButton = form.querySelector("button[type='submit']");
            if (submitButton) submitButton.disabled = true;

            fetch(form.action, {
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
                        if (data.redirected) {
                            var responseDocument = new DOMParser().parseFromString(data.fallbackHtml, "text/html");
                            var incomingPanel = responseDocument.querySelector(".cef-panel");
                            var currentPanel = document.querySelector(".cef-panel");
                            if (incomingPanel && currentPanel) {
                                currentPanel.replaceWith(document.importNode(incomingPanel, true));
                                closeModal();
                                invokeTableInitializers(document);
                                if (data.url) window.history.replaceState({}, "", data.url);
                                return;
                            }
                        }
                        HTMLFormElement.prototype.submit.call(form);
                        return;
                    }
                    if (data && data.fragment_html && data.fragment_selector) {
                        var target = document.querySelector(data.fragment_selector);
                        if (!target) {
                            HTMLFormElement.prototype.submit.call(form);
                            return;
                        }
                        var template = document.createElement("template");
                        template.innerHTML = data.fragment_html;
                        template.content.querySelectorAll("script").forEach(function (script) { script.remove(); });
                        target.replaceChildren(template.content.cloneNode(true));
                        invokeTableInitializers(target);
                        if (data.close_modal) {
                            closeModal();
                        } else if (data.modal_html) {
                            replaceAssignmentModal(data.modal_html);
                        }
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
        });

        function replaceAssignmentModal(html) {
            var currentModal = document.getElementById("modalAsignarProfesorGrupo");
            var responseDocument = new DOMParser().parseFromString(html, "text/html");
            var incomingModal = responseDocument.getElementById("modalAsignarProfesorGrupo");
            var currentDialog = currentModal ? currentModal.querySelector(".cef-docente-modal") : null;
            var incomingDialog = incomingModal ? incomingModal.querySelector(".cef-docente-modal") : null;
            if (!currentDialog || !incomingDialog) return false;
            currentDialog.replaceChildren.apply(
                currentDialog,
                Array.prototype.map.call(incomingDialog.childNodes, function (node) {
                    return document.importNode(node, true);
                })
            );
            currentModal.classList.add("is-open");
            currentModal.setAttribute("aria-hidden", "false");
            return true;
        }
    }

    function installAlumnoSeccionesExpansion() {
        if (window.cefAlumnoSeccionesExpansionReady) return;
        window.cefAlumnoSeccionesExpansionReady = true;

        document.addEventListener("click", function (event) {
            var toggle = event.target.closest("[data-cef-alumno-secciones-toggle]");
            if (!toggle) return;

            var secciones = toggle.closest(".cef-alumno-secciones");
            if (!secciones) return;

            event.preventDefault();
            var expanded = toggle.getAttribute("aria-expanded") === "true";
            var adicionales = secciones.querySelectorAll("[data-cef-alumno-seccion-adicional]");
            adicionales.forEach(function (seccion) {
                seccion.hidden = expanded;
            });

            toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
            if (expanded) {
                var restantes = toggle.getAttribute("data-cef-alumno-secciones-restantes");
                toggle.textContent = restantes === "1"
                    ? "+ 1 sección más"
                    : "+ " + restantes + " secciones más";
            } else {
                toggle.textContent = "Mostrar menos";
            }
        });
    }

    function initEspecialAlumnos(root) {
        installAlumnoSeccionesExpansion();
        installDropdown({
            readyFlag: "cefAlumnoDropdownReady",
            dropdownSelector: "[data-cef-alumno-dropdown]",
            toggleSelector: "[data-cef-alumno-dropdown-toggle]",
            menuSelector: "[data-cef-alumno-dropdown-menu]",
            menuWidth: 320
        });
    }

    function initEspecialDocentes(root) {
        installDropdown({
            readyFlag: "cefProfesorDropdownReady",
            dropdownSelector: "[data-cef-profesor-dropdown]",
            toggleSelector: "[data-cef-profesor-dropdown-toggle]",
            menuSelector: "[data-cef-profesor-dropdown-menu]",
            menuWidth: 320
        });
        installDocenteAssignment();
    }

    function initEspecialSecciones(root) {
        installDropdown({
            readyFlag: "cefRowActionsReady",
            dropdownSelector: "[data-cef-row-actions]",
            toggleSelector: "[data-cef-row-actions-toggle]",
            menuSelector: "[data-cef-row-actions-menu]",
            menuWidth: 220
        });
    }

    function initializeView(root) {
        initEspecialAlumnos(root);
        initEspecialDocentes(root);
        initEspecialSecciones(root);
        installModalTriggers();
        installModalForms();
        invokeTableInitializers(root);
    }

    function closeBajaModalAfterReload() {
        var modal = document.getElementById("modalBajaAlumnoEspecial");
        if (!modal || !modal.classList.contains("is-open")) return;

        var navigationEntries = window.performance && window.performance.getEntriesByType
            ? window.performance.getEntriesByType("navigation")
            : [];
        var isReload = navigationEntries.length && navigationEntries[0].type === "reload";
        if (!isReload) return;

        var url = new URL(window.location.href);
        if (!url.searchParams.has("abrir_modal_baja")) return;
        url.searchParams.delete("abrir_modal_baja");
        url.searchParams.delete("alumno_banco_id");
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        modal.removeAttribute("aria-busy");
        var body = modal.querySelector(".cef-modal-body");
        if (body) body.replaceChildren();
        window.history.replaceState({}, "", url.toString());
    }

    function replaceRegion(region, incomingRegion) {
        var nodes = [];
        incomingRegion.childNodes.forEach(function (node) {
            if (node.nodeType === 1 && node.tagName === "SCRIPT") return;
            nodes.push(document.importNode(node, true));
        });
        region.replaceChildren.apply(region, nodes);
        region.dataset.especialSection = incomingRegion.dataset.especialSection || "";
        region.dataset.especialTitle = incomingRegion.dataset.especialTitle || "";
        region.dataset.especialSubtitle = incomingRegion.dataset.especialSubtitle || "";
    }

    function fallback(url) {
        window.location.href = url.toString();
    }

    function navigate(url, mode) {
        var region = findRegion(document);
        var section = findSectionForUrl(url);
        if (!compatibleShell() || !region || !isSupportedSection(section)) {
            fallback(url);
            return;
        }

        if (activeRequest) activeRequest.controller.abort();
        var controller = new AbortController();
        var requestId = ++requestSequence;
        activeRequest = { controller: controller, id: requestId };
        setLoading(region);

        fetch(url.toString(), {
            method: "GET",
            credentials: "same-origin",
            signal: controller.signal,
            headers: {
                "Accept": "text/html",
                "X-Requested-With": "XMLHttpRequest",
                "X-Especial-Partial": "1"
            }
        })
            .then(function (response) {
                if (!response.ok) throw new Error("La navegacion parcial devolvio un error HTTP.");
                var contentType = response.headers.get("content-type") || "";
                if (contentType.indexOf("text/html") === -1) throw new Error("La respuesta parcial no es HTML.");
                return response.text();
            })
            .then(function (html) {
                if (!activeRequest || activeRequest.id !== requestId) return;
                var documentResponse = new DOMParser().parseFromString(html, "text/html");
                var incomingRegion = findRegion(documentResponse);
                if (!incomingRegion || incomingRegion.dataset.especialSection !== section) {
                    throw new Error("La respuesta parcial no contiene la seccion esperada.");
                }
                replaceRegion(region, incomingRegion);
                updateHeader(region);
                updateNavbar(section);
                setReady(region);
                initializeView(region);
                if (mode === "push") window.history.pushState({ especialSection: section }, "", url.toString());
            })
            .catch(function (error) {
                if (error && error.name === "AbortError") return;
                if (!activeRequest || activeRequest.id !== requestId) return;
                fallback(url);
            })
            .finally(function () {
                if (activeRequest && activeRequest.id === requestId) activeRequest = null;
            });
    }

    document.addEventListener("click", function (event) {
        if (isModifiedClick(event) || event.defaultPrevented) return;
        var link = event.target.closest(SECTION_LINK_SELECTOR);
        if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
        var url = new URL(link.href, window.location.href);
        var region = findRegion(document);
        if (
            url.origin !== window.location.origin
            || !isSupportedSection(link.dataset.especialSection)
            || !region
            || !isSupportedSection(region.dataset.especialSection)
            || !compatibleShell()
        ) return;
        event.preventDefault();
        navigate(url, "push");
    });

    window.addEventListener("popstate", function () {
        var url = new URL(window.location.href);
        var section = findSectionForUrl(url);
        if (isSupportedSection(section) && compatibleShell()) navigate(url, "pop");
        else fallback(url);
    });

    window.initEspecialAlumnos = initEspecialAlumnos;
    window.initEspecialDocentes = initEspecialDocentes;
    window.initEspecialSecciones = initEspecialSecciones;

    document.addEventListener("DOMContentLoaded", function () {
        var region = findRegion(document);
        if (region) {
            initializeView(region);
            closeBajaModalAfterReload();
        }
    });
})();
