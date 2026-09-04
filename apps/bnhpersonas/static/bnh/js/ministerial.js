/* BNH Personal — 20260903.3 */
"use strict";
(() => {
    const VERSION = "20260903.3";
    const jq = () => window.jQuery;
    const hasSelect2 = () => Boolean(jq() && jq().fn && jq().fn.select2);

    function refresh(select) {
        if (select && hasSelect2()) jq()(select).trigger("change.select2");
    }

    function options(select, rows, key, label, selected = "") {
        if (!select) return;
        if (!Array.isArray(rows)) throw new Error(`La respuesta no contiene opciones válidas para ${select.name}.`);
        select.replaceChildren(new Option("Seleccione", ""));
        rows.forEach(row => select.add(new Option(String(row[label]), String(row[key]))));
        select.value = Array.from(select.options).some(o => o.value === String(selected)) ? String(selected) : "";
        refresh(select);
    }

    async function getJson(url, controller) {
        let timedOut = false;
        const timer = window.setTimeout(() => { timedOut = true; controller.abort(); }, 20000);
        try {
            const response = await fetch(url, {
                signal: controller.signal,
                credentials: "same-origin",
                cache: "no-store",
                headers: { "Accept": "application/json" }
            });
            if (response.redirected) throw new Error("La sesión fue redirigida. Ingrese nuevamente y recargue la página.");
            if (!response.ok) throw new Error(`No se pudieron cargar las opciones (HTTP ${response.status}).`);
            if (!response.headers.get("content-type")?.includes("application/json")) {
                throw new Error("La vista de catálogos no devolvió JSON. Revise la sesión y la URL del formulario.");
            }
            return await response.json();
        } catch (error) {
            if (timedOut) throw new Error("La carga de opciones superó 20 segundos. Reintente la selección.");
            throw error;
        } finally {
            window.clearTimeout(timer);
        }
    }

    function start() {
        if (hasSelect2()) {
            document.querySelectorAll("select.select2").forEach(select => {
                try {
                    if (!jq()(select).data("select2")) jq()(select).select2({ width: "100%" });
                } catch (error) {
                    console.warn("No se pudo inicializar Select2 en", select.name, error);
                }
            });
        }
        document.querySelectorAll("form[data-editor]").forEach(form => {
            if (form.dataset.bnhVersion === VERSION) return;
            form.dataset.bnhVersion = VERSION;
            const field = name => form.querySelector(`[name="${name}"], [name="actividad-${name}"], [name="persona-${name}"]`);
            const value = name => field(name)?.value || "";
            const nonTeaching = () => value("categoria") === "NO DOCENTE";
            let requestId = 0, controller, localController;
            let pending = false, localityPending = false;
            const status = document.createElement("div");
            status.className = "alert alert-info mt-3";
            status.setAttribute("role", "status");
            status.setAttribute("aria-live", "polite");
            status.hidden = true;
            form.prepend(status);
            const message = text => { status.textContent = text; status.hidden = !text; };
            const clear = name => options(field(name), [], "", "");
            const disabled = (name, state) => {
                const select = field(name);
                if (select) { select.disabled = state; refresh(select); }
            };
            function enable() {
                disabled("niveles", !value("modalidad") || pending);
                disabled("ceic", !value("niveles") || pending);
                disabled("grado_anio", nonTeaching() || !value("niveles") || pending);
                disabled("secciones", nonTeaching() || !value("grado_anio") || pending);
                disabled("localidad", !value("provincia") || localityPending);
            }
            function category() {
                for (const name of ["grado_anio", "secciones", "espacios"]) {
                    const select = field(name);
                    if (!select) continue;
                    const wrapper = select.closest("[data-field]");
                    if (wrapper) wrapper.hidden = nonTeaching();
                    select.disabled = nonTeaching();
                    if (nonTeaching()) { select.value = ""; refresh(select); }
                }
            }
            async function catalogs(source) {
                controller?.abort();
                controller = new AbortController();
                const currentController = controller;
                const id = ++requestId;
                if (source === "modalidad") ["niveles", "ceic", "grado_anio", "secciones"].forEach(clear);
                if (source === "niveles") ["ceic", "grado_anio", "secciones"].forEach(clear);
                if (source === "grado_anio") clear("secciones");
                if (!value("modalidad")) { pending = false; message(""); enable(); return; }
                const selected = { nivel: value("niveles"), ceic: value("ceic"), grado: value("grado_anio"), seccion: value("secciones") };
                pending = true; enable(); message("Cargando opciones…");
                try {
                    if (!form.dataset.catalogUrl) throw new Error("Falta data-catalog-url en el formulario.");
                    const url = new URL(form.dataset.catalogUrl, window.location.origin);
                    url.searchParams.set("modalidad", value("modalidad"));
                    url.searchParams.set("nivel", selected.nivel);
                    url.searchParams.set("grado", selected.grado);
                    const data = await getJson(url, currentController);
                    if (id !== requestId) return;
                    options(field("niveles"), data.niveles, "c_nivel", "descrip_nivel", selected.nivel);
                    if (value("niveles")) {
                        options(field("ceic"), data.ceic, "c_ceic", "descripcion", selected.ceic);
                        options(field("grado_anio"), data.grado, "c_grado_anio", "nombre_grado_anio", selected.grado);
                        options(field("secciones"), data.secciones, "c_seccion", "nombre_seccion", selected.seccion);
                    } else {
                        ["ceic", "grado_anio", "secciones"].forEach(clear);
                    }
                    category();
                    if (!data.niveles.length) message("La modalidad seleccionada no tiene niveles configurados.");
                    else if (value("niveles") && !nonTeaching() && !data.grado.length) message("Esta modalidad y nivel no tienen grados configurados. Solicite revisar el catálogo.");
                    else message("");
                } catch (error) {
                    if (id === requestId && error.name !== "AbortError") message(error.message);
                } finally {
                    if (id === requestId) { pending = false; enable(); }
                }
            }
            async function localities() {
                localController?.abort();
                const current = new AbortController();
                localController = current;
                clear("localidad");
                localityPending = true; enable();
                try {
                    if (!value("provincia")) return;
                    if (!form.dataset.localitiesUrl) throw new Error("Falta data-localities-url en el formulario.");
                    const url = new URL(form.dataset.localitiesUrl, window.location.origin);
                    url.searchParams.set("provincia", value("provincia"));
                    const rows = await getJson(url, current);
                    if (localController === current) options(field("localidad"), rows, "c_localidad", "descrip_localidad");
                } catch (error) {
                    if (localController === current && error.name !== "AbortError") message(error.message);
                } finally {
                    if (localController === current) { localityPending = false; enable(); }
                }
            }
            // Un cambio nativo puede llegar también por jQuery: se procesa una sola vez.
            let scheduled = false, changedName = "";
            function changed(event) {
                const target = event.target;
                const names = ["modalidad", "niveles", "grado_anio", "categoria", "provincia"];
                const name = names.find(key => field(key) === target);
                if (!name) return;
                changedName = name;
                if (scheduled) return;
                scheduled = true;
                queueMicrotask(() => {
                    scheduled = false;
                    const name = changedName;
                    if (name === "provincia") { localities(); return; }
                    if (name === "categoria") { category(); catalogs("inicio"); return; }
                    catalogs(name);
                });
            }
            form.addEventListener("change", changed);
            if (jq()) jq()(form).off("change.bnhMinisterial").on("change.bnhMinisterial", "select", changed);
            form.addEventListener("submit", event => {
                if (pending || localityPending) { event.preventDefault(); message("Espere a que termine la carga de opciones."); }
            });
            category(); enable();
            if (value("modalidad")) catalogs("inicio");
        });
        document.querySelectorAll("form").forEach(form => {
            if (form.dataset.bnhSubmitBound) return;
            form.dataset.bnhSubmitBound = "1";
            form.addEventListener("submit", event => {
                if (event.defaultPrevented) return;
                if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
                if (form.dataset.submitting) { event.preventDefault(); return; }
                form.dataset.submitting = "1";
                form.querySelectorAll('button[type="submit"],button:not([type])').forEach(button => { button.disabled = true; });
            });
        });
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
    else start();
    window.addEventListener("pageshow", () => {
        document.querySelectorAll("form").forEach(form => {
            delete form.dataset.submitting;
            form.querySelectorAll('button[type="submit"],button:not([type])').forEach(button => { button.disabled = false; });
        });
    });
})();
