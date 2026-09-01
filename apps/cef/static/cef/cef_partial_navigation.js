(function () {
    "use strict";

    var controller = null;
    var requestId = 0;
    var loadingDelay = 200;
    var activeMenuStateKey = "cef-active-menu-before-page-navigation";
    var navigationSelector =
        "[data-cef-section-link][data-cef-fragment-url], " +
        "[data-cef-view-link][data-cef-fragment-url]";

    function region() {
        return document.getElementById("cef-content-region");
    }

    function links() {
        return Array.prototype.slice.call(
            document.querySelectorAll(navigationSelector)
        );
    }

    function courseLinks() {
        return Array.prototype.slice.call(
            document.querySelectorAll("[data-cef-course-view-link]")
        );
    }

    function isNormalClick(event, link, allowHash) {
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
        return url.origin === window.location.origin && (allowHash || !url.hash);
    }

    function setActive(activeLink) {
        document.querySelectorAll(".cef-module-nav .nav-link").forEach(function (link) {
            var active = link === activeLink;
            link.classList.toggle("active", active);
            if (active) link.setAttribute("aria-current", "page");
            else link.removeAttribute("aria-current");
        });
    }

    function saveActiveMenuState() {
        var activeLink = document.querySelector(".cef-module-nav .nav-link.active");
        if (!activeLink) return;
        try {
            window.sessionStorage.setItem(activeMenuStateKey, activeLink.href);
        } catch (error) {
            return;
        }
    }

    function restoreActiveMenuState() {
        var activeHref;
        try {
            activeHref = window.sessionStorage.getItem(activeMenuStateKey);
            window.sessionStorage.removeItem(activeMenuStateKey);
        } catch (error) {
            return;
        }
        if (!activeHref) return;
        var activeLink = Array.prototype.slice.call(
            document.querySelectorAll(".cef-module-nav .nav-link")
        ).find(function (link) {
            return link.href === activeHref;
        });
        if (activeLink) setActive(activeLink);
    }

    function setViewActive(activeLink) {
        var tabs = activeLink ? activeLink.closest(".nav-tabs") : null;
        if (!tabs) return;
        tabs.querySelectorAll(".nav-link").forEach(function (link) {
            var active = link === activeLink;
            link.classList.toggle("active", active);
            if (active) link.setAttribute("aria-current", "page");
            else link.removeAttribute("aria-current");
        });
    }

    function showLoading(target, viewLabel, preserveHeight) {
        if (!target) return;
        var currentHeight = preserveHeight
            ? Math.ceil(target.getBoundingClientRect().height)
            : 0;
        if (window.CEFSelects) window.CEFSelects.destroy(target);
        var loading = document.createElement("div");
        var spinner = document.createElement("span");
        var label = document.createElement("span");
        loading.className = "cef-inline-loading cef-partial-loading";
        loading.setAttribute("role", "status");
        loading.setAttribute("aria-live", "polite");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("aria-hidden", "true");
        label.textContent = viewLabel ? "Cargando " + viewLabel + "..." : "Cargando...";
        loading.appendChild(spinner);
        loading.appendChild(label);
        if (currentHeight > 144) loading.style.minHeight = currentHeight + "px";
        target.replaceChildren(loading);
        target.setAttribute("aria-busy", "true");
    }

    function scheduleLoading(target, viewLabel, preserveHeight) {
        return window.setTimeout(function () {
            showLoading(target, viewLabel, preserveHeight);
        }, loadingDelay);
    }

    function findLink(url) {
        var availableLinks = links();
        var exactView = availableLinks.find(function (link) {
            var linkUrl = new URL(link.href, window.location.href);
            return link.hasAttribute("data-cef-view-link")
                && linkUrl.pathname === url.pathname
                && linkUrl.search === url.search;
        });
        if (exactView) return exactView;
        var exact = availableLinks.find(function (link) {
            var linkUrl = new URL(link.href, window.location.href);
            return linkUrl.pathname === url.pathname && linkUrl.search === url.search;
        });
        if (exact) return exact;
        return availableLinks.find(function (link) {
            return link.hasAttribute("data-cef-section-link")
                && new URL(link.href, window.location.href).pathname === url.pathname;
        }) || null;
    }

    function findCourseLink(url) {
        var matches = courseLinks().filter(function (link) {
            var linkUrl = new URL(link.href, window.location.href);
            return linkUrl.pathname === url.pathname && linkUrl.search === url.search;
        });
        return matches.find(function (link) {
            return !link.classList.contains("active");
        }) || matches[0] || null;
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
        var sectionNavigation = link.hasAttribute("data-cef-section-link");
        var historyUpdated = false;
        var loadingTimer = null;

        if (sectionNavigation) setActive(link);
        else setViewActive(link);
        content.setAttribute("aria-busy", "true");
        if (sectionNavigation) {
            showLoading(content, "");
        } else {
            var panel = link.closest(".cef-panel");
            var viewContent = panel ? panel.querySelector("[data-cef-view-content]") : null;
            loadingTimer = scheduleLoading(
                viewContent || content,
                link.textContent.trim(),
                Boolean(viewContent)
            );
            if (pushState) {
                window.history.pushState({}, "", targetUrl.href);
                historyUpdated = true;
            }
        }

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
                    if (loadingTimer !== null) window.clearTimeout(loadingTimer);
                    if (window.CEFSelects) window.CEFSelects.destroy(content);
                    content.innerHTML = html;
                    content.setAttribute("aria-busy", "false");
                    runInitializers(content);
                    if (pushState && !historyUpdated) {
                        window.history.pushState({}, "", targetUrl.href);
                    }
                })
                .catch(function (error) {
                    if (error.name === "AbortError" || currentId !== requestId) return;
                    window.location.assign(targetUrl.href);
                })
                .finally(function () {
                    if (loadingTimer !== null) window.clearTimeout(loadingTimer);
                    if (currentId === requestId && content.isConnected) {
                        content.setAttribute("aria-busy", "false");
                    }
                    if (controller === currentController) controller = null;
                });
        });
    }

    function courseFragmentNodes(data) {
        if (!data || !data.ok || !Array.isArray(data.fragments)) return null;
        var replacements = [];
        var valid = data.fragments.every(function (fragment) {
            var current = fragment.selector
                ? document.querySelector(fragment.selector)
                : null;
            if (!current || typeof fragment.html !== "string") return false;
            var wrapper = document.createElement("div");
            wrapper.innerHTML = fragment.html.trim();
            var next = wrapper.firstElementChild;
            if (!next) return false;
            replacements.push({ current: current, next: next });
            return true;
        });
        return valid ? replacements : null;
    }

    function loadCourseView(link, targetUrl, pushState) {
        var currentSection = link.closest(".cef-course-section");
        if (!currentSection) {
            window.location.assign(targetUrl.href);
            return;
        }

        if (controller) controller.abort();
        controller = new AbortController();
        requestId += 1;
        var currentId = requestId;
        var currentController = controller;
        var sectionId = currentSection.id;
        var sectionTop = currentSection.getBoundingClientRect().top;
        var fragmentUrl = new URL(targetUrl.href);
        fragmentUrl.hash = "";
        fragmentUrl.searchParams.set("fragmento", link.dataset.cefCourseView);
        var loadingTarget = currentSection.querySelector("[data-cef-fragment]");
        var historyUpdated = false;
        var loadingTimer = null;
        setViewActive(link);
        currentSection.setAttribute("aria-busy", "true");
        loadingTimer = scheduleLoading(
            loadingTarget || currentSection,
            link.textContent.trim(),
            Boolean(loadingTarget)
        );
        if (pushState) {
            window.history.pushState({}, "", targetUrl.href);
            historyUpdated = true;
        }

        fetch(fragmentUrl.href, {
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            signal: currentController.signal
        })
            .then(function (response) {
                var contentType = response.headers.get("content-type") || "";
                if (!response.ok || response.redirected || contentType.indexOf("application/json") === -1) {
                    throw new Error("HTTP " + response.status);
                }
                return response.json();
            })
            .then(function (data) {
                if (currentController.signal.aborted || currentId !== requestId) return;
                if (loadingTimer !== null) window.clearTimeout(loadingTimer);
                var replacements = courseFragmentNodes(data);
                if (!replacements) throw new Error("Respuesta parcial inválida");
                replacements.forEach(function (replacement) {
                    if (window.CEFSelects) window.CEFSelects.destroy(replacement.current);
                    replacement.current.replaceWith(replacement.next);
                    runInitializers(replacement.next);
                });
                if (pushState && !historyUpdated) {
                    window.history.pushState({}, "", targetUrl.href);
                }
                var nextSection = sectionId ? document.getElementById(sectionId) : null;
                if (nextSection) {
                    window.requestAnimationFrame(function () {
                        var delta = nextSection.getBoundingClientRect().top - sectionTop;
                        if (Math.abs(delta) > 0.5) window.scrollBy(0, delta);
                    });
                }
            })
            .catch(function (error) {
                if (error.name === "AbortError" || currentId !== requestId) return;
                window.location.assign(targetUrl.href);
            })
            .finally(function () {
                if (loadingTimer !== null) window.clearTimeout(loadingTimer);
                if (currentId === requestId && currentSection.isConnected) {
                    currentSection.setAttribute("aria-busy", "false");
                }
                if (controller === currentController) controller = null;
            });
    }

    document.addEventListener("click", function (event) {
        var courseLink = event.target.closest("[data-cef-course-view-link]");
        if (courseLink && isNormalClick(event, courseLink, true)) {
            event.preventDefault();
            if (courseLink.classList.contains("active")) return;
            loadCourseView(courseLink, new URL(courseLink.href, window.location.href), true);
            return;
        }

        var link = event.target.closest(navigationSelector);
        if (!link || !isNormalClick(event, link)) return;
        event.preventDefault();
        if (link.hasAttribute("data-cef-view-link") && link.classList.contains("active")) return;
        load(link, new URL(link.href, window.location.href), true);
    });

    window.addEventListener("popstate", function () {
        var targetUrl = new URL(window.location.href);
        var courseLink = findCourseLink(targetUrl);
        if (courseLink) {
            loadCourseView(courseLink, targetUrl, false);
            return;
        }
        var link = findLink(targetUrl);
        if (!link) {
            window.location.assign(targetUrl.href);
            return;
        }
        load(link, targetUrl, false);
    });

    window.CEFPartialNavigation = {
        saveActiveMenuState: saveActiveMenuState,
        setActive: setActive,
        restoreActiveMenuState: restoreActiveMenuState
    };
})();
