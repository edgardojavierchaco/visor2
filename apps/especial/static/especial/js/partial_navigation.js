(function () {
    "use strict";

    var SECTION_LINK_SELECTOR = "[data-especial-section-link]";
    var REGION_SELECTOR = "[data-especial-content-region]";
    var SEARCH_SELECTOR = "[data-especial-search]";
    var SUBVIEW_LINK_SELECTOR = "[data-especial-subview-link]";
    var SUPPORTED_SECTIONS = ["alumnos", "docentes", "cueanexo", "secciones", "ciclos"];
    var requestSequence = 0;
    var activeRequest = null;
    var lastConfirmedUrl = window.location.href;

    function isSupportedSection(section) {
        return SUPPORTED_SECTIONS.indexOf(section) !== -1;
    }

    function findRegion(root) {
        if (!root) return null;
        if (root.matches && root.matches(REGION_SELECTOR)) return root;
        return root.querySelector ? root.querySelector(REGION_SELECTOR) : null;
    }

    function findSearchRoot(root) {
        if (!root) return null;
        if (root.matches && root.matches(SEARCH_SELECTOR)) return root;
        return root.querySelector ? root.querySelector(SEARCH_SELECTOR) : null;
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

    function subviewLinks(searchRoot) {
        return searchRoot ? searchRoot.querySelectorAll(SUBVIEW_LINK_SELECTOR) : [];
    }

    function getSubviewLink(searchRoot, view) {
        var links = subviewLinks(searchRoot);
        for (var i = 0; i < links.length; i += 1) {
            if (links[i].dataset.especialSubview === view) return links[i];
        }
        return null;
    }

    function findSubviewActionsSlot(searchRoot) {
        var panel = searchRoot && searchRoot.closest ? searchRoot.closest(".cef-panel") : null;
        return panel ? panel.querySelector("[data-especial-subview-actions]") : null;
    }

    function syncSubviewActions(operation, incomingRegion) {
        var incomingSlot = findTarget(incomingRegion, "[data-especial-subview-actions]");
        if (!operation.actionSlot || !incomingSlot) {
            throw new Error("La respuesta parcial no contiene el bloque de acciones esperado.");
        }
        replaceTarget(operation.actionSlot, incomingSlot);
        operation.actionsCommitted = true;
    }

    function restoreSubviewActions(operation) {
        if (!operation || !operation.actionsCommitted || !operation.actionSlot) return;
        operation.actionSlot.replaceChildren.apply(operation.actionSlot, operation.previousActionChildren || []);
        operation.actionsCommitted = false;
    }

    function syncSubviewTabs(searchRoot, confirmedView, pendingView, suppressInitialTransition) {
        if (!searchRoot || !confirmedView) return;
        var links = subviewLinks(searchRoot);
        for (var i = 0; i < links.length; i += 1) {
            var link = links[i];
            var view = link.dataset.especialSubview || "";
            link.classList.remove("is-active", "is-pending");
            if (view === confirmedView) link.classList.add("is-active");
            if (pendingView && view === pendingView && view !== confirmedView) {
                link.classList.add("is-pending");
            }
            link.setAttribute("aria-selected", view === confirmedView ? "true" : "false");
        }
        searchRoot.dataset.especialSearchView = confirmedView;
        if (pendingView && pendingView !== confirmedView) {
            searchRoot.dataset.especialSearchPendingView = pendingView;
        } else {
            searchRoot.removeAttribute("data-especial-search-pending-view");
        }

        var indicator = searchRoot.querySelector("[data-especial-view-indicator]");
        var destination = getSubviewLink(searchRoot, pendingView || confirmedView);
        if (indicator && destination) {
            if (suppressInitialTransition) indicator.style.transition = "none";
            indicator.style.width = destination.offsetWidth + "px";
            indicator.style.transform = "translateX(" + destination.offsetLeft + "px)";
            if (suppressInitialTransition) {
                var restoreIndicatorTransition = function () {
                    indicator.style.transition = "";
                };
                if (window.requestAnimationFrame) window.requestAnimationFrame(restoreIndicatorTransition);
                else window.setTimeout(restoreIndicatorTransition, 0);
            }
        }
    }

    function initializeSubviewTabs(root) {
        var searchRoot = findSearchRoot(root);
        if (!searchRoot) return;
        var active = searchRoot.querySelector(SUBVIEW_LINK_SELECTOR + ".is-active");
        var confirmedView = searchRoot.dataset.especialSearchView
            || (active && active.dataset.especialSubview)
            || "actuales";
        syncSubviewTabs(searchRoot, confirmedView, "", true);
    }

    function findSubviewOptions(region, url) {
        var searchRoot = findSearchRoot(region);
        if (!searchRoot) return null;
        var viewParam = searchRoot.getAttribute("data-especial-search-view-param") || "vista";
        var view = url.searchParams.get(viewParam) || searchRoot.dataset.especialSearchView || "";
        var link = getSubviewLink(searchRoot, view);
        if (!link) return null;
        return {
            subview: view,
            targetSelector: searchRoot.getAttribute("data-especial-search-results-selector") || ""
        };
    }

    function cloneChildNodes(root) {
        var nodes = [];
        root.childNodes.forEach(function (node) {
            nodes.push(node.cloneNode(true));
        });
        return nodes;
    }

    function clearSubviewLoadingTimer(operation) {
        if (operation && operation.loadingTimer) {
            window.clearTimeout(operation.loadingTimer);
            operation.loadingTimer = null;
        }
    }

    function setSearchControlsDisabled(operation, disabled) {
        if (!operation || !operation.searchRoot) return;
        if (disabled) {
            operation.disabledControls = [];
            var controls = operation.searchRoot.querySelectorAll(
                "[data-especial-search-input]"
            );
            for (var i = 0; i < controls.length; i += 1) {
                operation.disabledControls.push({
                    node: controls[i],
                    disabled: controls[i].disabled
                });
                controls[i].disabled = true;
            }
            return;
        }
        (operation.disabledControls || []).forEach(function (entry) {
            if (entry.node) entry.node.disabled = entry.disabled;
        });
        operation.disabledControls = [];
    }

    function localizedLoading(viewLabel) {
        var status = document.createElement("div");
        status.className = "especial-search-results-loading";
        status.setAttribute("role", "status");
        status.setAttribute("aria-live", "polite");
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("aria-hidden", "true");
        status.appendChild(spinner);
        status.appendChild(document.createTextNode("Cargando " + viewLabel + "..."));
        return status;
    }

    function localizedError(viewLabel) {
        var error = document.createElement("div");
        error.className = "alert alert-danger mb-3";
        error.setAttribute("role", "alert");
        error.textContent = "No se pudo cargar " + viewLabel + ". Se conservaron los resultados anteriores.";
        return error;
    }

    function beginSubviewTransition(operation) {
        var target = operation.target;
        operation.searchRoot = findSearchRoot(document);
        if (!operation.searchRoot) return false;
        operation.actionSlot = findSubviewActionsSlot(operation.searchRoot);
        if (!operation.actionSlot) return false;
        operation.confirmedView = operation.searchRoot.dataset.especialSearchView || "actuales";
        operation.previousChildren = cloneChildNodes(target);
        operation.previousSearchMode = target.getAttribute("data-especial-search-mode");
        operation.previousActionChildren = cloneChildNodes(operation.actionSlot);
        operation.previousMinHeight = target.style.minHeight;
        var previousHeight = target.getBoundingClientRect().height;
        if (previousHeight > 0) target.style.minHeight = Math.ceil(previousHeight) + "px";
        var link = getSubviewLink(operation.searchRoot, operation.subview);
        operation.viewLabel = link ? link.textContent.trim() : operation.subview;
        target.setAttribute("aria-busy", "true");
        setSearchControlsDisabled(operation, true);
        syncSubviewTabs(operation.searchRoot, operation.confirmedView, operation.subview);
        operation.loadingTimer = window.setTimeout(function () {
            if (activeRequest !== operation) return;
            if (window.EspecialUI && typeof window.EspecialUI.destroy === "function") {
                window.EspecialUI.destroy(target);
            }
            operation.targetDestroyed = true;
            target.replaceChildren(localizedLoading(operation.viewLabel));
            operation.loadingShown = true;
        }, 200);
        return true;
    }

    function restoreSubviewTarget(operation) {
        if (!operation || !operation.target || !operation.previousChildren) return;
        if (window.EspecialUI && typeof window.EspecialUI.destroy === "function") {
            window.EspecialUI.destroy(operation.target);
        }
        operation.target.replaceChildren.apply(operation.target, operation.previousChildren);
        if (operation.previousSearchMode === null) {
            operation.target.removeAttribute("data-especial-search-mode");
        } else {
            operation.target.setAttribute("data-especial-search-mode", operation.previousSearchMode);
        }
        if (window.EspecialUI && typeof window.EspecialUI.init === "function") {
            window.EspecialUI.init(operation.target);
        }
        if (
            operation.searchRoot
            && window.EspecialBusqueda
            && typeof window.EspecialBusqueda.refresh === "function"
        ) {
            window.EspecialBusqueda.refresh(operation.searchRoot);
        }
    }

    function restoreSubviewOperation(operation, showError) {
        clearSubviewLoadingTimer(operation);
        if (operation.loadingShown || operation.targetReplaced) restoreSubviewTarget(operation);
        restoreSubviewActions(operation);
        operation.target.style.minHeight = operation.previousMinHeight || "";
        setReady(operation.target);
        setSearchControlsDisabled(operation, false);
        syncSubviewTabs(operation.searchRoot, operation.confirmedView, "");
        if (showError) operation.target.insertBefore(localizedError(operation.viewLabel), operation.target.firstChild);
        if (operation.mode === "pop" && operation.previousUrl !== window.location.href) {
            var previousUrl = new URL(operation.previousUrl, window.location.href);
            window.history.replaceState(
                { especialSection: findSectionForUrl(previousUrl) },
                "",
                previousUrl.toString()
            );
        }
        lastConfirmedUrl = operation.previousUrl;
    }

    function cancelOperation(operation) {
        clearSubviewLoadingTimer(operation);
        if (operation.subview) {
            if (operation.loadingShown || operation.targetReplaced) restoreSubviewTarget(operation);
            restoreSubviewActions(operation);
            operation.target.style.minHeight = operation.previousMinHeight || "";
            setReady(operation.target);
            setSearchControlsDisabled(operation, false);
            syncSubviewTabs(operation.searchRoot, operation.confirmedView, "");
        }
    }

    function commitSubviewOperation(operation, incomingTarget, incomingRegion) {
        clearSubviewLoadingTimer(operation);
        syncSubviewActions(operation, incomingRegion);
        if (!operation.targetDestroyed && window.EspecialUI && typeof window.EspecialUI.destroy === "function") {
            window.EspecialUI.destroy(operation.target);
        }
        replaceTarget(operation.target, incomingTarget);
        operation.target.setAttribute(
            "data-especial-search-mode",
            incomingTarget.getAttribute("data-especial-search-mode") || "server"
        );
        operation.targetReplaced = true;
        setReady(operation.target);
        if (window.EspecialUI && typeof window.EspecialUI.init === "function") {
            window.EspecialUI.init(operation.target);
        }
        if (
            operation.searchRoot
            && window.EspecialBusqueda
            && typeof window.EspecialBusqueda.refresh === "function"
        ) {
            window.EspecialBusqueda.refresh(operation.searchRoot);
        }
        operation.target.style.minHeight = operation.previousMinHeight || "";
        setSearchControlsDisabled(operation, false);
        syncSubviewTabs(operation.searchRoot, operation.subview, "");
    }

    function navigate(url, mode, options) {
        options = options || {};
        var sameUrl = url.pathname === window.location.pathname && url.search === window.location.search;
        if (sameUrl && mode !== "pop") return;
        if (
            activeRequest
            && activeRequest.url.toString() === url.toString()
            && activeRequest.subview === (options.subview || "")
        ) return;

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
        if (options.subview && !target) {
            fallback(url, mode);
            return;
        }

        if (activeRequest) {
            activeRequest.controller.abort();
            cancelOperation(activeRequest);
            activeRequest = null;
        }
        var controller = new AbortController();
        var requestId = ++requestSequence;
        var operation = {
            controller: controller,
            id: requestId,
            mode: mode,
            options: options,
            previousUrl: lastConfirmedUrl,
            subview: options.subview || "",
            target: target,
            url: url
        };
        activeRequest = operation;
        if (target) {
            if (operation.subview) {
                if (!beginSubviewTransition(operation)) {
                    activeRequest = null;
                    fallback(url, mode);
                    return;
                }
            } else {
                target.setAttribute("aria-busy", "true");
            }
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
                    if (operation.subview && operation.searchRoot) {
                        commitSubviewOperation(operation, incomingTarget, incomingRegion);
                    } else {
                        if (window.EspecialUI && typeof window.EspecialUI.destroy === "function") {
                            window.EspecialUI.destroy(target);
                        }
                        replaceTarget(target, incomingTarget);
                        setReady(target);
                        if (window.EspecialUI && typeof window.EspecialUI.init === "function") {
                            window.EspecialUI.init(target);
                        }
                    }
                } else {
                    replaceRegion(region, incomingRegion);
                    setReady(region);
                    if (window.EspecialUI && typeof window.EspecialUI.init === "function") {
                        window.EspecialUI.init(region);
                    }
                    initializeSubviewTabs(region);
                }
                updateHeader(region);
                updateNavbar(section);
                if (mode === "push") window.history.pushState({ especialSection: section }, "", url.toString());
                if (mode === "replace") window.history.replaceState({ especialSection: section }, "", url.toString());
                lastConfirmedUrl = url.toString();
            })
            .catch(function (error) {
                if (error && error.name === "AbortError") return;
                if (!activeRequest || activeRequest.id !== requestId) return;
                if (operation.subview && operation.searchRoot) {
                    restoreSubviewOperation(operation, true);
                    return;
                }
                fallback(url, mode);
            })
            .finally(function () {
                if (activeRequest && activeRequest.id === requestId) activeRequest = null;
            });
    }

    document.addEventListener("click", function (event) {
        if (isModifiedClick(event) || event.defaultPrevented) return;
        var subviewLink = event.target.closest(SUBVIEW_LINK_SELECTOR);
        if (subviewLink) {
            if (subviewLink.target === "_blank" || subviewLink.hasAttribute("download")) return;
            var subviewUrl = new URL(subviewLink.href, window.location.href);
            var subviewRegion = findRegion(document);
            var subviewSection = subviewLink.dataset.especialSection || findSectionForUrl(subviewUrl);
            if (
                subviewUrl.origin !== window.location.origin
                || !isSupportedSection(subviewSection)
                || !subviewRegion
                || subviewRegion.dataset.especialSection !== subviewSection
                || !compatibleShell()
            ) return;
            event.preventDefault();
            navigate(subviewUrl, "push", {
                targetSelector: subviewLink.dataset.especialTargetSelector || "",
                subview: subviewLink.dataset.especialSubview || ""
            });
            return;
        }

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
        var region = findRegion(document);
        var section = findSectionForUrl(url);
        if (isSupportedSection(section) && compatibleShell()) {
            navigate(url, "pop", findSubviewOptions(region, url) || {});
        } else {
            fallback(url);
        }
    });

    initializeSubviewTabs(document);
    window.EspecialPartialNavigation = { navigate: navigate };
})();
