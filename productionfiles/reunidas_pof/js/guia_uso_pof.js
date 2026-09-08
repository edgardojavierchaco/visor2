(function () {
    "use strict";

    const modal = document.querySelector("[data-pof-guide-modal]");

    if (!modal || modal.dataset.pofGuideBound === "true") {
        return;
    }

    const openButton = document.querySelector("[data-pof-guide-open]");
    let lastFocusedElement = null;

    /** Abre la ayuda de la pantalla actual y conserva el foco de origen. */
    function openGuide() {
        lastFocusedElement = document.activeElement;
        modal.classList.remove("pof-hidden");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("pof-modal-open");
        modal.querySelector("[data-pof-guide-close]").focus();
    }

    /** Cierra la ayuda y devuelve el foco al control que la abrió. */
    function closeGuide() {
        modal.classList.add("pof-hidden");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("pof-modal-open");
        const focusTarget = lastFocusedElement && lastFocusedElement.isConnected
            ? lastFocusedElement
            : openButton;
        if (focusTarget) {
            focusTarget.focus();
        }
    }

    openButton?.addEventListener("click", openGuide);

    modal.querySelectorAll("[data-pof-guide-close]").forEach(function (button) {
        button.addEventListener("click", closeGuide);
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeGuide();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.classList.contains("pof-hidden")) {
            closeGuide();
        }
    });

    modal.dataset.pofGuideBound = "true";
})();
