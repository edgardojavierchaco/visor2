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

    function closeDropdown(dropdown, descriptor) {
        if (!dropdown) return;
        var toggle = dropdown.querySelector(descriptor.toggleSelector);
        var menu = dropdown.querySelector(descriptor.menuSelector);
        if (toggle) toggle.setAttribute("aria-expanded", "false");
        if (menu) {
            menu.classList.remove("show");
            menu.removeAttribute("style");
        }
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
                if (dropdown !== current) closeDropdown(dropdown, descriptor);
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
        var left = Math.min(rect.left, bounds.right - menuWidth - 8);
        menu.style.position = "fixed";
        menu.style.top = (rect.bottom + 4) + "px";
        menu.style.left = Math.max(bounds.left + 8, left) + "px";
        menu.style.width = menuWidth + "px";
        menu.style.zIndex = "1090";
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
                var menu = dropdown ? dropdown.querySelector(descriptor.menuSelector) : null;
                if (!descriptor || !dropdown || !menu) return;

                var willOpen = !menu.classList.contains("show");
                closeAll(dropdown);
                toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
                menu.classList.toggle("show", willOpen);
                if (willOpen) positionMenu(toggle, menu, descriptor);
                else menu.removeAttribute("style");
                return;
            }

            var insideMenu = target && target.closest ? target.closest(
                "[data-cef-alumno-dropdown-menu], "
                + "[data-cef-profesor-dropdown-menu], "
                + "[data-cef-row-actions-menu]"
            ) : null;
            if (!insideMenu) closeAll(null);
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" || event.key === "Esc") closeAll(null);
        });
        window.addEventListener("scroll", function () { closeAll(null); }, true);
        window.addEventListener("resize", function () { closeAll(null); });
    }

    window.EspecialDropdowns = {
        install: install,
        closeAll: function () { closeAll(null); }
    };
})();
