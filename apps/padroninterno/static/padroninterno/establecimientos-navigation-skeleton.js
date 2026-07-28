(function () {
    'use strict';

    var STORAGE_KEY = 'padron_est_nav_skeleton_v1';
    var DISABLED_TEST_KEY = 'padron_est_nav_skeleton_disabled_for_test';
    var ACTIVE_CLASS = 'padron-est-nav-pending';
    var TARGET_PATH = '/padron/establecimiento/';
    var MAX_STATE_AGE = 30000;
    var SAFETY_TIMEOUT = 15000;
    var navigationStarted = false;
    var removalScheduled = false;

    function markForensic(name, data) {
        if (typeof window.padronFlickerMark !== 'function') {
            return;
        }
        try {
            window.padronFlickerMark(name, data || null);
        } catch (error) {
            // El registrador nunca debe alterar la navegacion real.
        }
    }

    function readState() {
        var raw;
        var state;

        try {
            raw = sessionStorage.getItem(STORAGE_KEY);
            state = raw ? JSON.parse(raw) : null;
        } catch (error) {
            state = null;
        }

        if (!state || state.targetPath !== TARGET_PATH || !state.startedAt || Date.now() - state.startedAt > MAX_STATE_AGE) {
            clearState();
            return null;
        }

        return state;
    }

    function clearState() {
        try {
            sessionStorage.removeItem(STORAGE_KEY);
        } catch (error) {
            // La cortina es opcional: la navegacion debe continuar aunque storage no este disponible.
        }
    }

    function curtainDisabledForTest() {
        var requested = new URLSearchParams(window.location.search).get('padron_curtain');
        try {
            if (requested === '0') {
                sessionStorage.setItem(DISABLED_TEST_KEY, '1');
            } else if (requested === '1') {
                sessionStorage.removeItem(DISABLED_TEST_KEY);
            }
            return sessionStorage.getItem(DISABLED_TEST_KEY) === '1';
        } catch (error) {
            return requested === '0';
        }
    }

    function nativeCrossDocumentTransitionAvailable() {
        return 'onpageswap' in window;
    }

    function hideCurtain() {
        var wasActive = document.documentElement.classList.contains(ACTIVE_CLASS);
        if (wasActive) {
            markForensic('curtain-before-hide');
        }
        document.documentElement.classList.remove(ACTIVE_CLASS);
        clearState();
        if (wasActive) {
            markForensic('curtain-hidden');
        }
    }

    function isInicio() {
        return window.location.pathname === '/padron/' || window.location.pathname === '/padron';
    }

    function isEstablecimientos() {
        return window.location.pathname === TARGET_PATH || window.location.pathname === '/padron/establecimiento';
    }

    function closestAnchor(node) {
        while (node && node.nodeType === 1) {
            if (node.tagName === 'A') {
                return node;
            }
            node = node.parentElement;
        }
        return null;
    }

    function isEligibleClick(event, anchor) {
        var url;
        var target;

        if (!anchor || event.defaultPrevented || (typeof event.button === 'number' && event.button !== 0) || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return false;
        }

        if (anchor.hasAttribute('download') || anchor.getAttribute('data-bs-toggle') === 'dropdown') {
            return false;
        }

        target = anchor.getAttribute('target');
        if (target && target.toLowerCase() !== '_self') {
            return false;
        }

        try {
            url = new URL(anchor.href, window.location.href);
        } catch (error) {
            return false;
        }

        return url.origin === window.location.origin && url.pathname === TARGET_PATH;
    }

    function showOutgoingCurtain(anchor, event) {
        var state;
        var destination = anchor.href;
        var fallbackTimer;
        var navigateOnce = function (reason) {
            if (!destination) {
                return;
            }
            window.clearTimeout(fallbackTimer);
            var next = destination;
            destination = '';
            markForensic('outgoing-navigation-commit', { reason: reason || 'unknown', href: next });
            window.location.assign(next);
        };

        if (navigationStarted) {
            event.preventDefault();
            return;
        }

        navigationStarted = true;
        event.preventDefault();
        state = { targetPath: TARGET_PATH, startedAt: Date.now() };

        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (error) {
            // La clase local sigue evitando el vacio aunque storage no este disponible.
        }

        document.documentElement.classList.add(ACTIVE_CLASS);
        markForensic('outgoing-curtain-class-added', { href: destination });

        fallbackTimer = window.setTimeout(function () {
            navigateOnce('timeout-fallback');
        }, 120);
        window.requestAnimationFrame(function () {
            markForensic('outgoing-curtain-first-frame');
            window.requestAnimationFrame(function () {
                markForensic('outgoing-curtain-painted');
                navigateOnce('double-animation-frame');
            });
        });
    }

    function destinationIsReady() {
        var root = document.querySelector('.establecimientos-wrapper[data-padron-initial-loading]');

        return !!root &&
            root.getAttribute('data-padron-initial-loading') !== 'true' &&
            !root.classList.contains('padron-is-initial-loading');
    }

    function removeWhenReady() {
        var observer;
        var safetyTimer;

        if (removalScheduled || !document.documentElement.classList.contains(ACTIVE_CLASS)) {
            return;
        }
        removalScheduled = true;

        function finishIfReady() {
            if (!destinationIsReady()) {
                return false;
            }

            if (observer) {
                observer.disconnect();
            }
            window.clearTimeout(safetyTimer);
            markForensic('destination-ready-signal');
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(hideCurtain);
            });
            return true;
        }

        if (finishIfReady()) {
            return;
        }

        observer = new MutationObserver(finishIfReady);
        observer.observe(document.documentElement, {
            subtree: true,
            attributes: true,
            attributeFilter: ['data-padron-initial-loading', 'class'],
            childList: true
        });

        safetyTimer = window.setTimeout(function () {
            observer.disconnect();
            markForensic('destination-safety-timeout');
            hideCurtain();
        }, SAFETY_TIMEOUT);
    }

    if (nativeCrossDocumentTransitionAvailable() || curtainDisabledForTest()) {
        document.documentElement.classList.remove(ACTIVE_CLASS);
        clearState();
        markForensic(nativeCrossDocumentTransitionAvailable() ? 'curtain-disabled-for-native-transition' : 'curtain-disabled-for-root-cause-test');
        return;
    }

    if (isInicio()) {
        hideCurtain();
        document.addEventListener('click', function (event) {
            var anchor = closestAnchor(event.target);
            if (isEligibleClick(event, anchor)) {
                showOutgoingCurtain(anchor, event);
            }
        }, true);

        window.addEventListener('pageshow', function (event) {
            if (event.persisted) {
                navigationStarted = false;
                hideCurtain();
            }
        });
        return;
    }

    if (isEstablecimientos() && readState()) {
        document.documentElement.classList.add(ACTIVE_CLASS);
        markForensic('incoming-curtain-class-restored');
        removeWhenReady();
    } else {
        hideCurtain();
    }
})();
