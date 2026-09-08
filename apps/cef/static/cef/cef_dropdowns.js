(function () {
    "use strict";

    var dropdownTypes = [
        {
            root: "[data-cef-row-actions]",
            toggle: "[data-cef-row-actions-toggle]",
            menu: "[data-cef-row-actions-menu]",
            width: 220
        },
        {
            root: "[data-cef-alumno-dropdown]",
            toggle: "[data-cef-alumno-dropdown-toggle]",
            menu: "[data-cef-alumno-dropdown-menu]",
            width: 320
        },
        {
            root: "[data-cef-profesor-dropdown]",
            toggle: "[data-cef-profesor-dropdown-toggle]",
            menu: "[data-cef-profesor-dropdown-menu]",
            width: 320
        }
    ];

    var rootSelector = dropdownTypes.map(function (type) { return type.root; }).join(",");
    var toggleSelector = dropdownTypes.map(function (type) { return type.toggle; }).join(",");
    var menuSelector = dropdownTypes.map(function (type) { return type.menu; }).join(",");

    function typeForToggle(toggle) {
        return dropdownTypes.find(function (type) {
            return toggle.matches(type.toggle);
        }) || null;
    }

    function elements(dropdown, type) {
        return {
            toggle: dropdown ? dropdown.querySelector(type.toggle) : null,
            menu: dropdown ? dropdown.querySelector(type.menu) : null
        };
    }

    function close(dropdown) {
        var type = dropdownTypes.find(function (item) {
            return dropdown.matches(item.root);
        });
        if (!type) return;

        var parts = elements(dropdown, type);
        if (parts.toggle) parts.toggle.setAttribute("aria-expanded", "false");
        if (parts.menu) {
            parts.menu.classList.remove("show");
            parts.menu.removeAttribute("style");
        }
    }

    function closeAll(except) {
        document.querySelectorAll(rootSelector).forEach(function (dropdown) {
            if (dropdown !== except) close(dropdown);
        });
    }

    function position(toggle, menu, preferredWidth) {
        var rect = toggle.getBoundingClientRect();
        var tableWrap = toggle.closest(".cef-table-wrap");
        var tableBounds = tableWrap ? tableWrap.getBoundingClientRect() : null;
        var viewportWidth = document.documentElement.clientWidth || window.innerWidth;
        var viewportHeight = document.documentElement.clientHeight || window.innerHeight;
        var availableWidth = Math.max(0, viewportWidth - 24);
        var menuWidth = Math.min(preferredWidth, availableWidth);
        var left = Math.min(rect.left, viewportWidth - menuWidth - 12);

        if (tableBounds && tableBounds.width >= menuWidth + 16) {
            left = Math.min(left, tableBounds.right - menuWidth - 8);
            left = Math.max(tableBounds.left + 8, left);
        }

        menu.style.position = "fixed";
        left = Math.max(12, Math.min(left, viewportWidth - menuWidth - 12));
        menu.style.left = left + "px";
        menu.style.width = menuWidth + "px";
        menu.style.maxWidth = availableWidth + "px";
        menu.style.maxHeight = Math.max(0, viewportHeight - 24) + "px";
        menu.style.overflowY = "auto";
        menu.style.zIndex = "1090";

        var menuHeight = menu.getBoundingClientRect().height;
        var top = rect.bottom + 4;
        if (top + menuHeight > viewportHeight - 12 && rect.top - menuHeight - 4 >= 12) {
            top = rect.top - menuHeight - 4;
        }
        menu.style.top = Math.max(12, Math.min(top, viewportHeight - menuHeight - 12)) + "px";
    }

    function open(toggle, dropdown, type) {
        var parts = elements(dropdown, type);
        if (!parts.menu) return false;

        closeAll(dropdown);
        toggle.setAttribute("aria-expanded", "true");
        parts.menu.classList.add("show");
        position(toggle, parts.menu, type.width);
        return true;
    }

    document.addEventListener("click", function (event) {
        var toggle = event.target.closest(toggleSelector);
        if (toggle) {
            var type = typeForToggle(toggle);
            var dropdown = type ? toggle.closest(type.root) : null;
            var parts = dropdown && type ? elements(dropdown, type) : null;
            if (!dropdown || !parts.menu) return;

            event.preventDefault();
            if (parts.menu.classList.contains("show")) {
                close(dropdown);
            } else {
                open(toggle, dropdown, type);
            }
            return;
        }

        var menu = event.target.closest(menuSelector);
        if (!menu) {
            closeAll(null);
            return;
        }

        var action = event.target.closest(".dropdown-item");
        if (action && !action.classList.contains("disabled") && action.getAttribute("aria-disabled") !== "true") {
            closeAll(null);
        }
    });

    document.addEventListener("keydown", function (event) {
        var toggle = event.target.closest(toggleSelector);
        if (toggle && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
            var type = typeForToggle(toggle);
            var dropdown = type ? toggle.closest(type.root) : null;
            if (!dropdown || !open(toggle, dropdown, type)) return;

            event.preventDefault();
            var items = dropdown.querySelectorAll(".dropdown-item:not(.disabled):not([aria-disabled='true'])");
            var item = event.key === "ArrowUp" ? items[items.length - 1] : items[0];
            if (item) item.focus();
            return;
        }

        if (event.key !== "Escape") return;
        var current = event.target.closest(rootSelector);
        if (!current) return;
        var currentToggle = current.querySelector(toggleSelector);
        close(current);
        if (currentToggle) currentToggle.focus();
    });

    window.addEventListener("scroll", function () {
        closeAll(null);
    }, true);
    window.addEventListener("resize", function () {
        closeAll(null);
    });

    window.CEFDropdowns = {
        closeAll: function () { closeAll(null); }
    };
})();
