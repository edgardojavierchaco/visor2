(function () {
    "use strict";

    var selectSelector = "select[data-cef-select]";
    var jqueryUrl = "https://code.jquery.com/jquery-3.6.0.min.js";
    var select2Url = "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js";

    function loadScript(id, src, callback) {
        var script = document.getElementById(id) || document.querySelector('script[src="' + src + '"]');
        if (script) {
            script.addEventListener("load", callback, { once: true });
            return;
        }

        script = document.createElement("script");
        script.id = id;
        script.src = src;
        script.addEventListener("load", callback, { once: true });
        document.head.appendChild(script);
    }

    function ensureSelect2(callback) {
        function loadSelect2() {
            if (window.jQuery.fn && window.jQuery.fn.select2) {
                callback();
                return;
            }
            loadScript("cef-select2-script", select2Url, callback);
        }

        if (window.jQuery) {
            loadSelect2();
            return;
        }
        loadScript("cef-jquery-script", jqueryUrl, loadSelect2);
    }

    function selectsIn(root) {
        root = root || document;
        var selects = [];
        if (root.matches && root.matches(selectSelector)) selects.push(root);
        if (root.querySelectorAll) {
            selects = selects.concat(Array.prototype.slice.call(root.querySelectorAll(selectSelector)));
        }
        return selects;
    }

    function searchThreshold(select) {
        if (select.dataset.cefSelectSearch === "always") return 0;
        var explicit = Number(select.dataset.cefSelectSearchThreshold);
        if (Number.isFinite(explicit)) return explicit;
        return Infinity;
    }

    function dropdownParent(select) {
        if (select.dataset.cefSelectDropdownParent === "body") return null;
        return select.closest(".modal, .cef-docente-overlay, .cef-overlay")
            || select.closest("[role='dialog'][aria-modal='true']");
    }

    function visualViewportSize() {
        var viewport = window.visualViewport;
        return {
            width: viewport ? viewport.width : (document.documentElement.clientWidth || window.innerWidth),
            height: viewport ? viewport.height : (document.documentElement.clientHeight || window.innerHeight)
        };
    }

    function constrainOpenDropdown() {
        if (!window.jQuery) return;
        var size = visualViewportSize();
        var maxWidth = Math.max(0, size.width - 24);
        var maxHeight = Math.max(96, Math.min(320, size.height - 144));
        var $dropdown = window.jQuery(
            ".cef-select2-dropdown, .cef-bnh-select2-dropdown"
        ).last();
        $dropdown.css("max-width", maxWidth + "px");
        $dropdown.find(".select2-results__options").css("max-height", maxHeight + "px");
    }

    function addCloseAction(select, $select) {
        if (select.dataset.cefSelectCloseAction !== "true") return;

        var $ = window.jQuery;
        // Usar el dropdown vivo del DOM. La referencia interna de Select2 puede
        // apuntar a una plantilla/desplegable todavía no insertado.
        var $dropdown = $(".select2-container--open .select2-dropdown").last();
        if (!$dropdown.length) $dropdown = $(".select2-dropdown").last();
        if (!$dropdown.length) return;

        var $button = $dropdown.children(".cef-select2-close-options");
        if (!$button.length) {
            $button = $(
                '<button type="button" class="cef-select2-close-options">' +
                '<i class="fa-solid fa-chevron-up" aria-hidden="true"></i>' +
                '<span>Ocultar opciones</span>' +
                '</button>'
            );
            $dropdown.append($button);
        }

        $button
            .off(".cefSelectClose")
            .on("mousedown.cefSelectClose", function (event) {
                event.preventDefault();
            })
            .on("click.cefSelectClose", function (event) {
                event.preventDefault();
                event.stopPropagation();
                $select.select2("close");
            });
    }

    function initSelect(select) {
        if (!select.isConnected) return;
        var $ = window.jQuery;
        var $select = $(select);

        if (!$select.data("select2")) {
            var parent = dropdownParent(select);
            var config = {
                width: "100%",
                dropdownCssClass: select.dataset.cefSelectStyle === "bnh"
                    ? "cef-bnh-select2-dropdown"
                    : "cef-select2-dropdown",
                minimumResultsForSearch: searchThreshold(select),
                language: {
                    searching: function () { return "Buscando..."; },
                    noResults: function () { return "No se encontraron resultados"; }
                }
            };
            if (select.dataset.closeOnSelect === "false") config.closeOnSelect = false;
            if (select.dataset.closeOnSelect === "true") config.closeOnSelect = true;
            if (parent) config.dropdownParent = $(parent);
            $select.select2(config);
        }

        // Vincular siempre nuestros eventos, incluso si otro inicializador creó
        // Select2 previamente.
        $select.off(".cefSelect");
        $select.on("select2:open.cefSelect", function () {
            window.setTimeout(function () {
                constrainOpenDropdown();
                addCloseAction(select, $select);
            }, 0);
            window.setTimeout(function () {
                addCloseAction(select, $select);
            }, 30);
        });
        $select.on("select2:select.cefSelect select2:clear.cefSelect", function () {
            if (select.dataset.cefSelectNativeChange !== "true") return;
            select.dispatchEvent(new Event("change", { bubbles: true }));
        });
    }

    function initContextNavigation() {
        var form = document.querySelector("[data-cef-context-form]");
        if (!form) return;

        var selects = Array.prototype.slice.call(form.querySelectorAll("select[name]"));
        var activeValues = selects.map(function (select) {
            var selected = Array.prototype.find.call(select.options, function (option) {
                return option.defaultSelected;
            });
            return selected ? selected.value : (select.options.length ? select.options[0].value : "");
        });
        var status = form.querySelector("[data-cef-context-status]");
        var pending = false;
        var timer = null;
        var payload = [];
        var locked = [];
        var originalAction = form.getAttribute("action");
        var editedForms = new Map();

        function editableForm(target) {
            var candidate = target && target.closest ? target.closest("form") : null;
            return candidate && candidate.closest("[data-cef-content-region]")
                && candidate.method.toLowerCase() === "post"
                && !candidate.matches("[data-cef-asistencia-guardado]") ? candidate : null;
        }

        function values(candidate) {
            return JSON.stringify(Array.prototype.filter.call(candidate.elements, function (field) {
                return field.name && /^(INPUT|SELECT|TEXTAREA)$/.test(field.tagName)
                    && !/^(hidden|submit|button|reset)$/.test(field.type);
            }).map(function (field) {
                if (field.type === "checkbox" || field.type === "radio") {
                    return [field.name, field.value, field.checked];
                }
                if (field.tagName === "SELECT") {
                    return [field.name, Array.prototype.filter.call(field.options, function (option) {
                        return option.selected;
                    }).map(function (option) { return option.value; })];
                }
                return [field.name, field.value];
            }));
        }

        // Capture before editing, including forms inserted by partial navigation.
        // Programmatic modal prefills are not themselves unsaved user changes.
        function rememberForm(event) {
            var candidate = editableForm(event.target);
            if (candidate && !editedForms.has(candidate)) {
                editedForms.set(candidate, values(candidate));
            }
        }
        document.addEventListener("focusin", rememberForm, true);
        document.addEventListener("pointerdown", rememberForm, true);
        document.addEventListener("beforeinput", rememberForm, true);
        document.addEventListener("reset", function (event) {
            var candidate = editableForm(event.target);
            if (!candidate) return;
            window.setTimeout(function () {
                if (!event.defaultPrevented) editedForms.set(candidate, values(candidate));
            }, 0);
        });

        function hasUnsavedChanges() {
            var attendance = document.querySelector("[data-cef-asistencia-workspace]");
            if (attendance && attendance.dataset.cefAsistenciaDirty === "true") return true;
            var dirty = false;
            editedForms.forEach(function (initial, candidate) {
                if (!candidate.isConnected) editedForms.delete(candidate);
                else if (values(candidate) !== initial) dirty = true;
            });
            return dirty;
        }

        function restoreSelections() {
            selects.forEach(function (select, index) {
                select.value = activeValues[index];
                sync(select);
            });
        }

        function restore() {
            window.clearTimeout(timer);
            payload.forEach(function (field) { field.remove(); });
            payload = [];
            locked.forEach(function (state) {
                state.element.inert = state.inert;
                if (state.disabled !== undefined) state.element.disabled = state.disabled;
            });
            locked = [];
            if (originalAction === null) form.removeAttribute("action");
            else form.setAttribute("action", originalAction);
            form.removeAttribute("aria-busy");
            status.textContent = "";
            pending = false;
            restoreSelections();
        }

        function destination() {
            // The active shared menu follows partial navigation too. Its URL is
            // a context-independent list, never a group/student/detail route.
            var link = document.querySelector(".cef-module-nav .nav-link.active");
            var current = new URL(window.location.href);
            if (!link) throw new Error("No se encontró la sección CEF activa");
            var target = new URL(link.href, current);
            if (target.origin !== current.origin) throw new Error("Destino CEF inválido");
            var source = target.pathname === current.pathname ? current : target;
            var view = source.searchParams.get("vista");
            target.search = "";
            target.hash = "";
            return { url: target.href, view: /^(actuales|historial)$/.test(view) ? view : "" };
        }

        function addPayload(name, value) {
            var field = document.createElement("input");
            field.type = "hidden";
            field.name = name;
            field.value = value;
            form.appendChild(field);
            payload.push(field);
        }

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            if (pending) return;
            var requested = selects.map(function (select) { return select.value; });
            restoreSelections();
            if (requested.every(function (value, index) { return value === activeValues[index]; })) return;
            if (document.querySelector("[data-cef-content-region] form[data-cef-submitting='1']")) {
                status.textContent = "Esperá a que termine el guardado antes de cambiar el contexto.";
                return;
            }
            if (hasUnsavedChanges() && !window.confirm(
                "Hay cambios sin guardar. ¿Querés descartarlos y cambiar de CEF o ciclo?"
            )) return;

            try {
                var target = destination();
                pending = true;
                form.action = target.url;
                selects.forEach(function (select, index) { addPayload(select.name, requested[index]); });
                if (target.view) addPayload("vista", target.view);
                var wrap = form.closest(".cef-wrap");
                wrap.querySelectorAll(
                    ".cef-module-nav, [data-cef-content-region], .cef-confirm-modal, " +
                    "[data-cef-context-form] select, [data-cef-context-form] a"
                ).forEach(function (element) {
                    locked.push({ element: element, inert: element.inert, disabled: element.disabled });
                    element.inert = true;
                    if (element.tagName === "SELECT") {
                        element.disabled = true;
                        sync(element);
                        var $select = window.jQuery && window.jQuery(element);
                        if ($select && $select.data("select2")) $select.select2("close");
                    }
                });
                form.setAttribute("aria-busy", "true");
                status.textContent = "Cambiando CEF / ciclo…";
                timer = window.setTimeout(function () {
                    status.textContent = "La navegación está demorando. Esperá a que termine de cargar.";
                }, 15000);
                // Same normal GET submission as the former Apply button. Only
                // transient hidden inputs carry the requested, not yet applied values.
                HTMLFormElement.prototype.submit.call(form);
            } catch (error) {
                restore();
                status.textContent = "No se pudo cambiar el contexto. Volvé a intentarlo.";
            }
        });

        form.addEventListener("change", function (event) {
            if (selects.indexOf(event.target) === -1) return;
            if (pending) {
                restoreSelections();
                return;
            }
            form.requestSubmit();
        });
        // Browsers may restore form controls from history; server-rendered
        // selections remain authoritative, including when returning from an error.
        window.addEventListener("pageshow", restore);
        window.addEventListener("pagehide", function () { window.clearTimeout(timer); });
    }

    function init(root, callback) {
        var selects = selectsIn(root);
        if (!selects.length) {
            if (callback) callback();
            return;
        }

        ensureSelect2(function () {
            selects.forEach(initSelect);
            if (callback) callback();
        });
    }

    function destroy(root) {
        if (!window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
        selectsIn(root).forEach(function (select) {
            var $select = window.jQuery(select);
            if ($select.data("select2")) {
                $select.off(".cefSelect");
                $select.select2("destroy");
            }
        });
    }

    function sync(select) {
        if (!select || !window.jQuery) return;
        var $select = window.jQuery(select);
        if ($select.data("select2")) $select.trigger("change.select2");
    }

    function focus(select) {
        if (!select) return;
        init(select, function () {
            var instance = window.jQuery(select).data("select2");
            if (instance && instance.$selection) instance.$selection.trigger("focus");
            else select.focus();
        });
    }

    initContextNavigation();

    window.initCefSelects = init;
    window.CEFSelects = {
        destroy: destroy,
        focus: focus,
        init: init,
        sync: sync
    };

    window.addEventListener("resize", constrainOpenDropdown);
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", constrainOpenDropdown);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { init(document); }, { once: true });
    } else {
        init(document);
    }
})();
