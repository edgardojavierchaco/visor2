(function () {
    'use strict';

    var FLAG_KEY = 'padron_flicker_diag_enabled';
    var STORE_KEY = 'padron_flicker_diag_sessions_v1';
    var MAX_SESSIONS = 8;
    var MAX_EVENTS = 900;
    var startedAt = Date.now();
    var observedNodes = [];
    var previousSessions = readStoredSessions();
    var current = {
        id: startedAt + '-' + Math.random().toString(36).slice(2, 8),
        startedAt: new Date(startedAt).toISOString(),
        path: window.location.pathname,
        queryKeys: Array.from(new URLSearchParams(window.location.search).keys()),
        referrerPath: safePath(document.referrer),
        userAgent: navigator.userAgent,
        events: []
    };

    function round(value) {
        return typeof value === 'number' && isFinite(value) ? Math.round(value * 10) / 10 : value;
    }

    function safePath(value) {
        if (!value) return '';
        try {
            var parsed = new URL(value, window.location.href);
            return parsed.origin === window.location.origin
                ? parsed.pathname
                : parsed.hostname + parsed.pathname;
        } catch (error) {
            return String(value).split('?')[0];
        }
    }

    function readStoredSessions() {
        try {
            var value = JSON.parse(sessionStorage.getItem(STORE_KEY) || '[]');
            return Array.isArray(value) ? value : [];
        } catch (error) {
            return [];
        }
    }

    function record(type, data) {
        if (current.events.length >= MAX_EVENTS) return;
        if (type === 'resource' && !data) return;
        current.events.push({
            t: round(performance.now()),
            type: type,
            data: data || null
        });
    }

    function persist() {
        try {
            var sessions = previousSessions.filter(function (session) {
                return session && session.id !== current.id;
            });
            sessions.push(current);
            sessionStorage.setItem(STORE_KEY, JSON.stringify(sessions.slice(-MAX_SESSIONS)));
        } catch (error) {
            record('diagnostic-storage-error', { message: String(error && error.message || error) });
        }
    }

    function nodeLabel(node) {
        if (!node || node.nodeType !== 1) return null;
        var label = node.tagName.toLowerCase();
        if (node.id) label += '#' + node.id;
        if (node.classList && node.classList.length) {
            label += '.' + Array.from(node.classList).slice(0, 4).join('.');
        }
        return label;
    }

    function rectAndStyle(selector) {
        var node = document.querySelector(selector);
        if (!node) return null;
        var rect = node.getBoundingClientRect();
        var style = window.getComputedStyle(node);
        return {
            node: nodeLabel(node),
            x: round(rect.x),
            y: round(rect.y),
            width: round(rect.width),
            height: round(rect.height),
            display: style.display,
            visibility: style.visibility,
            opacity: style.opacity,
            background: style.backgroundColor
        };
    }

    function stylesheetState() {
        return Array.from(document.querySelectorAll('link[rel~="stylesheet"]')).map(function (link) {
            return {
                href: safePath(link.href),
                ready: !!link.sheet,
                disabled: !!link.disabled,
                media: link.media || 'all'
            };
        });
    }

    function snapshot(reason) {
        var content = document.querySelector('.content-wrapper');
        var page = document.querySelector('.padron-page-wrapper');
        return {
            reason: reason,
            readyState: document.readyState,
            visibilityState: document.visibilityState,
            htmlClass: document.documentElement.className || '',
            bodyClass: document.body ? document.body.className : null,
            bareLayout: !!content && !page,
            contentChildren: content ? content.childElementCount : null,
            stylesheets: stylesheetState(),
            header: rectAndStyle('.main-header'),
            sidebar: rectAndStyle('.main-sidebar'),
            content: rectAndStyle('.content-wrapper'),
            page: rectAndStyle('.padron-page-wrapper'),
            moduleNav: rectAndStyle('.padron-module-nav')
        };
    }

    function observePerformance(type, mapper) {
        try {
            if (!window.PerformanceObserver) return;
            if (PerformanceObserver.supportedEntryTypes &&
                PerformanceObserver.supportedEntryTypes.indexOf(type) === -1) return;
            var observer = new PerformanceObserver(function (list) {
                list.getEntries().forEach(function (entry) {
                    record(type, mapper(entry));
                });
            });
            observer.observe({ type: type, buffered: true });
        } catch (error) {
            record('observer-unavailable', { type: type, message: String(error && error.message || error) });
        }
    }

    function resourceData(entry) {
        if (entry.initiatorType !== 'link' && entry.initiatorType !== 'script' &&
            !/cdn\.jsdelivr|cdnjs\.cloudflare|code\.jquery|\/static\//i.test(entry.name)) return null;
        return {
            name: safePath(entry.name),
            initiatorType: entry.initiatorType,
            start: round(entry.startTime),
            duration: round(entry.duration),
            responseStart: round(entry.responseStart),
            responseEnd: round(entry.responseEnd),
            transferSize: entry.transferSize || 0,
            encodedBodySize: entry.encodedBodySize || 0,
            cached: entry.transferSize === 0 && entry.decodedBodySize > 0,
            renderBlockingStatus: entry.renderBlockingStatus || null
        };
    }

    observePerformance('paint', function (entry) {
        return { name: entry.name, start: round(entry.startTime) };
    });
    observePerformance('largest-contentful-paint', function (entry) {
        return {
            start: round(entry.startTime),
            renderTime: round(entry.renderTime),
            loadTime: round(entry.loadTime),
            size: entry.size || 0,
            element: nodeLabel(entry.element)
        };
    });
    observePerformance('layout-shift', function (entry) {
        return {
            start: round(entry.startTime),
            value: round(entry.value),
            hadRecentInput: !!entry.hadRecentInput,
            sources: Array.from(entry.sources || []).map(function (source) {
                return nodeLabel(source.node);
            }).filter(Boolean)
        };
    });
    observePerformance('longtask', function (entry) {
        return { start: round(entry.startTime), duration: round(entry.duration), name: entry.name };
    });
    observePerformance('resource', resourceData);

    function eventRecord(name, event) {
        record(name, {
            persisted: event && typeof event.persisted === 'boolean' ? event.persisted : null,
            snapshot: snapshot(name)
        });
    }

    document.addEventListener('readystatechange', function () {
        eventRecord('readystatechange');
    });
    document.addEventListener('DOMContentLoaded', function (event) {
        attachNodeObservers();
        eventRecord('DOMContentLoaded', event);
    });
    window.addEventListener('load', function (event) {
        eventRecord('load', event);
        window.setTimeout(recordNavigationTiming, 0);
        window.setTimeout(persist, 1000);
    });
    window.addEventListener('pageshow', function (event) {
        eventRecord('pageshow', event);
    });
    window.addEventListener('pagehide', function (event) {
        eventRecord('pagehide', event);
        persist();
    });
    document.addEventListener('visibilitychange', function () {
        eventRecord('visibilitychange');
        if (document.visibilityState === 'hidden') persist();
    });

    document.addEventListener('load', function (event) {
        var target = event.target;
        if (!target || (target.tagName !== 'LINK' && target.tagName !== 'SCRIPT')) return;
        record('asset-load', {
            node: nodeLabel(target),
            url: safePath(target.href || target.src),
            snapshot: snapshot('asset-load')
        });
    }, true);

    window.addEventListener('error', function (event) {
        var target = event.target;
        record(target && (target.src || target.href) ? 'asset-error' : 'window-error', {
            url: safePath(target && (target.src || target.href) || ''),
            message: event.message || '',
            filename: safePath(event.filename || ''),
            line: event.lineno || 0,
            column: event.colno || 0
        });
    }, true);
    window.addEventListener('unhandledrejection', function (event) {
        record('unhandledrejection', { reason: String(event.reason && event.reason.message || event.reason || '') });
    });

    function attachNodeObservers() {
        if (!window.MutationObserver) return;
        ['html', 'body', '.main-header', '.main-sidebar', '.content-wrapper', '.padron-page-wrapper', '.padron-module-nav'].forEach(function (selector) {
            var node = document.querySelector(selector);
            if (!node || observedNodes.indexOf(node) !== -1) return;
            observedNodes.push(node);
            var observer = new MutationObserver(function (mutations) {
                mutations.forEach(function (mutation) {
                    record('attribute-change', {
                        node: nodeLabel(mutation.target),
                        attribute: mutation.attributeName,
                        value: mutation.target.getAttribute(mutation.attributeName),
                        snapshot: snapshot('attribute-change')
                    });
                });
            });
            observer.observe(node, { attributes: true, attributeFilter: ['class', 'style', 'hidden'] });
        });
    }

    function recordNavigationTiming() {
        var navigation = performance.getEntriesByType('navigation')[0];
        if (!navigation) return;
        record('navigation-timing', {
            type: navigation.type,
            ttfb: round(navigation.responseStart),
            responseDownload: round(navigation.responseEnd - navigation.responseStart),
            domInteractive: round(navigation.domInteractive),
            domContentLoaded: round(navigation.domContentLoadedEventEnd),
            loadEvent: round(navigation.loadEventEnd),
            transferSize: navigation.transferSize || 0,
            encodedBodySize: navigation.encodedBodySize || 0
        });
    }

    var lastFrameState = '';
    var frameDeadline = performance.now() + 8000;
    function sampleFrame() {
        attachNodeObservers();
        var state = snapshot('animation-frame');
        var serialized = JSON.stringify(state);
        if (serialized !== lastFrameState) {
            lastFrameState = serialized;
            record('frame-state-change', state);
        }
        if (performance.now() < frameDeadline) requestAnimationFrame(sampleFrame);
    }

    window.padronFlickerReport = function () {
        persist();
        var sessions = readStoredSessions();
        var report = { generatedAt: new Date().toISOString(), sessions: sessions };
        var json = JSON.stringify(report, null, 2);
        console.log('[PADRON-FLICKER-JSON-INICIO]\n' + json + '\n[PADRON-FLICKER-JSON-FIN]');
        return json;
    };

    window.padronFlickerReset = function () {
        previousSessions = [];
        current.events = [];
        sessionStorage.removeItem(STORE_KEY);
        record('diagnostic-reset', snapshot('diagnostic-reset'));
        console.info('[PADRON-FLICKER] Historial reiniciado.');
    };

    window.padronFlickerStop = function () {
        persist();
        sessionStorage.removeItem(FLAG_KEY);
        console.info('[PADRON-FLICKER] Se desactivara al navegar o recargar.');
    };

    record('diagnostic-start', snapshot('diagnostic-start'));
    requestAnimationFrame(sampleFrame);
    window.setTimeout(persist, 5000);
    console.info('[PADRON-FLICKER] Diagnostico activo. Tras el parpadeo ejecute: padronFlickerReport()');
})();
