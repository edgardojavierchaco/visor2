/* BNH Personal — 20260908.1 */
"use strict";
(() => {
    const VERSION = "20260908.1";
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

            // ============================================================
            // CUIL -> VALIDACIÓN + AUTOCOMPLETADO DE DNI
            // ============================================================
            // El DNI se toma de los 8 dígitos centrales del CUIL.
            // Si el DNI real tiene 7 dígitos, se conserva el 0 inicial.
            // Ej.: CUIL 20-01234567-X -> DNI 01234567

            const normalizarCuil = raw => String(raw || "").replace(/\D/g, "");

            function validarCuil(raw) {
                const cuil = normalizarCuil(raw);

                if (!cuil) {
                    return { valido: false, vacio: true, mensaje: "" };
                }

                if (cuil.length !== 11) {
                    return {
                        valido: false,
                        mensaje: "El CUIL debe tener 11 dígitos."
                    };
                }

                const coef = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
                let total = 0;

                for (let i = 0; i < 10; i += 1) {
                    total += Number(cuil[i]) * coef[i];
                }

                const resto = total % 11;
                let dv = 11 - resto;

                if (dv === 11) {
                    dv = 0;
                } else if (dv === 10) {
                    return {
                        valido: false,
                        mensaje: "CUIL inválido: dígito verificador no representable."
                    };
                }

                if (dv !== Number(cuil[10])) {
                    return {
                        valido: false,
                        mensaje: "CUIL inválido: el dígito verificador no coincide."
                    };
                }

                return {
                    valido: true,
                    cuil,
                    // Ocho posiciones centrales. No se convierte a Number
                    // para conservar un posible cero inicial.
                    dni: cuil.substring(2, 10),
                    mensaje: ""
                };
            }

            function setCuilFeedback(input, text, error = false) {
                if (!input) return;

                let feedback = input.parentElement?.querySelector("[data-cuil-feedback]");

                if (!feedback) {
                    feedback = document.createElement("div");
                    feedback.dataset.cuilFeedback = "1";
                    feedback.className = "form-text";
                    input.insertAdjacentElement("afterend", feedback);
                }

                feedback.textContent = text || "";
                feedback.className = error ? "form-text text-danger" : "form-text text-success";
                feedback.hidden = !text;
            }

            function validarYCompletarDni({ mostrarMensaje = true } = {}) {
                const inputCuil = field("cuil");
                const inputDni = field("dni");

                if (!inputCuil || !inputDni) return true;

                const resultado = validarCuil(inputCuil.value);

                inputCuil.classList.remove("is-valid", "is-invalid");

                if (resultado.vacio) {
                    setCuilFeedback(inputCuil, "");
                    return false;
                }

                if (!resultado.valido) {
                    inputCuil.classList.add("is-invalid");
                    setCuilFeedback(inputCuil, resultado.mensaje, true);
                    return false;
                }

                inputCuil.value = resultado.cuil;
                inputCuil.classList.add("is-valid");

                // Siempre dejamos ocho caracteres. Si el DNI tiene siete
                // dígitos, queda con cero delante porque el CUIL contiene
                // ese cero dentro de sus ocho posiciones centrales.
                inputDni.value = resultado.dni;

                inputDni.dispatchEvent(new Event("input", { bubbles: true }));
                inputDni.dispatchEvent(new Event("change", { bubbles: true }));

                if (mostrarMensaje) {
                    setCuilFeedback(
                        inputCuil,
                        `CUIL válido. DNI ${resultado.dni} completado automáticamente.`
                    );
                } else {
                    setCuilFeedback(inputCuil, "");
                }

                return true;
            }

            const inputCuil = field("cuil");

            if (inputCuil) {
                inputCuil.addEventListener("input", () => {
                    inputCuil.classList.remove("is-valid", "is-invalid");
                    setCuilFeedback(inputCuil, "");

                    const cuil = normalizarCuil(inputCuil.value);

                    // Apenas llega a 11 dígitos, validamos y completamos DNI.
                    if (cuil.length === 11) {
                        validarYCompletarDni();
                    }
                });

                inputCuil.addEventListener("blur", () => {
                    if (normalizarCuil(inputCuil.value)) {
                        validarYCompletarDni();
                    }
                });

                // Al editar una persona existente no mostramos mensaje,
                // pero normalizamos el CUIL y sincronizamos el DNI si es válido.
                if (normalizarCuil(inputCuil.value).length === 11) {
                    validarYCompletarDni({ mostrarMensaje: false });
                }
            }
            const normalizedCategory = () => String(
                value("categoria") || ""
            ).trim().toUpperCase();

            const nonTeaching = () => normalizedCategory() === "NO DOCENTE";
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

                disabled(
                    "niveles",
                    !value("modalidad") || pending
                );

                /*
                * DOCENTE:
                * el CEIC depende del nivel.
                *
                * NO DOCENTE:
                * el CEIC pertenece al rango especial
                * c_niv 1023-1025 y no depende del
                * grado/año.
                */
                disabled(
                    "ceic",
                    (
                        !nonTeaching()
                        && !value("niveles")
                    )
                    || pending
                );

                disabled(
                    "grado_anio",
                    nonTeaching()
                    || !value("niveles")
                    || pending
                );

                disabled(
                    "secciones",
                    nonTeaching()
                    || !value("grado_anio")
                    || pending
                );

                disabled(
                    "localidad",
                    !value("provincia")
                    || localityPending
                );
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
                if (source === "categoria") ["ceic", "grado_anio", "secciones"].forEach(clear);
                if (source === "modalidad") ["niveles", "ceic", "grado_anio", "secciones"].forEach(clear);
                if (source === "niveles") ["ceic", "grado_anio", "secciones"].forEach(clear);
                if (source === "grado_anio") clear("secciones");
                if (
                    !value("modalidad")
                    && !nonTeaching()
                ) {
                    pending = false;
                    message("");
                    enable();
                    return;
                }
                const selected = {
                    nivel: value("niveles"),
                    ceic: source === "categoria" ? "" : value("ceic"),
                    grado: value("grado_anio"),
                    seccion: value("secciones")
                };
                pending = true; enable(); message("Cargando opciones…");
                try {
                    if (!form.dataset.catalogUrl) throw new Error("Falta data-catalog-url en el formulario.");
                    const url = new URL(form.dataset.catalogUrl, window.location.origin);
                    url.searchParams.set(
                        "categoria",
                        normalizedCategory()
                    );

                    url.searchParams.set(
                        "modalidad",
                        value("modalidad")
                    );

                    url.searchParams.set(
                        "nivel",
                        selected.nivel
                    );

                    url.searchParams.set(
                        "grado",
                        selected.grado
                    );
                    const data = await getJson(url, currentController);
                    if (id !== requestId) return;
                    if (value("modalidad")) {
                        options(
                            field("niveles"),
                            data.niveles,
                            "c_nivel",
                            "descrip_nivel",
                            selected.nivel
                        );
                    }

                    if (nonTeaching()) {

                        /*
                        * PERSONAL NO DOCENTE
                        *
                        * Sólo CEIC c_niv 1023-1025.
                        * Grado y sección no corresponden.
                        */

                        options(
                            field("ceic"),
                            data.ceic,
                            "c_ceic",
                            "descripcion",
                            selected.ceic
                        );

                        clear("grado_anio");
                        clear("secciones");

                    } else if (value("niveles")) {

                        /*
                        * PERSONAL DOCENTE
                        */

                        options(
                            field("ceic"),
                            data.ceic,
                            "c_ceic",
                            "descripcion",
                            selected.ceic
                        );

                        options(
                            field("grado_anio"),
                            data.grado,
                            "c_grado_anio",
                            "nombre_grado_anio",
                            selected.grado
                        );

                        options(
                            field("secciones"),
                            data.secciones,
                            "c_seccion",
                            "nombre_seccion",
                            selected.seccion
                        );

                    } else {

                        [
                            "ceic",
                            "grado_anio",
                            "secciones"
                        ].forEach(clear);
                    }
                    category();
                    if (nonTeaching()) {
                        if (!data.ceic.length) {
                            message("No se encontraron cargos CEIC con c_niv entre 1023 y 1025.");
                        } else {
                            message("");
                        }
                    } else if (!data.niveles.length) {
                        message("La modalidad seleccionada no tiene niveles configurados.");
                    } else if (value("niveles") && !data.grado.length) {
                        message("Esta modalidad y nivel no tienen grados configurados. Solicite revisar el catálogo.");
                    } else {
                        message("");
                    }
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
                    if (name === "categoria") { category(); catalogs("categoria"); return; }
                    catalogs(name);
                });
            }
            form.addEventListener("change", changed);
            if (jq()) jq()(form).off("change.bnhMinisterial").on("change.bnhMinisterial", "select", changed);
            form.addEventListener("submit", event => {
                const inputCuil = field("cuil");

                if (
                    inputCuil
                    && normalizarCuil(inputCuil.value)
                    && !validarYCompletarDni()
                ) {
                    event.preventDefault();
                    inputCuil.focus();
                    message("Revise el CUIL antes de guardar.");
                    return;
                }

                if (pending || localityPending) {
                    event.preventDefault();
                    message("Espere a que termine la carga de opciones.");
                }
            });
            category(); enable();
            if (value("modalidad") || nonTeaching()) catalogs("inicio");
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

