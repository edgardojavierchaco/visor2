(function () {
    'use strict';

    var FLAG_KEY = 'padron_flicker_diag_enabled';
    var STORE_KEY = 'padron_flicker_forensic_sessions_v3';
    var TARGET_KEY = 'padron_flicker_forensic_target_path';
    var TARGET_PATHS = ['/padron/establecimiento/', '/padron/localizacion/'];
    var TARGET_PATH = readTargetPath();
    var MAX_SESSIONS = 4;
    var MAX_EVENTS = 1400;
    var current;
    var frameDeadline = 0;
    var frameSampling = false;
    var lastFrameSampleAt = 0;
    var lastFrameState = '';
    var seenCritical = {};
    var releaseAbs = null;
    var autoReportTimer = null;

    if (!isEnabled()) {
        return;
    }

    current = {
        id: Date.now() + '-' + Math.random().toString(36).slice(2, 8),
        path: window.location.pathname,
        targetPath: TARGET_PATH,
        query: window.location.search,
        referrerPath: safePath(document.referrer),
        timeOrigin: round(performance.timeOrigin || (Date.now() - performance.now())),
        startedAbs: absNow(),
        userAgent: navigator.userAgent,
        events: []
    };

    function isEnabled() {
        try {
            return sessionStorage.getItem(FLAG_KEY) === '1';
        } catch (error) {
            return false;
        }
    }

    function readTargetPath() {
        try {
            var stored = sessionStorage.getItem(TARGET_KEY);
            return TARGET_PATHS.indexOf(stored) !== -1 ? stored : '/padron/establecimiento/';
        } catch (error) {
            return '/padron/establecimiento/';
        }
    }

    function rememberTargetPath(path) {
        TARGET_PATH = path;
        current.targetPath = path;
        try { sessionStorage.setItem(TARGET_KEY, path); } catch (error) {}
    }

    function round(value) {
        return typeof value === 'number' && isFinite(value) ? Math.round(value * 10) / 10 : value;
    }

    function roundFine(value) {
        return typeof value === 'number' && isFinite(value) ? Math.round(value * 100000) / 100000 : value;
    }

    function absNow() {
        return round((performance.timeOrigin || (Date.now() - performance.now())) + performance.now());
    }

    function safePath(value) {
        if (!value) return '';
        try {
            var parsed = new URL(value, window.location.href);
            return parsed.origin === window.location.origin ? parsed.pathname : parsed.hostname + parsed.pathname;
        } catch (error) {
            return String(value).split('?')[0];
        }
    }

    function readSessions() {
        try {
            var parsed = JSON.parse(sessionStorage.getItem(STORE_KEY) || '[]');
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            return [];
        }
    }

    function allSessions() {
        var sessions = readSessions().filter(function (session) {
            return session && session.id !== current.id;
        });
        sessions.push(current);
        return sessions.slice(-MAX_SESSIONS);
    }

    function persist() {
        try {
            sessionStorage.setItem(STORE_KEY, JSON.stringify(allSessions()));
        } catch (error) {
            // El diagnostico no debe alterar la navegacion si storage esta lleno o bloqueado.
        }
    }

    function record(type, data, persistNow) {
        if (current.events.length >= MAX_EVENTS) return;
        current.events.push({
            t: round(performance.now()),
            abs: absNow(),
            type: type,
            data: data || null
        });
        if (persistNow) persist();
    }

    function nodeLabel(node) {
        if (!node || node.nodeType !== 1) return null;
        var label = node.tagName.toLowerCase();
        if (node.id) label += '#' + node.id;
        if (node.classList && node.classList.length) {
            label += '.' + Array.prototype.slice.call(node.classList, 0, 4).join('.');
        }
        return label;
    }

    function rectStyle(selector) {
        var node = document.querySelector(selector);
        var rect;
        var style;
        if (!node) return null;
        rect = node.getBoundingClientRect();
        style = window.getComputedStyle(node);
        return {
            node: nodeLabel(node),
            x: round(rect.x),
            y: round(rect.y),
            w: round(rect.width),
            h: round(rect.height),
            display: style.display,
            visibility: style.visibility,
            opacity: style.opacity,
            background: style.backgroundColor,
            borderColor: style.borderColor,
            borderRadius: style.borderRadius,
            marginLeft: style.marginLeft,
            transform: style.transform
        };
    }

    function isPainted(rect) {
        return !!rect && rect.display !== 'none' && rect.visibility !== 'hidden' &&
            Number(rect.opacity) !== 0 && rect.w > 0 && rect.h > 0;
    }

    function pointStack() {
        var x = Math.max(1, Math.round(window.innerWidth * 0.5));
        var y = Math.max(1, Math.round(window.innerHeight * 0.35));
        var nodes;
        if (document.elementsFromPoint) {
            nodes = document.elementsFromPoint(x, y);
        } else {
            nodes = [document.elementFromPoint(x, y)];
        }
        return (nodes || []).slice(0, 7).map(nodeLabel).filter(Boolean);
    }

    function stylesheetState() {
        return Array.prototype.map.call(document.querySelectorAll('link[rel~="stylesheet"]'), function (link) {
            return {
                href: safePath(link.href),
                ready: !!link.sheet,
                disabled: !!link.disabled
            };
        });
    }

    function snapshot(reason) {
        var curtain = rectStyle('.padron-est-nav-curtain');
        var page = rectStyle('.padron-page-wrapper');
        var content = rectStyle('.content-wrapper');
        var curtainPainted = isPainted(curtain);
        var pagePainted = isPainted(page);
        var visualState = curtainPainted ? 'CURTAIN' : (pagePainted ? 'REAL_PAGE' : (content ? 'BARE_LAYOUT' : 'NO_CONTENT'));
        var loadingRoot = document.querySelector('.padron-page-wrapper[data-padron-initial-loading]');

        return {
            reason: reason,
            readyState: document.readyState,
            visibilityState: document.visibilityState,
            visualState: visualState,
            htmlClass: document.documentElement.className || '',
            bodyClass: document.body ? document.body.className : null,
            initialLoading: loadingRoot ? loadingRoot.getAttribute('data-padron-initial-loading') : null,
            viewport: { w: window.innerWidth, h: window.innerHeight },
            stack: pointStack(),
            curtain: curtain,
            page: page,
            content: content,
            realNav: rectStyle('.padron-page-wrapper .padron-module-nav'),
            realHeading: rectStyle('.padron-page-wrapper .page-heading'),
            realFilter: rectStyle('.padron-page-wrapper .filter-card'),
            realResults: rectStyle('.padron-page-wrapper .results-bar'),
            realTable: rectStyle('.padron-page-wrapper .table-shell')
        };
    }

    function geometryComparison() {
        var pairs = [
            ['nav', '.padron-est-nav-curtain__modulebar', '.padron-page-wrapper .padron-module-nav'],
            ['heading', '.padron-est-nav-curtain__heading-row h2', '.padron-page-wrapper .page-heading h2'],
            ['filter', '.padron-est-nav-curtain__filter-card', '.padron-page-wrapper .filter-card'],
            ['results', '.padron-est-nav-curtain__results', '.padron-page-wrapper .results-bar'],
            ['table', '.padron-est-nav-curtain__table', '.padron-page-wrapper .table-shell']
        ];
        var maxDelta = 0;
        var results = pairs.map(function (pair) {
            var curtain = rectStyle(pair[1]);
            var real = rectStyle(pair[2]);
            var delta = null;
            if (curtain && real) {
                delta = {
                    x: round(Math.abs(curtain.x - real.x)),
                    y: round(Math.abs(curtain.y - real.y)),
                    w: round(Math.abs(curtain.w - real.w)),
                    h: round(Math.abs(curtain.h - real.h)),
                    backgroundEqual: curtain.background === real.background,
                    borderRadiusEqual: curtain.borderRadius === real.borderRadius
                };
                maxDelta = Math.max(maxDelta, delta.x, delta.y, delta.w, delta.h);
            }
            return { part: pair[0], curtain: curtain, real: real, delta: delta };
        });
        return { maxDelta: round(maxDelta), pairs: results };
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
            record('observer-unavailable', { observer: type, message: String(error && error.message || error) });
        }
    }

    observePerformance('paint', function (entry) {
        return {
            name: entry.name,
            start: round(entry.startTime),
            absStart: round(current.timeOrigin + entry.startTime)
        };
    });
    observePerformance('layout-shift', function (entry) {
        return {
            start: round(entry.startTime),
            absStart: round(current.timeOrigin + entry.startTime),
            value: roundFine(entry.value),
            hadRecentInput: !!entry.hadRecentInput,
            sources: Array.prototype.map.call(entry.sources || [], function (source) {
                return nodeLabel(source.node);
            }).filter(Boolean)
        };
    });
    observePerformance('longtask', function (entry) {
        return {
            start: round(entry.startTime),
            absStart: round(current.timeOrigin + entry.startTime),
            duration: round(entry.duration),
            name: entry.name
        };
    });
    observePerformance('largest-contentful-paint', function (entry) {
        return {
            start: round(entry.startTime),
            absStart: round(current.timeOrigin + entry.startTime),
            size: entry.size || 0,
            element: nodeLabel(entry.element)
        };
    });

    function checkCriticalNodes(source) {
        [
            ['curtain', '.padron-est-nav-curtain'],
            ['page-wrapper', '.padron-page-wrapper'],
            ['real-nav', '.padron-page-wrapper .padron-module-nav'],
            ['real-table', '.padron-page-wrapper .table-shell']
        ].forEach(function (item) {
            if (seenCritical[item[0]] || !document.querySelector(item[1])) return;
            seenCritical[item[0]] = true;
            record('critical-node-present', {
                kind: item[0],
                source: source,
                snapshot: snapshot('critical-node-present:' + item[0])
            }, true);
        });
    }

    function isCriticalTarget(node) {
        if (!node || node.nodeType !== 1) return false;
        return node === document.documentElement ||
            node === document.body ||
            node.matches('.content-wrapper, .padron-page-wrapper, .padron-est-nav-curtain, .table-shell, .table-responsive, .results-bar, .page-heading');
    }

    if (window.MutationObserver) {
        var mutationObserver = new MutationObserver(function (mutations) {
            checkCriticalNodes('mutation');
            mutations.forEach(function (mutation) {
                if (mutation.type !== 'attributes' || !isCriticalTarget(mutation.target)) return;
                var data = {
                    node: nodeLabel(mutation.target),
                    attribute: mutation.attributeName,
                    value: mutation.target.getAttribute(mutation.attributeName),
                    snapshot: snapshot('critical-attribute')
                };
                record('critical-attribute', data, true);
                if (mutation.target === document.documentElement && mutation.attributeName === 'class' &&
                    document.documentElement.classList.contains('padron-est-nav-pending') === false &&
                    releaseAbs === null) {
                    releaseAbs = absNow();
                    record('curtain-release-detected', {
                        snapshot: snapshot('curtain-release-detected'),
                        comparison: geometryComparison()
                    }, true);
                    startFrameSampling('curtain-release', 3500);
                    scheduleAutoReport(2600);
                }
            });
        });
        mutationObserver.observe(document.documentElement, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeOldValue: true,
            attributeFilter: ['class', 'style', 'hidden', 'data-padron-initial-loading']
        });
    }

    function frameSample() {
        var now = performance.now();
        var state;
        var serialized;
        if (now - lastFrameSampleAt >= 45) {
            lastFrameSampleAt = now;
            checkCriticalNodes('frame');
            state = snapshot('frame');
            serialized = JSON.stringify(state);
            if (serialized !== lastFrameState) {
                lastFrameState = serialized;
                record('frame-state-change', state);
            }
        }
        if (now < frameDeadline) {
            window.requestAnimationFrame(frameSample);
        } else {
            frameSampling = false;
            persist();
        }
    }

    function startFrameSampling(reason, duration) {
        frameDeadline = Math.max(frameDeadline, performance.now() + (duration || 10000));
        record('frame-sampling-start', { reason: reason, until: round(frameDeadline) });
        if (!frameSampling) {
            frameSampling = true;
            window.requestAnimationFrame(frameSample);
        }
    }

    function marker(name, data) {
        var payload = {
            name: name,
            detail: data || null,
            snapshot: snapshot('marker:' + name)
        };
        if (name === 'destination-ready-signal' || name === 'curtain-before-hide') {
            payload.comparison = geometryComparison();
        }
        record('marker', payload, true);
        startFrameSampling('marker:' + name, name.indexOf('curtain') !== -1 ? 4500 : 10000);
        if (name === 'curtain-hidden') {
            releaseAbs = releaseAbs || absNow();
            scheduleAutoReport(2600);
        }
    }

    window.padronFlickerMark = marker;

    document.addEventListener('click', function (event) {
        var anchor = event.target && event.target.closest ? event.target.closest('a[href]') : null;
        var url;
        if (!anchor) return;
        try {
            url = new URL(anchor.href, window.location.href);
        } catch (error) {
            return;
        }
        if (url.origin === window.location.origin && TARGET_PATHS.indexOf(url.pathname) !== -1) {
            rememberTargetPath(url.pathname);
            marker('target-link-click-capture', { href: url.pathname + url.search });
        }
    }, true);

    function lifecycle(name, event) {
        record(name, {
            persisted: event && typeof event.persisted === 'boolean' ? event.persisted : null,
            snapshot: snapshot(name)
        }, name === 'pagehide' || name === 'visibilitychange');
    }

    document.addEventListener('readystatechange', function (event) { lifecycle('readystatechange', event); });
    document.addEventListener('DOMContentLoaded', function (event) {
        checkCriticalNodes('DOMContentLoaded');
        lifecycle('DOMContentLoaded', event);
    });
    window.addEventListener('pageshow', function (event) { lifecycle('pageshow', event); });
    window.addEventListener('load', function (event) {
        lifecycle('load', event);
        recordNavigationTiming();
        if (window.location.pathname === TARGET_PATH) scheduleAutoReport(9000);
    });
    window.addEventListener('pagehide', function (event) { lifecycle('pagehide', event); });
    document.addEventListener('visibilitychange', function (event) { lifecycle('visibilitychange', event); });

    window.addEventListener('error', function (event) {
        var target = event.target;
        record(target && (target.src || target.href) ? 'asset-error' : 'window-error', {
            url: safePath(target && (target.src || target.href) || event.filename || ''),
            message: event.message || '',
            line: event.lineno || 0,
            column: event.colno || 0
        }, true);
    }, true);
    window.addEventListener('unhandledrejection', function (event) {
        record('unhandledrejection', {
            reason: String(event.reason && event.reason.message || event.reason || '')
        }, true);
    });

    function recordNavigationTiming() {
        var navigation = performance.getEntriesByType('navigation')[0];
        if (!navigation) return;
        record('navigation-timing', {
            type: navigation.type,
            requestStartAbs: round(current.timeOrigin + navigation.requestStart),
            responseStartAbs: round(current.timeOrigin + navigation.responseStart),
            responseEndAbs: round(current.timeOrigin + navigation.responseEnd),
            ttfb: round(navigation.responseStart - navigation.requestStart),
            responseDownload: round(navigation.responseEnd - navigation.responseStart),
            domInteractive: round(navigation.domInteractive),
            domContentLoaded: round(navigation.domContentLoadedEventEnd),
            loadEvent: round(navigation.loadEventEnd),
            transferSize: navigation.transferSize || 0
        }, true);
    }

    function firstEvent(session, type, predicate) {
        var events = session ? session.events || [] : [];
        for (var i = 0; i < events.length; i += 1) {
            if (events[i].type === type && (!predicate || predicate(events[i]))) return events[i];
        }
        return null;
    }

    function lastEvent(session, type, predicate) {
        var events = session ? session.events || [] : [];
        for (var i = events.length - 1; i >= 0; i -= 1) {
            if (events[i].type === type && (!predicate || predicate(events[i]))) return events[i];
        }
        return null;
    }

    function analyze(sessions) {
        var incoming = null;
        var outgoing = null;
        var i;
        for (i = sessions.length - 1; i >= 0; i -= 1) {
            if (!incoming && sessions[i].path === TARGET_PATH) {
                incoming = sessions[i];
            } else if (incoming && !outgoing && (sessions[i].path === '/padron/' || sessions[i].path === '/padron')) {
                outgoing = sessions[i];
                break;
            }
        }

        var firstPaint = firstEvent(incoming, 'paint', function (event) {
            return event.data && event.data.name === 'first-paint';
        });
        var curtainPresent = firstEvent(incoming, 'critical-node-present', function (event) {
            return event.data && event.data.kind === 'curtain';
        });
        var pagePresent = firstEvent(incoming, 'critical-node-present', function (event) {
            return event.data && event.data.kind === 'page-wrapper';
        });
        var outgoingPainted = lastEvent(outgoing, 'marker', function (event) {
            return event.data && event.data.name === 'outgoing-curtain-painted';
        });
        var release = firstEvent(incoming, 'marker', function (event) {
            return event.data && (event.data.name === 'curtain-hidden' || event.data.name === 'curtain-before-hide');
        }) || firstEvent(incoming, 'curtain-release-detected');
        var comparisonEvent = firstEvent(incoming, 'marker', function (event) {
            return event.data && event.data.comparison;
        }) || firstEvent(incoming, 'curtain-release-detected');
        var errors = (incoming ? incoming.events : []).filter(function (event) {
            return event.type === 'window-error' || event.type === 'asset-error' || event.type === 'unhandledrejection';
        });
        var bareFrames = (incoming ? incoming.events : []).filter(function (event) {
            return event.type === 'frame-state-change' && event.data && event.data.visualState === 'BARE_LAYOUT';
        });
        var releaseTime = release ? release.abs : null;
        var firstPaintAbs = firstPaint && firstPaint.data ? firstPaint.data.absStart : null;
        var visibleBareFrames = bareFrames.filter(function (event) {
            return firstPaintAbs && event.abs >= firstPaintAbs;
        });
        var pageAbs = pagePresent ? pagePresent.abs : null;
        var stabilityStart = releaseTime || firstPaintAbs;
        var stabilityWindow = releaseTime ? 1500 : 6000;
        var postReleaseShifts = (incoming ? incoming.events : []).filter(function (event) {
            return event.type === 'layout-shift' && stabilityStart && event.data &&
                event.data.absStart >= stabilityStart && event.data.absStart <= stabilityStart + stabilityWindow &&
                !event.data.hadRecentInput;
        });
        var shiftTotal = postReleaseShifts.reduce(function (sum, event) {
            return sum + Number(event.data.value || 0);
        }, 0);
        var comparison = comparisonEvent && comparisonEvent.data ? comparisonEvent.data.comparison : null;
        var curtainAbs = curtainPresent ? curtainPresent.abs : null;
        var verdict;
        var confidence;

        if (firstPaintAbs && curtainAbs && firstPaintAbs + 1 < curtainAbs) {
            verdict = 'FIRST_PAINT_BEFORE_INCOMING_CURTAIN';
            confidence = 'high';
        } else if (!curtainPresent && firstPaintAbs && pageAbs && firstPaintAbs + 1 < pageAbs) {
            verdict = 'FIRST_PAINT_BEFORE_REAL_PAGE_WRAPPER';
            confidence = 'high';
        } else if (visibleBareFrames.length) {
            verdict = 'BARE_LAYOUT_FRAME_CONFIRMED';
            confidence = 'high';
        } else if (errors.length) {
            verdict = 'JAVASCRIPT_OR_ASSET_ERROR_DURING_TRANSITION';
            confidence = 'high';
        } else if (comparison && comparison.maxDelta > 6) {
            verdict = 'CURTAIN_AND_REAL_PAGE_GEOMETRY_MISMATCH';
            confidence = 'high';
        } else if (shiftTotal >= 0.002) {
            verdict = curtainPresent ? 'REAL_PAGE_LAYOUT_SHIFT_AFTER_CURTAIN_RELEASE' : 'REAL_PAGE_LAYOUT_SHIFT_AFTER_FIRST_PAINT';
            confidence = 'high';
        } else if (!firstPaint || !pagePresent || (curtainPresent && !release)) {
            verdict = 'INSUFFICIENT_CRITICAL_EVENTS';
            confidence = 'low';
        } else {
            verdict = 'NO_DOM_CAUSE_CAPTURED_REQUIRES_BROWSER_FILMSTRIP';
            confidence = 'medium';
        }

        return {
            verdict: verdict,
            confidence: confidence,
            evidence: {
                outgoingCurtainPaintedAbs: outgoingPainted ? outgoingPainted.abs : null,
                incomingFirstPaintAbs: firstPaintAbs,
                incomingCurtainPresentAbs: curtainAbs,
                incomingPageWrapperPresentAbs: pageAbs,
                curtainReleaseAbs: releaseTime,
                bareLayoutFrames: visibleBareFrames.length,
                prePaintBareFrames: bareFrames.length - visibleBareFrames.length,
                postReleaseLayoutShiftTotal: roundFine(shiftTotal),
                postReleaseLayoutShifts: postReleaseShifts.length,
                geometryMaxDeltaPx: comparison ? comparison.maxDelta : null,
                errors: errors.map(function (event) { return event.data; })
            },
            geometry: comparison,
            meaning: {
                FIRST_PAINT_BEFORE_INCOMING_CURTAIN: 'El nuevo documento se pinto antes de que existiera su cortina.',
                FIRST_PAINT_BEFORE_REAL_PAGE_WRAPPER: 'El navegador pinto el layout base antes de que existiera el contenido real del modulo.',
                BARE_LAYOUT_FRAME_CONFIRMED: 'Se registro al menos un cuadro con layout pero sin cortina ni pagina real.',
                JAVASCRIPT_OR_ASSET_ERROR_DURING_TRANSITION: 'Un error de script o recurso interrumpio el armado visual.',
                CURTAIN_AND_REAL_PAGE_GEOMETRY_MISMATCH: 'El salto visible ocurre al cambiar entre dos geometrías distintas.',
                REAL_PAGE_LAYOUT_SHIFT_AFTER_CURTAIN_RELEASE: 'La pagina real cambia de layout despues de retirar la cortina.',
                REAL_PAGE_LAYOUT_SHIFT_AFTER_FIRST_PAINT: 'La pagina real cambia de layout despues del primer pintado visible.',
                INSUFFICIENT_CRITICAL_EVENTS: 'La navegacion no produjo todos los marcadores necesarios.',
                NO_DOM_CAUSE_CAPTURED_REQUIRES_BROWSER_FILMSTRIP: 'El DOM fue estable; el siguiente nivel es una traza del compositor con capturas.'
            }[verdict]
        };
    }

    function buildReport() {
        persist();
        var sessions = readSessions();
        return {
            generatedAt: new Date().toISOString(),
            diagnosis: analyze(sessions),
            sessions: sessions
        };
    }

    function printReport() {
        var report = buildReport();
        var diagnosis = JSON.stringify(report.diagnosis, null, 2);
        var full = JSON.stringify(report, null, 2);
        console.log('[PADRON-FORENSIC-DIAGNOSIS]\n' + diagnosis);
        console.log('[PADRON-FORENSIC-FULL-REPORT-BEGIN]\n' + full + '\n[PADRON-FORENSIC-FULL-REPORT-END]');
        return full;
    }

    function scheduleAutoReport(delay) {
        window.clearTimeout(autoReportTimer);
        autoReportTimer = window.setTimeout(printReport, delay);
    }

    window.padronFlickerReport = printReport;
    window.padronFlickerReset = function () {
        try { sessionStorage.removeItem(STORE_KEY); } catch (error) {}
        current.events = [];
        record('diagnostic-reset', { snapshot: snapshot('diagnostic-reset') }, true);
        console.info('[PADRON-FORENSIC] Historial reiniciado.');
    };
    window.padronFlickerStop = function () {
        persist();
        try { sessionStorage.removeItem(FLAG_KEY); } catch (error) {}
        console.info('[PADRON-FORENSIC] Se desactivara al navegar o recargar.');
    };

    record('diagnostic-start', {
        stylesheets: stylesheetState(),
        snapshot: snapshot('diagnostic-start')
    }, true);
    checkCriticalNodes('diagnostic-start');
    startFrameSampling('diagnostic-start', 12000);
    console.info('[PADRON-FORENSIC] Prueba forense activa. El informe se imprimira automaticamente.');
})();
