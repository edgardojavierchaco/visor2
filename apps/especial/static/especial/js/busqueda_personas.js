(function () {
    "use strict";

    function buildFormUrl(form) {
        var url = new URL(form.getAttribute("action"), window.location.href);
        new FormData(form).forEach(function (value, key) {
            url.searchParams.set(key, value);
        });
        return url.toString();
    }

    function fetchRequest(url, options, waitForPaint) {
        var request = Object.assign({}, options || {});
        if (!request.credentials) request.credentials = "same-origin";
        if (!waitForPaint || typeof window.requestAnimationFrame !== "function") {
            return fetch(url, request);
        }
        return new Promise(function (resolve, reject) {
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    fetch(url, request).then(resolve, reject);
                });
            });
        });
    }

    function parseResponse(response, errorMessage) {
        if (!response.ok) {
            var message = errorMessage || "La operación devolvió un error HTTP.";
            throw new Error(message + " (HTTP " + response.status + ").");
        }
        var contentType = response.headers.get("content-type") || "";
        if (contentType.indexOf("application/json") !== -1) {
            return response.json().then(function (data) {
                return { json: data, redirected: response.redirected, url: response.url };
            });
        }
        return response.text().then(function (html) {
            return { html: html, redirected: response.redirected, url: response.url };
        });
    }

    function destroyUI(root) {
        if (window.EspecialUI && typeof window.EspecialUI.destroy === "function") {
            window.EspecialUI.destroy(root);
        }
    }

    function initUI(root) {
        if (window.EspecialUI && typeof window.EspecialUI.init === "function") {
            window.EspecialUI.init(root);
        }
    }

    function focusSearchInput(modal, selector) {
        if (!modal || !selector) return;
        var input = modal.querySelector(selector);
        if (input) input.focus();
    }

    function replaceModalDialog(modal, html, options) {
        if (!modal || typeof html !== "string") return false;
        var config = options || {};
        var responseDocument = new DOMParser().parseFromString(html, "text/html");
        var incomingModal = responseDocument.getElementById(config.modalId || modal.id);
        var dialogSelector = config.dialogSelector || ".cef-modal, .cef-docente-modal";
        var currentDialog = modal.querySelector(dialogSelector);
        var incomingDialog = incomingModal ? incomingModal.querySelector(dialogSelector) : null;
        if (!currentDialog || !incomingDialog) return false;

        destroyUI(currentDialog);
        var nodes = [];
        incomingDialog.childNodes.forEach(function (node) {
            if (node.nodeType === 1 && node.tagName === "SCRIPT") return;
            nodes.push(document.importNode(node, true));
        });
        currentDialog.replaceChildren.apply(currentDialog, nodes);
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        if (config.historyUrl && window.history && window.history.replaceState) {
            window.history.replaceState({}, "", config.historyUrl);
        }
        initUI(modal);
        focusSearchInput(modal, config.focusSelector === undefined ? "input[name='cuil']" : config.focusSelector);
        return true;
    }

    function replaceFragment(selector, html) {
        var current = selector ? document.querySelector(selector) : null;
        if (!current || typeof html !== "string") return null;
        var template = document.createElement("template");
        template.innerHTML = html;
        template.content.querySelectorAll("script").forEach(function (script) { script.remove(); });
        destroyUI(current);
        current.replaceChildren(template.content.cloneNode(true));
        initUI(current);
        return current;
    }

    function replacePanel(html) {
        if (typeof html !== "string") return null;
        var responseDocument = new DOMParser().parseFromString(html, "text/html");
        var incomingPanel = responseDocument.querySelector(".cef-panel");
        var currentPanel = document.querySelector(".cef-panel");
        if (!incomingPanel || !currentPanel) return null;
        var newPanel = document.importNode(incomingPanel, true);
        destroyUI(currentPanel);
        currentPanel.replaceWith(newPanel);
        initUI(newPanel);
        return newPanel;
    }

    window.EspecialBusquedaPersonas = {
        buildFormUrl: buildFormUrl,
        fetchRequest: fetchRequest,
        parseResponse: parseResponse,
        replaceModalDialog: replaceModalDialog,
        replaceFragment: replaceFragment,
        replacePanel: replacePanel,
        focusSearchInput: focusSearchInput
    };
})();
