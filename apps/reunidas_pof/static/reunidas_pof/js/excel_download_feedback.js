/**
 * Coordina el estado visual de las descargas Excel POF con la confirmación
 * que Django deja en una cookie cuando la respuesta XLSX ya está construida.
 * El token solo correlaciona la descarga con su opción y nunca autoriza datos.
 */
(function () {
    "use strict";

    const READY_COOKIE_NAME = "pof_excel_download_ready";
    const READY_COOKIE_PATH = "/";
    const LEGACY_READY_COOKIE_PATH = "/reunidas_pof/";
    const READY_CHECK_INTERVAL = 100;
    const RECOVERY_TIMEOUT = 120000;
    const EXPORT_SELECTOR = "[data-pof-excel-link], [data-pof-excel-all-link]";
    const activeGroups = new WeakMap();

    function readCookie(name) {
        const prefix = name + "=";
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (let index = 0; index < cookies.length; index += 1) {
            const cookie = cookies[index].trim();
            if (cookie.indexOf(prefix) !== 0) {
                continue;
            }
            try {
                return decodeURIComponent(cookie.slice(prefix.length));
            } catch (_error) {
                return "";
            }
        }
        return "";
    }

    function expireReadyCookie(path) {
        document.cookie = READY_COOKIE_NAME
            + "=; Max-Age=0; Path="
            + path
            + "; SameSite=Lax";
    }

    function clearReadyCookie() {
        expireReadyCookie(READY_COOKIE_PATH);
        expireReadyCookie(LEGACY_READY_COOKIE_PATH);
    }

    function createDownloadToken() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        if (window.crypto && typeof window.crypto.getRandomValues === "function") {
            const bytes = new Uint8Array(16);
            window.crypto.getRandomValues(bytes);
            return Array.from(bytes).map(function (byte) {
                return byte.toString(16).padStart(2, "0");
            }).join("");
        }
        return "pof-"
            + Date.now().toString(36)
            + "-"
            + Math.random().toString(36).slice(2)
            + Math.random().toString(36).slice(2);
    }

    function snapshotAttribute(element, name) {
        return element.hasAttribute(name) ? element.getAttribute(name) : null;
    }

    function restoreAttribute(element, name, value) {
        if (value === null) {
            element.removeAttribute(name);
        } else {
            element.setAttribute(name, value);
        }
    }

    function getGroup(link) {
        return link.closest(".pof-grid-dropdown") || document.body;
    }

    function getExportActions(group) {
        return Array.from(group.querySelectorAll(EXPORT_SELECTOR));
    }

    function getExportToggle(group) {
        return Array.from(group.querySelectorAll(".pof-btn-excel")).find(function (element) {
            return element.tagName === "BUTTON";
        }) || null;
    }

    function buildDownloadUrl(link, token) {
        const href = link.getAttribute("href");
        if (!href || href === "#") {
            return "";
        }
        const url = new URL(href, window.location.href);
        if (url.origin !== window.location.origin) {
            return "";
        }
        url.searchParams.set("download_token", token);
        return url.toString();
    }

    function setBusyLabel(link) {
        const icon = link.querySelector(".pof-action-icon");
        if (icon) {
            icon.textContent = "hourglass_top";
            icon.classList.add("pof-download-spinner");
        }

        const labelNode = Array.from(link.childNodes).find(function (node) {
            return node.nodeType === Node.TEXT_NODE && node.textContent.trim();
        });
        if (labelNode) {
            labelNode.nodeValue = " Procesando...";
            return;
        }

        const label = document.createElement("span");
        label.textContent = "Procesando...";
        link.append(label);
    }

    function setToggleBusy(toggle) {
        const icon = document.createElement("span");
        icon.className = "pof-action-icon pof-material-symbol material-symbols-outlined pof-download-spinner";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "progress_activity";

        const label = document.createElement("span");
        label.className = "pof-download-label";
        label.textContent = "Procesando...";

        toggle.replaceChildren(icon, label);
    }

    function createDownloadOverlay() {
        const overlay = document.createElement("div");
        overlay.className = "pof-export-download-overlay";
        overlay.setAttribute("role", "status");
        overlay.setAttribute("aria-live", "polite");

        const panel = document.createElement("div");
        panel.className = "pof-export-download-overlay-panel";

        const icon = document.createElement("span");
        icon.className = "pof-material-symbol material-symbols-outlined pof-download-spinner pof-export-download-overlay-spinner";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "progress_activity";

        const title = document.createElement("strong");
        title.className = "pof-export-download-overlay-title";
        title.textContent = "Procesando exportación...";

        const detail = document.createElement("span");
        detail.className = "pof-export-download-overlay-detail";
        detail.textContent = "La descarga comenzará en unos instantes.";

        panel.append(icon, title, detail);
        overlay.append(panel);
        return overlay;
    }

    function blockAction(link, selected) {
        const snapshot = {
            html: link.innerHTML,
            ariaBusy: snapshotAttribute(link, "aria-busy"),
            ariaDisabled: snapshotAttribute(link, "aria-disabled"),
            ariaLabel: snapshotAttribute(link, "aria-label"),
            tabIndex: snapshotAttribute(link, "tabindex")
        };
        link.dataset.pofDownloadBlocked = "true";
        link.setAttribute("aria-disabled", "true");
        link.setAttribute("tabindex", "-1");

        if (selected) {
            link.classList.add("pof-export-download-busy");
            link.setAttribute("aria-busy", "true");
            link.setAttribute("aria-label", "Procesando...");
            setBusyLabel(link);
        } else {
            link.classList.add("pof-export-download-blocked");
        }
        return snapshot;
    }

    function restoreAction(link, snapshot, selected) {
        if (selected) {
            link.innerHTML = snapshot.html;
        }
        link.classList.remove(
            "pof-export-download-busy",
            "pof-export-download-blocked"
        );
        delete link.dataset.pofDownloadBlocked;
        restoreAttribute(link, "aria-busy", snapshot.ariaBusy);
        if (!link.classList.contains("pof-export-btn-disabled")) {
            restoreAttribute(link, "aria-disabled", snapshot.ariaDisabled);
        }
        restoreAttribute(link, "aria-label", snapshot.ariaLabel);
        restoreAttribute(link, "tabindex", snapshot.tabIndex);
    }

    function finishDownload(state) {
        if (state.pollTimer) {
            window.clearInterval(state.pollTimer);
        }
        if (state.recoveryTimer) {
            window.clearTimeout(state.recoveryTimer);
        }
        if (readCookie(READY_COOKIE_NAME) === state.token) {
            clearReadyCookie();
        }
        if (state.frame && state.frame.parentNode) {
            state.frame.remove();
        }

        state.actions.forEach(function (action) {
            restoreAction(
                action,
                state.snapshots.get(action),
                action === state.selectedAction
            );
        });
        if (state.toggle) {
            state.toggle.innerHTML = state.toggleSnapshot.html;
            restoreAttribute(state.toggle, "aria-busy", state.toggleSnapshot.ariaBusy);
            restoreAttribute(state.toggle, "aria-disabled", state.toggleSnapshot.ariaDisabled);
            restoreAttribute(state.toggle, "aria-label", state.toggleSnapshot.ariaLabel);
            restoreAttribute(state.toggle, "tabindex", state.toggleSnapshot.tabIndex);
        }
        if (state.page) {
            state.page.inert = state.pageInert;
            restoreAttribute(state.page, "aria-busy", state.pageAriaBusy);
        }
        if (state.overlay && state.overlay.parentNode) {
            state.overlay.remove();
        }
        state.group.classList.remove("pof-export-download-active");
        activeGroups.delete(state.group);
    }

    function startDownload(link, group) {
        if (activeGroups.has(group)) {
            return false;
        }

        clearReadyCookie();
        const token = createDownloadToken();
        const downloadUrl = buildDownloadUrl(link, token);
        const actions = getExportActions(group);
        if (!downloadUrl || !actions.length) {
            return false;
        }

        const toggle = getExportToggle(group);
        const state = {
            group: group,
            token: token,
            selectedAction: link,
            actions: actions,
            snapshots: new Map(),
            toggle: toggle,
            toggleSnapshot: toggle
                ? {
                    html: toggle.innerHTML,
                    ariaBusy: snapshotAttribute(toggle, "aria-busy"),
                    ariaDisabled: snapshotAttribute(toggle, "aria-disabled"),
                    ariaLabel: snapshotAttribute(toggle, "aria-label"),
                    tabIndex: snapshotAttribute(toggle, "tabindex")
                }
                : null,
            frame: null,
            pollTimer: null,
            recoveryTimer: null,
            overlay: null,
            page: document.querySelector(".pof-page"),
            pageInert: false,
            pageAriaBusy: null
        };
        activeGroups.set(group, state);

        actions.forEach(function (action) {
            state.snapshots.set(action, blockAction(action, action === link));
        });
        if (toggle) {
            group.classList.add("pof-export-download-active");
            toggle.setAttribute("aria-busy", "true");
            toggle.setAttribute("aria-disabled", "true");
            toggle.setAttribute("aria-label", "Procesando...");
            toggle.setAttribute("tabindex", "-1");
            setToggleBusy(toggle);
        }
        if (state.page) {
            state.pageInert = Boolean(state.page.inert);
            state.pageAriaBusy = snapshotAttribute(state.page, "aria-busy");
            state.page.inert = true;
            state.page.setAttribute("aria-busy", "true");
        }
        state.overlay = createDownloadOverlay();
        (document.body || document.documentElement).appendChild(state.overlay);

        try {
            const frame = document.createElement("iframe");
            frame.setAttribute("aria-hidden", "true");
            frame.tabIndex = -1;
            frame.style.cssText = "border:0;height:0;position:absolute;visibility:hidden;width:0;";
            frame.src = downloadUrl;
            (document.body || document.documentElement).appendChild(frame);
            state.frame = frame;
        } catch (error) {
            window.console.error(error);
            finishDownload(state);
            return false;
        }

        state.pollTimer = window.setInterval(function () {
            if (readCookie(READY_COOKIE_NAME) === state.token) {
                finishDownload(state);
            }
        }, READY_CHECK_INTERVAL);
        state.recoveryTimer = window.setTimeout(function () {
            if (activeGroups.get(group) === state) {
                finishDownload(state);
            }
        }, RECOVERY_TIMEOUT);
        return true;
    }

    document.querySelectorAll(EXPORT_SELECTOR).forEach(function (link) {
        const group = getGroup(link);
        link.addEventListener("click", function (event) {
            if (link.getAttribute("aria-disabled") === "true"
                || link.dataset.pofDownloadBlocked === "true") {
                event.preventDefault();
                return;
            }
            if (startDownload(link, group)) {
                event.preventDefault();
            }
        });

        const toggle = getExportToggle(group);
        if (toggle && !toggle.dataset.pofDownloadFeedbackBound) {
            toggle.dataset.pofDownloadFeedbackBound = "true";
            toggle.addEventListener("click", function (event) {
                if (activeGroups.has(group)) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                }
            });
        }
    });
}());
