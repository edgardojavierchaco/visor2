(function () {
    "use strict";

    var changedButtons = [];

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
        restoreButton: restoreButton,
        startButton: setButtonLoading,
        submitForm: submitForm
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
    window.addEventListener("pageshow", restore);
})();
