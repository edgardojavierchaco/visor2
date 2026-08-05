(function () {
    "use strict";

    if (window.cefProfesoresGlobalReady) return;
    window.cefProfesoresGlobalReady = true;

    function asignarModal() {
        return document.getElementById("modalAsignarProfesorGrupo");
    }

    function bajaModal() {
        return document.getElementById("modalBajaProfesorCef");
    }

    function setText(modal, selector, value) {
        var el = modal.querySelector(selector);
        if (el) el.textContent = value || "";
    }

    function setValue(modal, selector, value) {
        var el = modal.querySelector(selector);
        if (el) el.value = value || "";
    }

    function openAsignarModal(modal, trigger) {
        setValue(modal, "[data-cef-asignar-grupo-id]", trigger.dataset.grupoId);
        setValue(modal, "[data-cef-asignar-docente-cuil]", trigger.dataset.docenteCuil);
        setText(modal, "[data-cef-asignar-grupo-label]", "Grupo: " + trigger.dataset.grupoLabel);
        setText(
            modal,
            "[data-cef-asignar-docente-label]",
            "Profesor: " + (trigger.dataset.docenteNombre || "Profesor") + " - CUIL " + trigger.dataset.docenteCuil
        );
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
    }

    function closeAsignarModal(modal) {
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
    }

    function openBajaModal(modal, trigger) {
        var template = document.getElementById(trigger.dataset.templateId);
        var content = modal.querySelector("[data-cef-baja-content]");
        if (!template || !content) return false;
        content.innerHTML = template.innerHTML;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        return true;
    }

    function closeBajaModal(modal) {
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
    }

    function replaceProfesorFragment(selector, html) {
        var current = selector ? document.querySelector(selector) : null;
        if (!current || typeof html !== "string") return false;
        if (window.CEFSelects) window.CEFSelects.destroy(current);
        current.innerHTML = html;
        if (window.initCefProfesoresTable) {
            window.initCefProfesoresTable(current);
        }
        if (window.initCefSelects) window.initCefSelects(current);
        return true;
    }

    function replaceAsignarModal(html) {
        var modal = asignarModal();
        var doc = new DOMParser().parseFromString(html, "text/html");
        var incomingModal = doc.getElementById("modalAsignarProfesorGrupo");
        var currentDialog = modal ? modal.querySelector(".cef-docente-modal") : null;
        var incomingDialog = incomingModal ? incomingModal.querySelector(".cef-docente-modal") : null;
        if (!modal || !currentDialog || !incomingDialog) return false;
        if (window.CEFSelects) window.CEFSelects.destroy(currentDialog);
        currentDialog.innerHTML = incomingDialog.innerHTML;
        if (window.initCefSelects) window.initCefSelects(currentDialog);
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        return true;
    }

    function replaceBajaModal(html) {
        var modal = bajaModal();
        var doc = new DOMParser().parseFromString(html, "text/html");
        var incomingModal = doc.getElementById("modalBajaProfesorCef");
        var currentDialog = modal ? modal.querySelector(".cef-docente-modal") : null;
        var incomingDialog = incomingModal ? incomingModal.querySelector(".cef-docente-modal") : null;
        if (!modal || !currentDialog || !incomingDialog) return false;
        currentDialog.innerHTML = incomingDialog.innerHTML;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        return true;
    }

    document.addEventListener("click", function (event) {
        var trigger = event.target.closest("[data-cef-asignar-grupo-open]");
        if (trigger) {
            if (trigger.classList.contains("disabled") || trigger.getAttribute("aria-disabled") === "true" || !trigger.dataset.grupoId) {
                event.preventDefault();
                return;
            }

            var modal = asignarModal();
            if (!modal) return;
            event.preventDefault();
            if (window.CEFDropdowns) window.CEFDropdowns.closeAll();
            openAsignarModal(modal, trigger);
            return;
        }

        var bajaTrigger = event.target.closest("[data-cef-baja-open]");
        if (bajaTrigger) {
            var modalBaja = bajaModal();
            if (!modalBaja) return;
            if (openBajaModal(modalBaja, bajaTrigger)) {
                event.preventDefault();
                if (window.CEFDropdowns) window.CEFDropdowns.closeAll();
            }
            return;
        }

        var currentModal = asignarModal();
        if (currentModal && (event.target === currentModal || event.target.closest("[data-cef-asignar-grupo-close]"))) {
            event.preventDefault();
            closeAsignarModal(currentModal);
            return;
        }


        var currentBajaModal = bajaModal();
        if (currentBajaModal && (event.target === currentBajaModal || event.target.closest("[data-cef-baja-close]"))) {
            event.preventDefault();
            closeBajaModal(currentBajaModal);
            return;
        }

    });

    document.addEventListener("submit", function (event) {
        var form = event.target.closest("[data-cef-asignar-grupo-form]");
        if (!form) return;

        event.preventDefault();
        var submitBtn = form.querySelector("button[type='submit']");
        if (submitBtn) submitBtn.disabled = true;

        fetch(form.getAttribute("action"), {
            method: "POST",
            body: new FormData(form),
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin"
        })
            .then(function (response) {
                if (!response.ok) throw new Error("No se pudo guardar.");
                var contentType = response.headers.get("content-type") || "";
                if (contentType.indexOf("application/json") === -1) {
                    return response.text().then(function (html) {
                        return { fallback_html: html, close_modal: response.redirected };
                    });
                }
                return response.json();
            })
            .then(function (data) {
                if (data.fragment_html) {
                    if (!replaceProfesorFragment(data.fragment_selector, data.fragment_html)) {
                        form.submit();
                        return;
                    }
                    if (data.close_modal) {
                        closeAsignarModal(asignarModal());
                    } else if (data.modal_html) {
                        replaceAsignarModal(data.modal_html);
                    }
                    return;
                }
                if (data.modal_html && replaceAsignarModal(data.modal_html)) {
                    return;
                }
                if (data.fallback_html) {
                    window.location.reload();
                    return;
                }
                form.submit();
            })
            .catch(function () {
                form.submit();
            })
            .finally(function () {
                if (submitBtn) submitBtn.disabled = false;
            });
    });

    document.addEventListener("submit", function (event) {
        var form = event.target.closest("[data-cef-baja-form]");
        if (!form) return;

        event.preventDefault();
        var submitBtn = form.querySelector("button[type='submit']");
        if (submitBtn) submitBtn.disabled = true;

        fetch(form.getAttribute("action"), {
            method: "POST",
            body: new FormData(form),
            headers: { "X-Requested-With": "XMLHttpRequest" },
            credentials: "same-origin"
        })
            .then(function (response) {
                if (!response.ok) throw new Error("No se pudo guardar.");
                return response.json();
            })
            .then(function (data) {
                if (!replaceProfesorFragment(data.fragment_selector, data.fragment_html)) {
                    form.submit();
                    return;
                }
                if (data.close_modal) {
                    closeBajaModal(bajaModal());
                } else if (data.modal_html) {
                    replaceBajaModal(data.modal_html);
                }
            })
            .catch(function () {
                form.submit();
            })
            .finally(function () {
                if (submitBtn) submitBtn.disabled = false;
            });
    });

})();
