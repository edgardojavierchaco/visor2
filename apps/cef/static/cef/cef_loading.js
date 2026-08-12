(function () {
    "use strict";

    var changedButtons = [];
    var pageLoadingNode = null;
    var pageLoadingHost = null;

    function getSubmitLabel(text) {
        text = (text || "").trim().toLowerCase();

        if (text.indexOf("guardar") !== -1) return "Guardando...";
        if (text.indexOf("agregar") !== -1) return "Agregando...";
        if (text.indexOf("eliminar") !== -1) return "Eliminando...";
        if (text.indexOf("asignar") !== -1 || text.indexOf("asociar") !== -1) return "Asignando...";
        if (text.indexOf("inscribir") !== -1 || text.indexOf("reinscribir") !== -1) return "Inscribiendo...";
        if (text.indexOf("aplicar") !== -1 || text.indexOf("marcar") !== -1) return "Aplicando...";
        return "Procesando...";
    }

    function setButtonLoading(button) {
        if (!button || button.disabled || button.dataset.cefLoadingButton === "1") return false;

        var width = button.getBoundingClientRect().width;
        var loadingLabel = getSubmitLabel(button.textContent);
        changedButtons.push({
            button: button,
            html: button.innerHTML,
            minWidth: button.style.minWidth,
            disabled: button.disabled
        });

        button.dataset.cefLoadingButton = "1";
        button.style.minWidth = Math.ceil(width) + "px";
        button.disabled = true;
        button.setAttribute("aria-disabled", "true");
        button.classList.add("cef-submit-loading");
        button.replaceChildren();

        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm me-2";
        spinner.setAttribute("aria-hidden", "true");
        button.appendChild(spinner);
        button.appendChild(document.createTextNode(loadingLabel));
        return true;
    }

    function restoreButton(button) {
        changedButtons = changedButtons.filter(function (state) {
            if (state.button !== button) return true;

            state.button.innerHTML = state.html;
            state.button.style.minWidth = state.minWidth;
            state.button.disabled = state.disabled;
            state.button.classList.remove("cef-submit-loading");
            state.button.removeAttribute("aria-disabled");
            delete state.button.dataset.cefLoadingButton;
            return false;
        });
    }

    function restore() {
        document.querySelectorAll("form[data-cef-submitting='1']").forEach(function (form) {
            delete form.dataset.cefSubmitting;
        });

        changedButtons.forEach(function (state) {
            if (!state.button) return;
            state.button.innerHTML = state.html;
            state.button.style.minWidth = state.minWidth;
            state.button.disabled = state.disabled;
            state.button.classList.remove("cef-submit-loading");
            state.button.removeAttribute("aria-disabled");
            delete state.button.dataset.cefLoadingButton;
        });
        changedButtons = [];
    }

    function isNormalNavigationClick(event, link) {
        if (!link || event.defaultPrevented || event.button !== 0) return false;
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return false;
        if (link.hasAttribute("download") || link.hasAttribute("data-bs-toggle")) return false;
        if ((link.getAttribute("target") || "_self").toLowerCase() !== "_self") return false;

        var href = (link.getAttribute("href") || "").trim();
        if (!href || href.charAt(0) === "#" || href.toLowerCase().indexOf("javascript:") === 0) return false;

        var url = new URL(link.href, window.location.href);
        return url.origin === window.location.origin
            && url.href !== window.location.href;
    }

    function showPageLoading() {
        if (pageLoadingNode && pageLoadingNode.isConnected) return;

        var loading = document.createElement("div");
        var spinner = document.createElement("span");
        var label = document.createElement("span");
        loading.className = "cef-page-loading";
        loading.setAttribute("role", "status");
        loading.setAttribute("aria-live", "polite");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("aria-hidden", "true");
        label.textContent = "Cargando...";
        loading.append(spinner, label);
        pageLoadingHost = document.getElementById("cef-content-region")
            || document.querySelector(".padron-page-wrapper > .card")
            || document.querySelector(".content-wrapper > .content");
        if (pageLoadingHost) {
            pageLoadingHost.classList.add("cef-page-loading-host");
            pageLoadingHost.appendChild(loading);
        } else {
            loading.classList.add("is-fixed");
            document.body.appendChild(loading);
        }
        pageLoadingNode = loading;
    }

    function hidePageLoading() {
        if (pageLoadingNode && pageLoadingNode.isConnected) {
            pageLoadingNode.remove();
        }
        if (pageLoadingHost) {
            pageLoadingHost.classList.remove("cef-page-loading-host");
        }
        pageLoadingHost = null;
        pageLoadingNode = null;
    }

    function findSubmitter(event, form) {
        if (event.submitter) return event.submitter;
        if (document.activeElement && document.activeElement.form === form) return document.activeElement;
        return form.querySelector("button:not([type]), button[type='submit'], input[type='submit']");
    }

    function afterRepaint(callback) {
        window.requestAnimationFrame(function () {
            window.requestAnimationFrame(callback);
        });
    }

    function prepareSubmit(form, button) {
        if (!form || form.dataset.cefSubmitting === "1") return false;
        form.dataset.cefSubmitting = "1";
        setButtonLoading(button || form.querySelector("button:not([type]), button[type='submit'], input[type='submit']"));
        return true;
    }

    function submitForm(form, button) {
        if (!form || !form.checkValidity()) {
            if (form) form.reportValidity();
            return;
        }
        if (!prepareSubmit(form, button)) return;
        afterRepaint(function () {
            HTMLFormElement.prototype.submit.call(form);
        });
    }

    function init() {
        document.addEventListener("click", function (event) {
            var target = event.target;
            var link = target && target.closest ? target.closest("[data-cef-page-loading-link]") : null;
            if (isNormalNavigationClick(event, link)) showPageLoading();
        }, true);

        document.addEventListener("submit", function (event) {
            var form = event.target;
            if (event.defaultPrevented || !form.closest(".cef-wrap")) return;
            if ((form.method || "get").toLowerCase() !== "post") return;

            if (form.dataset.cefSubmitting === "1") {
                event.preventDefault();
                return;
            }

            if (!form.checkValidity()) {
                event.preventDefault();
                form.reportValidity();
                return;
            }

            event.preventDefault();
            if (!prepareSubmit(form, findSubmitter(event, form))) return;
            afterRepaint(function () {
                HTMLFormElement.prototype.submit.call(form);
            });
        });
    }

    window.CEFLoading = {
        hide: restore,
        showPage: showPageLoading,
        hidePage: hidePageLoading,
        restoreButton: restoreButton,
        startButton: setButtonLoading,
        submitForm: submitForm
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
    window.addEventListener("pageshow", function () {
        restore();
        hidePageLoading();
    });
})();
