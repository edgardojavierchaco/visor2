(function () {
    "use strict";

    var DESCRIPTORS = [
        {
            dropdownSelector: "[data-cef-alumno-dropdown]",
            toggleSelector: "[data-cef-alumno-dropdown-toggle]",
            menuSelector: "[data-cef-alumno-dropdown-menu]",
            menuWidth: 320,
            withinTable: true
        },
        {
            dropdownSelector: "[data-cef-profesor-dropdown]",
            toggleSelector: "[data-cef-profesor-dropdown-toggle]",
            menuSelector: "[data-cef-profesor-dropdown-menu]",
            menuWidth: 320,
            withinTable: false
        },
        {
            dropdownSelector: "[data-cef-row-actions]",
            toggleSelector: "[data-cef-row-actions-toggle]",
            menuSelector: "[data-cef-row-actions-menu]",
            menuWidth: 220,
            withinTable: true
        }
    ];
    var installed = false;
    var activeDropdown = null;

    function menuFor(dropdown, descriptor) {
        if (!dropdown) return null;
        return dropdown.__cefPortalMenu || dropdown.querySelector(descriptor.menuSelector);
    }

    function isDocentesRowActions(dropdown, descriptor) {
        return descriptor.dropdownSelector === "[data-cef-row-actions]"
            && dropdown
            && dropdown.closest(".cef-docentes-panel");
    }

    function isAlumnosRowActions(dropdown, descriptor) {
        return descriptor.dropdownSelector === "[data-cef-row-actions]"
            && dropdown
            && dropdown.closest(".cef-alumnos-table");
    }

    function isDocentesProfessorDropdown(dropdown, descriptor) {
        return descriptor.dropdownSelector === "[data-cef-profesor-dropdown]"
            && dropdown
            && dropdown.closest(".cef-docentes-row-actions-portal");
    }

    function containsDropdown(dropdown, current) {
        return dropdown === current
            || dropdown.contains(current)
            || (dropdown.__cefPortalMenu && dropdown.__cefPortalMenu.contains(current));
    }

    function portalMenu(dropdown, menu, descriptor) {
        if (!isDocentesRowActions(dropdown, descriptor) || menu.__cefPortalState) return;
        menu.__cefPortalState = {
            parent: menu.parentNode,
            nextSibling: menu.nextSibling,
            dropdown: dropdown
        };
        menu.__cefPortalOwner = dropdown;
        menu.classList.add("cef-docentes-row-actions-portal");
        document.body.appendChild(menu);
        dropdown.__cefPortalMenu = menu;
    }

    function restoreMenu(menu) {
        var state = menu && menu.__cefPortalState;
        if (!state) return;
        if (state.parent && state.parent.isConnected) {
            state.parent.insertBefore(menu, state.nextSibling && state.nextSibling.parentNode === state.parent
                ? state.nextSibling
                : null);
        } else {
            menu.remove();
        }
        menu.__cefPortalState = null;
        menu.__cefPortalOwner = null;
        menu.classList.remove("cef-docentes-row-actions-portal");
        if (state.dropdown) state.dropdown.__cefPortalMenu = null;
    }

    function closeDropdown(dropdown, descriptor) {
        if (!dropdown) return;
        var toggle = dropdown.querySelector(descriptor.toggleSelector);
        var menu = menuFor(dropdown, descriptor);
        if (toggle) toggle.setAttribute("aria-expanded", "false");
        if (menu) {
            menu.classList.remove("show");
            menu.removeAttribute("style");
            restoreMenu(menu);
        }
        if (activeDropdown && activeDropdown.dropdown === dropdown) activeDropdown = null;
    }

    function descriptorForToggle(toggle) {
        for (var i = 0; i < DESCRIPTORS.length; i += 1) {
            if (toggle.matches(DESCRIPTORS[i].toggleSelector)) return DESCRIPTORS[i];
        }
        return null;
    }

    function closeAll(current) {
        DESCRIPTORS.forEach(function (descriptor) {
            document.querySelectorAll(descriptor.dropdownSelector).forEach(function (dropdown) {
                if (!containsDropdown(dropdown, current)) closeDropdown(dropdown, descriptor);
            });
        });
    }

    function positionMenu(toggle, menu, descriptor) {
        var rect = toggle.getBoundingClientRect();
        var tableWrap = descriptor.withinTable ? toggle.closest(".cef-table-wrap") : null;
        var bounds = tableWrap ? tableWrap.getBoundingClientRect() : {
            left: 12,
            right: window.innerWidth - 12
        };
        var menuWidth = Math.min(descriptor.menuWidth, window.innerWidth - 24);
        if (isDocentesProfessorDropdown(toggle.closest(descriptor.dropdownSelector), descriptor)) {
            var professorPadding = 8;
            var professorGap = 8;
            var professorWidth = Math.min(
                menu.getBoundingClientRect().width || menuWidth,
                window.innerWidth - professorPadding * 2
            );
            var professorHeight = menu.getBoundingClientRect().height || 180;
            var professorLeftPosition = rect.left - professorWidth - professorGap;
            professorLeftPosition = Math.max(
                professorPadding,
                Math.min(professorLeftPosition, window.innerWidth - professorPadding - professorWidth)
            );
            var professorBelow = window.innerHeight - rect.top - professorPadding;
            var professorAbove = rect.bottom - professorPadding;
            var professorUp = professorBelow < professorHeight && professorAbove > professorBelow;
            var professorAvailable = Math.max(40, professorUp ? professorAbove : professorBelow);
            var professorMenuHeight = Math.min(professorHeight, professorAvailable);
            var professorTop = professorUp
                ? rect.bottom - professorMenuHeight
                : rect.top;
            professorTop = Math.max(
                professorPadding,
                Math.min(professorTop, window.innerHeight - professorPadding - professorMenuHeight)
            );
            menu.style.position = "fixed";
            menu.style.left = professorLeftPosition + "px";
            menu.style.right = "auto";
            menu.style.top = professorTop + "px";
            menu.style.bottom = "auto";
            menu.style.width = professorWidth + "px";
            menu.style.maxHeight = professorMenuHeight + "px";
            menu.style.overflowY = professorHeight > professorMenuHeight ? "auto" : "visible";
            menu.style.zIndex = "1091";
            return;
        }
        if (isAlumnosRowActions(toggle.closest(descriptor.dropdownSelector), descriptor)) {
            var alumnosPadding = 8;
            var alumnosGap = 8;
            var alumnosWidth = Math.min(descriptor.menuWidth, window.innerWidth - alumnosPadding * 2);
            menu.style.visibility = "hidden";
            menu.style.maxHeight = "none";
            menu.style.overflowY = "visible";
            var alumnosMeasured = menu.getBoundingClientRect();
            var alumnosHeight = Math.max(alumnosMeasured.height, menu.scrollHeight, 1);
            var alumnosBelow = window.innerHeight - rect.bottom - alumnosPadding - alumnosGap;
            var alumnosAbove = rect.top - alumnosPadding - alumnosGap;
            var alumnosUp = alumnosBelow < alumnosHeight;
            var alumnosAvailable = Math.max(40, alumnosUp ? alumnosAbove : alumnosBelow);
            var alumnosMenuHeight = Math.min(alumnosHeight, alumnosAvailable);
            var alumnosTop = alumnosUp
                ? rect.top - alumnosGap - alumnosMenuHeight
                : rect.bottom + alumnosGap;
            alumnosTop = Math.max(
                alumnosPadding,
                Math.min(alumnosTop, window.innerHeight - alumnosPadding - alumnosMenuHeight)
            );
            var alumnosLeft = Math.max(
                alumnosPadding,
                Math.min(rect.right - alumnosWidth, window.innerWidth - alumnosPadding - alumnosWidth)
            );
            menu.style.position = "fixed";
            menu.style.left = alumnosLeft + "px";
            menu.style.right = "auto";
            var alumnosUseBottom = alumnosUp && alumnosTop >= alumnosPadding;
            if (alumnosUseBottom) {
                menu.style.top = "auto";
                menu.style.bottom = (window.innerHeight - rect.top + alumnosGap) + "px";
            } else {
                menu.style.top = alumnosTop + "px";
                menu.style.bottom = "auto";
            }
            menu.style.width = alumnosWidth + "px";
            menu.style.maxHeight = alumnosMenuHeight + "px";
            menu.style.overflowY = alumnosHeight > alumnosMenuHeight ? "auto" : "visible";
            menu.style.visibility = "visible";
            menu.style.zIndex = "1090";
            return;
        }
        if (isDocentesRowActions(toggle.closest(descriptor.dropdownSelector), descriptor)) {
            var docentesPadding = 8;
            var docentesGap = 4;
            var docentesWidth = Math.min(descriptor.menuWidth, window.innerWidth - docentesPadding * 2);
            var docentesHeight = menu.getBoundingClientRect().height || 200;
            var docentesBelow = window.innerHeight - rect.bottom - docentesPadding - docentesGap;
            var docentesAbove = rect.top - docentesPadding - docentesGap;
            var docentesUp = docentesBelow < docentesHeight && docentesAbove > docentesBelow;
            var docentesAvailable = Math.max(40, docentesUp ? docentesAbove : docentesBelow);
            var docentesMenuHeight = Math.min(docentesHeight, docentesAvailable);
            var docentesTop = docentesUp
                ? rect.top - docentesGap - docentesMenuHeight
                : rect.bottom + docentesGap;
            docentesTop = Math.max(
                docentesPadding,
                Math.min(docentesTop, window.innerHeight - docentesPadding - docentesMenuHeight)
            );
            var docentesLeft = Math.max(
                docentesPadding,
                Math.min(rect.right - docentesWidth, window.innerWidth - docentesPadding - docentesWidth)
            );
            menu.style.position = "fixed";
            menu.style.left = "auto";
            menu.style.right = "auto";
            menu.style.top = docentesTop + "px";
            menu.style.bottom = "auto";
            menu.style.left = docentesLeft + "px";
            menu.style.width = docentesWidth + "px";
            menu.style.maxHeight = docentesMenuHeight + "px";
            menu.style.overflowY = docentesHeight > docentesMenuHeight ? "auto" : "visible";
            menu.style.zIndex = "1090";
            return;
        }
        if (descriptor.dropdownSelector !== "[data-cef-alumno-dropdown]") {
            var sectionLeft = Math.min(rect.left, bounds.right - menuWidth - 8);
            menu.style.position = "fixed";
            menu.style.top = (rect.bottom + 4) + "px";
            menu.style.left = Math.max(bounds.left + 8, sectionLeft) + "px";
            menu.style.width = menuWidth + "px";
            menu.style.zIndex = "1090";
            return;
        }
        var viewportPadding = 8;
        var menuHeight = menu.getBoundingClientRect().height || 240;
        var spaceBelow = window.innerHeight - rect.bottom - viewportPadding;
        var spaceAbove = rect.top - viewportPadding;
        var opensUp = spaceBelow < menuHeight && spaceAbove > spaceBelow;
        var top = opensUp ? rect.top - Math.min(menuHeight, spaceAbove) : rect.bottom + 4;
        var left = rect.left;

        if (descriptor.dropdownSelector === "[data-cef-alumno-dropdown]") {
            var spaceRight = window.innerWidth - rect.right - viewportPadding;
            var spaceLeft = rect.left - viewportPadding;
            if (spaceRight < menuWidth && spaceLeft >= menuWidth) {
                left = rect.left - menuWidth - 4;
            } else if (spaceRight >= menuWidth) {
                left = rect.right + 4;
                top = Math.max(viewportPadding, Math.min(rect.top, window.innerHeight - menuHeight - viewportPadding));
            }
        }

        var maxTop = Math.max(viewportPadding, window.innerHeight - Math.min(menuHeight, window.innerHeight - viewportPadding * 2) - viewportPadding);
        top = Math.max(viewportPadding, Math.min(top, maxTop));
        left = Math.min(left, bounds.right - menuWidth - viewportPadding);
        left = Math.max(viewportPadding, left);
        menu.style.position = "fixed";
        menu.style.top = top + "px";
        menu.style.left = left + "px";
        menu.style.width = menuWidth + "px";
        menu.style.maxHeight = Math.max(120, window.innerHeight - top - viewportPadding) + "px";
        menu.style.overflowY = "auto";
        menu.style.zIndex = "1090";
    }

    function repositionActive() {
        if (!activeDropdown || !activeDropdown.toggle || !activeDropdown.menu
            || !activeDropdown.toggle.isConnected || !activeDropdown.menu.isConnected
            || !activeDropdown.menu.classList.contains("show")) return;
        positionMenu(activeDropdown.toggle, activeDropdown.menu, activeDropdown.descriptor);
    }

    function handleViewportChange() {
        if (activeDropdown && (
            isAlumnosRowActions(activeDropdown.dropdown, activeDropdown.descriptor)
            ||
            isDocentesRowActions(activeDropdown.dropdown, activeDropdown.descriptor)
            || isDocentesProfessorDropdown(activeDropdown.dropdown, activeDropdown.descriptor)
        )) {
            repositionActive();
        } else {
            closeAll(null);
        }
    }

    function cleanupOrphanPortals() {
        document.querySelectorAll(".cef-docentes-row-actions-portal").forEach(function (menu) {
            var owner = menu.__cefPortalOwner;
            if (!owner || !owner.isConnected) {
                if (activeDropdown && activeDropdown.menu === menu) activeDropdown = null;
                menu.remove();
            }
        });
    }

    function install() {
        if (installed) return;
        installed = true;

        document.addEventListener("click", function (event) {
            var target = event.target;
            var toggle = target && target.closest ? target.closest(
                "[data-cef-alumno-dropdown-toggle], "
                + "[data-cef-profesor-dropdown-toggle], "
                + "[data-cef-row-actions-toggle]"
            ) : null;
            if (toggle) {
                event.preventDefault();
                var descriptor = descriptorForToggle(toggle);
                var dropdown = descriptor ? toggle.closest(descriptor.dropdownSelector) : null;
                var menu = dropdown ? menuFor(dropdown, descriptor) : null;
                if (!descriptor || !dropdown || !menu) return;

                if (toggle.closest(".cef-docentes-panel")
                    && window.EspecialDocentes
                    && typeof window.EspecialDocentes.closeModalsForDropdown === "function") {
                    window.EspecialDocentes.closeModalsForDropdown();
                }

                var willOpen = !menu.classList.contains("show");
                if (!willOpen) {
                    closeDropdown(dropdown, descriptor);
                    return;
                }
                if (isDocentesRowActions(dropdown, descriptor)) closeAll(null);
                else closeAll(dropdown);
                portalMenu(dropdown, menu, descriptor);
                toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
                menu.classList.add("show");
                activeDropdown = { dropdown: dropdown, toggle: toggle, menu: menu, descriptor: descriptor };
                positionMenu(toggle, menu, descriptor);
                return;
            }

            var insideMenu = target && target.closest ? target.closest(
                "[data-cef-alumno-dropdown-menu], "
                + "[data-cef-profesor-dropdown-menu], "
                + "[data-cef-row-actions-menu]"
            ) : null;
            if (!insideMenu) {
                closeAll(null);
            } else if (insideMenu.__cefPortalOwner
                && !target.closest("[data-cef-profesor-dropdown-toggle]")) {
                closeDropdown(insideMenu.__cefPortalOwner, DESCRIPTORS[2]);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" || event.key === "Esc") closeAll(null);
        });
        window.addEventListener("scroll", handleViewportChange, true);
        window.addEventListener("resize", handleViewportChange);
        if (window.MutationObserver) {
            new MutationObserver(cleanupOrphanPortals).observe(document.body, { childList: true, subtree: true });
        }
    }

    window.EspecialDropdowns = {
        install: install,
        closeAll: function () { closeAll(null); },
        closeForElement: function (element) {
            if (!element || !element.closest) return;
            for (var i = 0; i < DESCRIPTORS.length; i += 1) {
                var descriptor = DESCRIPTORS[i];
                var dropdown = element.closest(descriptor.dropdownSelector);
                if (!dropdown && descriptor.dropdownSelector === "[data-cef-row-actions]") {
                    var portalMenu = element.closest(".cef-docentes-row-actions-portal");
                    dropdown = portalMenu && portalMenu.__cefPortalOwner;
                }
                if (dropdown) {
                    closeDropdown(dropdown, descriptor);
                    return;
                }
            }
        }
    };
})();
