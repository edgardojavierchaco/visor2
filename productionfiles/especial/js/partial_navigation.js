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

    function findTarget(root, selector) {
        if (!root || !selector || !root.querySelector) return null;
        try {
            return root.querySelector(selector);
        } catch (error) {
            return null;
        }
    }

    function replaceTarget(target, incomingTarget) {
        var nodes = [];
        incomingTarget.childNodes.forEach(function (node) {
            if (node.nodeType === 1 && node.tagName === "SCRIPT") return;
            nodes.push(document.importNode(node, true));
        });
        target.replaceChildren.apply(target, nodes);
    }

    function fallback(url, mode) {
        if (mode === "replace") {
            window.location.replace(url.toString());
            return;
        }
        window.location.href = url.toString();
    }

    function navigate(url, mode, options) {
        options = options || {};
        var region = findRegion(document);
        var section = findSectionForUrl(url);
        var target = findTarget(region, options.targetSelector);
        if (!compatibleShell() || !region || !isSupportedSection(section)) {
            fallback(url, mode);
            return;
        }
        if (options.targetSelector && !target) {
            fallback(url, mode);
            return;
        }
        if (activeRequest) activeRequest.controller.abort();
        var controller = new AbortController();
        var requestId = ++requestSequence;
        activeRequest = { controller: controller, id: requestId };
        if (target) {
            target.setAttribute("aria-busy", "true");
        } else {
            if (window.EspecialUI && typeof window.EspecialUI.destroy === "function") {
                window.EspecialUI.destroy(region);
            }
            setLoading(region);
        }

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
                var responseDocument = new DOMParser().parseFromString(html, "text/html");
                var incomingRegion = findRegion(responseDocument);
                if (!incomingRegion || incomingRegion.dataset.especialSection !== section) {
                    throw new Error("La respuesta parcial no contiene la seccion esperada.");
                }
                if (target) {
                    var incomingTarget = findTarget(incomingRegion, options.targetSelector);
                    if (!incomingTarget) {
                        throw new Error("La respuesta parcial no contiene el bloque esperado.");
                    }
                    if (window.EspecialUI && typeof window.EspecialUI.destroy === "function") {
                        window.EspecialUI.destroy(target);
                    }
                    replaceTarget(target, incomingTarget);
                    setReady(target);
                    if (window.EspecialUI && typeof window.EspecialUI.init === "function") {
                        window.EspecialUI.init(target);
                    }
                } else {
                    replaceRegion(region, incomingRegion);
                    setReady(region);
                    if (window.EspecialUI && typeof window.EspecialUI.init === "function") {
                        window.EspecialUI.init(region);
                    }
                }
                updateHeader(region);
                updateNavbar(section);
                if (mode === "push") window.history.pushState({ especialSection: section }, "", url.toString());
                if (mode === "replace") window.history.replaceState({ especialSection: section }, "", url.toString());
            })
            .catch(function (error) {
                if (error && error.name === "AbortError") return;
                if (!activeRequest || activeRequest.id !== requestId) return;
                fallback(url, mode);
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

    window.EspecialPartialNavigation = { navigate: navigate };
})();
