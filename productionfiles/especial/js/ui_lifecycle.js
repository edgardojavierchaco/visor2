(function () {
    "use strict";

    var installed = false;

    function install() {
        if (installed) return;
        installed = true;
        if (window.EspecialDropdowns && typeof window.EspecialDropdowns.install === "function") {
            window.EspecialDropdowns.install();
        }
        if (window.EspecialAlumnos && typeof window.EspecialAlumnos.install === "function") {
            window.EspecialAlumnos.install();
        }
        if (window.EspecialDocentes && typeof window.EspecialDocentes.install === "function") {
            window.EspecialDocentes.install();
        }
    }

    function init(root) {
        if (window.EspecialTableControls && typeof window.EspecialTableControls.init === "function") {
            window.EspecialTableControls.init(root);
        }
        if (window.EspecialContextSelector && typeof window.EspecialContextSelector.init === "function") {
            window.EspecialContextSelector.init(root);
        }
        if (window.EspecialAlumnos && typeof window.EspecialAlumnos.init === "function") {
            window.EspecialAlumnos.init(root);
        }
        if (window.EspecialDocentes && typeof window.EspecialDocentes.init === "function") {
            window.EspecialDocentes.init(root);
        }
    }

    function destroy(root) {
        if (window.EspecialContextSelector && typeof window.EspecialContextSelector.destroy === "function") {
            window.EspecialContextSelector.destroy(root);
        }
        if (window.EspecialAlumnos && typeof window.EspecialAlumnos.destroy === "function") {
            window.EspecialAlumnos.destroy(root);
        }
        if (window.EspecialDocentes && typeof window.EspecialDocentes.destroy === "function") {
            window.EspecialDocentes.destroy(root);
        }
    }

    window.EspecialUI = {
        install: install,
        init: init,
        destroy: destroy
    };

    function bootstrap() {
        install();
        init(document);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
    } else {
        bootstrap();
    }
})();
