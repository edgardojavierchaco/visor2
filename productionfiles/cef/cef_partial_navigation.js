(function () {
    "use strict";

    var controller = null;
    var requestId = 0;

    function region() {
        return document.getElementById("cef-content-region");
    }

    function links() {
        return Array.prototype.slice.call(
            document.querySelectorAll("[data-cef-section-link][data-cef-fragment-url]")
        );
    }

    function isNormalClick(event, link) {
        if (event.defaultPrevented || event.button !== 0) return false;
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return false;
        if (link.hasAttribute("download") || link.hasAttribute("data-bs-toggle")) return false;
        if ((link.getAttribute("target") || "_self").toLowerCase() !== "_self") return false;
        if ((link.getAttribute("role") || "").toLowerCase() === "button") return false;

        var href = (link.getAttribute("href") || "").trim();
        if (!href || href.charAt(0) === "#" || href.toLowerCase().indexOf("javascript:") === 0) {
            return false;
        }

        var url = new URL(link.href, window.location.href);
        return url.origin === window.location.origin && !url.hash;
    }

    function setActive(activeLink) {
        document.querySelectorAll(".cef-module-nav .nav-link").forEach(function (link) {
            var active = link === activeLink;
            link.classList.toggle("active", active);
            if (active) link.setAttribute("aria-current", "page");
            else link.removeAttribute("aria-current");
        });
    }

    function findLink(url) {
        return links().find(function (link) {
            return new URL(link.href, window.location.href).pathname === url.pathname;
        }) || null;
    }

    function runInitializers(content) {
        if (typeof window.initCefSelects === "function") {
            window.initCefSelects(content);
        }
        if (typeof window.initCefTables === "function") {
            window.initCefTables(content);
        }
        if (typeof window.initInventarioList === "function") {
            window.initInventarioList(content);
        }
    }

    function load(link, targetUrl, pushState) {
        var content = region();
        if (!content) {
            window.location.assign(targetUrl.href);
            return;
        }

        if (controller) controller.abort();
        controller = new AbortController();
        requestId += 1;
        var currentId = requestId;
        var currentController = controller;
        var fragmentUrl = new URL(link.dataset.cefFragmentUrl, window.location.origin);
        fragmentUrl.search = targetUrl.search;

        setActive(link);
        content.setAttribute("aria-busy", "true");
        if (window.CEFSelects) window.CEFSelects.destroy(content);
        content.innerHTML =
            '<div class="cef-inline-loading cef-partial-loading" role="status" aria-live="polite">' +
                '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>' +
                '<span>Cargando...</span>' +
            '</div>';

        window.requestAnimationFrame(function () {
            if (currentController.signal.aborted || currentId !== requestId) return;

            fetch(fragmentUrl.href, {
                credentials: "same-origin",
                headers: { "X-Requested-With": "XMLHttpRequest" },
                signal: currentController.signal
            })
                .then(function (response) {
                    var contentType = response.headers.get("content-type") || "";
                    if (!response.ok || response.redirected || contentType.indexOf("text/html") === -1) {
                        throw new Error("HTTP " + response.status);
                    }
                    return response.text();
                })
                .then(function (html) {
                    if (currentController.signal.aborted || currentId !== requestId) return;
                    if (!html.trim()) throw new Error("Respuesta vacía");
                    content.innerHTML = html;
                    content.setAttribute("aria-busy", "false");
                    runInitializers(content);
                    if (pushState) {
                        window.history.pushState({}, "", targetUrl.href);
                    }
                })
                .catch(function (error) {
                    if (error.name === "AbortError" || currentId !== requestId) return;
                    window.location.assign(targetUrl.href);
                })
                .finally(function () {
                    if (controller === currentController) controller = null;
                });
        });
    }

    document.addEventListener("click", function (event) {
        var link = event.target.closest("[data-cef-section-link][data-cef-fragment-url]");
        if (!link || !isNormalClick(event, link)) return;
        event.preventDefault();
        load(link, new URL(link.href, window.location.href), true);
    });

    window.addEventListener("popstate", function () {
        var targetUrl = new URL(window.location.href);
        var link = findLink(targetUrl);
        if (!link) {
            window.location.assign(targetUrl.href);
            return;
        }
        load(link, targetUrl, false);
    });
})();
