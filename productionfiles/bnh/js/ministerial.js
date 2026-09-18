/* BNH Personal — 20260918.2 */
"use strict";

(() => {
    const VERSION = "20260918.2";
    const jq = () => window.jQuery;
    const hasSelect2 = () => Boolean(jq() && jq().fn && jq().fn.select2);

    function refresh(select) {
        if (select && hasSelect2()) jq()(select).trigger("change.select2");
    }

    function fillOptions(select, rows, key, label, selected = "", placeholder = "Seleccione") {
        if (!select) return;
        if (!Array.isArray(rows)) {
            throw new Error(`La respuesta no contiene opciones válidas para ${select.name}.`);
        }
        select.replaceChildren(new Option(placeholder, ""));
        rows.forEach(row => select.add(new Option(String(row[label] ?? ""), String(row[key] ?? ""))));
        const target = String(selected ?? "");
        select.value = Array.from(select.options).some(o => o.value === target) ? target : "";
        refresh(select);
    }

    async function getJson(url, controller) {
        let timedOut = false;
        const timer = window.setTimeout(() => {
            timedOut = true;
            controller.abort();
        }, 20000);

        try {
            const response = await fetch(url, {
                signal: controller.signal,
                credentials: "same-origin",
                cache: "no-store",
                headers: { "Accept": "application/json" }
            });
            if (response.redirected) {
                throw new Error("La sesión fue redirigida. Ingrese nuevamente y recargue la página.");
            }
            if (!response.ok) {
                throw new Error(`No se pudieron cargar las opciones (HTTP ${response.status}).`);
            }
            if (!response.headers.get("content-type")?.includes("application/json")) {
                throw new Error("La vista de catálogos no devolvió JSON.");
            }
            return await response.json();
        } catch (error) {
            if (timedOut) throw new Error("La carga de opciones superó 20 segundos. Reintente.");
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

            const field = name => form.querySelector(
                `[name="${name}"], [name="actividad-${name}"], [name="persona-${name}"]`
            );
            const value = name => field(name)?.value || "";
            const personalTypeCode = () => Number(value("tipo_personal") || 0);
            const nonTeaching = () => personalTypeCode() === 2;

            // ============================================================
            // CUIL -> DNI
            // ============================================================
            const normalizarCuil = raw => String(raw || "").replace(/\D/g, "");

            function validarCuil(raw) {
                const cuil = normalizarCuil(raw);
                if (!cuil) return { valido: false, vacio: true, mensaje: "" };
                if (cuil.length !== 11) {
                    return { valido: false, mensaje: "El CUIL debe tener 11 dígitos." };
                }

                const coef = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
                let total = 0;
                for (let i = 0; i < 10; i += 1) total += Number(cuil[i]) * coef[i];
                const resto = total % 11;
                let dv = 11 - resto;
                if (dv === 11) dv = 0;
                else if (dv === 10) {
                    return { valido: false, mensaje: "CUIL inválido: dígito verificador no representable." };
                }
                if (dv !== Number(cuil[10])) {
                    return { valido: false, mensaje: "CUIL inválido: el dígito verificador no coincide." };
                }
                return {
                    valido: true,
                    cuil,
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

                const result = validarCuil(inputCuil.value);
                inputCuil.classList.remove("is-valid", "is-invalid");

                if (result.vacio) {
                    setCuilFeedback(inputCuil, "");
                    return false;
                }
                if (!result.valido) {
                    inputCuil.classList.add("is-invalid");
                    setCuilFeedback(inputCuil, result.mensaje, true);
                    return false;
                }

                inputCuil.value = result.cuil;
                inputCuil.classList.add("is-valid");
                // Se conservan siempre las ocho posiciones centrales,
                // incluido el cero inicial para DNI de siete dígitos.
                inputDni.value = result.dni;
                inputDni.dispatchEvent(new Event("input", { bubbles: true }));
                inputDni.dispatchEvent(new Event("change", { bubbles: true }));

                setCuilFeedback(
                    inputCuil,
                    mostrarMensaje ? `CUIL válido. DNI ${result.dni} completado automáticamente.` : ""
                );
                return true;
            }

            const inputCuil = field("cuil");

            // ============================================================
            // PERSONA EXISTENTE: ALTA / VINCULACIÓN
            // ============================================================
            let personLookupController = null;
            let personLookupPending = false;
            let duplicatePersonDetected = false;
            let linkPersonFound = !form.dataset.personLinkUrl;

            function personFeedbackContainer() {
                if (!inputCuil) return null;

                let box = inputCuil.parentElement?.querySelector(
                    "[data-person-feedback]"
                );

                if (!box) {
                    box = document.createElement("div");
                    box.dataset.personFeedback = "1";
                    box.className = "alert mt-2 mb-0";
                    box.hidden = true;

                    const cuilFeedback =
                        inputCuil.parentElement?.querySelector(
                            "[data-cuil-feedback]"
                        );

                    if (cuilFeedback) {
                        cuilFeedback.insertAdjacentElement("afterend", box);
                    } else {
                        inputCuil.insertAdjacentElement("afterend", box);
                    }
                }

                return box;
            }

            function clearPersonFeedback() {
                const box = personFeedbackContainer();
                if (!box) return;
                box.replaceChildren();
                box.hidden = true;
                box.className = "alert mt-2 mb-0";
            }

            function showPersonFeedback({
                text = "",
                kind = "info",
                url = "",
                label = ""
            } = {}) {
                const box = personFeedbackContainer();
                if (!box) return;

                box.replaceChildren();
                box.className = `alert alert-${kind} mt-2 mb-0`;
                box.hidden = !text;

                if (!text) return;

                const span = document.createElement("span");
                span.textContent = text;
                box.append(span);

                if (url && label) {
                    const link = document.createElement("a");
                    link.href = url;
                    link.className = "btn btn-sm btn-outline-primary ms-3";
                    link.textContent = label;
                    box.append(link);
                }
            }

            function clearLinkedIdentity() {
                if (!form.dataset.personLinkUrl) return;

                ["dni", "apellido", "nombre"].forEach(name => {
                    const input = field(name);
                    if (input) input.value = "";
                });

                linkPersonFound = false;
            }

            async function checkExistingPersonForAlta(cuil) {
                if (!form.dataset.personCheckUrl) return;

                personLookupController?.abort();
                const current = new AbortController();
                personLookupController = current;
                personLookupPending = true;
                duplicatePersonDetected = false;

                try {
                    const url = new URL(
                        form.dataset.personCheckUrl,
                        window.location.origin
                    );
                    url.searchParams.set("cuil", cuil);

                    const data = await getJson(url, current);
                    if (personLookupController !== current) return;

                    if (!data.existe) {
                        duplicatePersonDetected = false;
                        showPersonFeedback({
                            text: data.mensaje || "CUIL disponible para una nueva alta.",
                            kind: "success"
                        });
                        return;
                    }

                    duplicatePersonDetected = true;

                    if (data.estado === "VISIBLE") {
                        showPersonFeedback({
                            text: data.mensaje,
                            kind: "warning",
                            url: data.accion_url,
                            label: data.accion_label || "Ver ficha"
                        });
                        return;
                    }

                    if (data.estado === "VINCULAR") {
                        showPersonFeedback({
                            text: data.mensaje,
                            kind: "warning",
                            url: data.accion_url,
                            label: data.accion_label || "Vincular existente"
                        });
                        return;
                    }

                    showPersonFeedback({
                        text: data.mensaje || "El CUIL ya se encuentra registrado.",
                        kind: "danger"
                    });

                } catch (error) {
                    if (
                        personLookupController === current
                        && error.name !== "AbortError"
                    ) {
                        duplicatePersonDetected = true;
                        showPersonFeedback({
                            text: error.message,
                            kind: "danger"
                        });
                    }
                } finally {
                    if (personLookupController === current) {
                        personLookupPending = false;
                    }
                }
            }

            async function searchPersonForLink(cuil) {
                if (!form.dataset.personLinkUrl) return;

                personLookupController?.abort();
                const current = new AbortController();
                personLookupController = current;
                personLookupPending = true;
                linkPersonFound = false;

                try {
                    const url = new URL(
                        form.dataset.personLinkUrl,
                        window.location.origin
                    );
                    url.searchParams.set("cuil", cuil);

                    const data = await getJson(url, current);
                    if (personLookupController !== current) return;

                    if (!data.existe) {
                        clearLinkedIdentity();
                        showPersonFeedback({
                            text: data.mensaje || "No se encontró personal registrado con ese CUIL.",
                            kind: "warning",
                            url: data.alta_url || "",
                            label: data.alta_url ? "Ir a Alta de personal" : ""
                        });
                        return;
                    }

                    const dni = field("dni");
                    const apellido = field("apellido");
                    const nombre = field("nombre");

                    if (dni) dni.value = data.dni || "";
                    if (apellido) apellido.value = data.apellido || "";
                    if (nombre) nombre.value = data.nombre || "";

                    [dni, apellido, nombre].forEach(input => {
                        if (!input) return;
                        input.dispatchEvent(
                            new Event("input", { bubbles: true })
                        );
                        input.dispatchEvent(
                            new Event("change", { bubbles: true })
                        );
                    });

                    linkPersonFound = true;

                    showPersonFeedback({
                        text: `Persona encontrada: ${data.apellido || ""}, ${data.nombre || ""}.`,
                        kind: "success",
                        url: data.detalle_url || "",
                        label: data.detalle_url ? "Ver ficha actual" : ""
                    });

                } catch (error) {
                    if (
                        personLookupController === current
                        && error.name !== "AbortError"
                    ) {
                        clearLinkedIdentity();
                        showPersonFeedback({
                            text: error.message,
                            kind: "danger"
                        });
                    }
                } finally {
                    if (personLookupController === current) {
                        personLookupPending = false;
                    }
                }
            }

            async function processCuil({ mostrarMensaje = true } = {}) {
                if (!inputCuil) return true;

                const result = validarCuil(inputCuil.value);

                if (!result.valido) {
                    validarYCompletarDni({ mostrarMensaje });
                    duplicatePersonDetected = false;
                    if (form.dataset.personLinkUrl) clearLinkedIdentity();
                    clearPersonFeedback();
                    return false;
                }

                validarYCompletarDni({ mostrarMensaje });

                if (form.dataset.personCheckUrl) {
                    await checkExistingPersonForAlta(result.cuil);
                } else if (form.dataset.personLinkUrl) {
                    await searchPersonForLink(result.cuil);
                }

                return true;
            }

            if (inputCuil) {
                inputCuil.addEventListener("input", () => {
                    inputCuil.classList.remove("is-valid", "is-invalid");
                    setCuilFeedback(inputCuil, "");
                    duplicatePersonDetected = false;
                    clearPersonFeedback();

                    if (form.dataset.personLinkUrl) {
                        clearLinkedIdentity();
                    }

                    if (normalizarCuil(inputCuil.value).length === 11) {
                        processCuil();
                    }
                });

                inputCuil.addEventListener("blur", () => {
                    if (normalizarCuil(inputCuil.value)) {
                        processCuil();
                    }
                });

                if (normalizarCuil(inputCuil.value).length === 11) {
                    processCuil({ mostrarMensaje: false });
                }
            }

            // ============================================================
            // ESTADO UI
            // ============================================================
            let cargoRequestId = 0;
            let curricularRequestId = 0;
            let cargoController = null;
            let curricularController = null;
            let localController = null;
            let conditionController = null;
            let cargoPending = false;
            let curricularPending = false;
            let localityPending = false;
            let conditionPending = false;

            const status = document.createElement("div");
            status.className = "alert alert-info mt-3";
            status.setAttribute("role", "status");
            status.setAttribute("aria-live", "polite");
            status.hidden = true;
            form.prepend(status);

            const message = text => {
                status.textContent = text || "";
                status.hidden = !text;
            };

            const clear = name => fillOptions(field(name), [], "", "");
            const setDisabled = (name, state) => {
                const input = field(name);
                if (!input) return;
                input.disabled = Boolean(state);
                refresh(input);
            };
            const setVisible = (name, visible) => {
                const input = field(name);
                if (!input) return;
                const wrapper = input.closest("[data-field]");
                if (wrapper) wrapper.hidden = !visible;
            };

            function updateCategoryUI() {
                const curricularFields = [
                    "modalidad_curricular",
                    "nivel_curricular",
                    "titulacion",
                    "espacio_curricular",
                    "grado_anio",
                    "secciones"
                ];
                curricularFields.forEach(name => setVisible(name, !nonTeaching()));
                form.querySelectorAll("[data-curricular-section]").forEach(el => {
                    el.hidden = nonTeaching();
                });

                if (nonTeaching()) {
                    curricularFields.forEach(name => {
                        const input = field(name);
                        if (!input) return;
                        input.value = "";
                        input.disabled = true;
                        refresh(input);
                    });
                    const source = field("titulacion_fuente");
                    if (source) source.value = "";
                }
            }

            function enable() {
                // Circuito Cargo / CEIC
                setDisabled("niveles", !value("modalidad") || cargoPending);
                setDisabled(
                    "ceic",
                    cargoPending || (!nonTeaching() && !value("niveles"))
                );

                // Circuito curricular
                const hideCurricular = nonTeaching();
                setDisabled("modalidad_curricular", hideCurricular || curricularPending);
                setDisabled(
                    "nivel_curricular",
                    hideCurricular || curricularPending || !value("modalidad_curricular")
                );
                setDisabled(
                    "titulacion",
                    hideCurricular || curricularPending || !value("nivel_curricular")
                );
                setDisabled(
                    "espacio_curricular",
                    hideCurricular || curricularPending || !value("titulacion")
                );
                setDisabled(
                    "grado_anio",
                    hideCurricular || curricularPending || !value("nivel_curricular")
                );
                setDisabled(
                    "secciones",
                    hideCurricular || curricularPending || !value("nivel_curricular")
                );

                setDisabled(
                    "cond_actividad",
                    !value("tipo_personal") || !value("sit_revista") || conditionPending
                );

                setDisabled("localidad", !value("provincia") || localityPending);
            }

            // ============================================================
            // CIRCUITO CARGO / CEIC (LEGACY)
            // ============================================================
            async function loadCargoCatalogs(source = "inicio") {
                cargoController?.abort();
                cargoController = new AbortController();
                const current = cargoController;
                const id = ++cargoRequestId;

                const selected = {
                    nivel: value("niveles"),
                    ceic: value("ceic")
                };

                if (source === "tipo_personal") clear("ceic");
                if (source === "modalidad") {
                    clear("niveles");
                    clear("ceic");
                    selected.nivel = "";
                    selected.ceic = "";
                }
                if (source === "niveles") {
                    clear("ceic");
                    selected.ceic = "";
                }

                if (!value("modalidad") && !nonTeaching()) {
                    cargoPending = false;
                    enable();
                    return;
                }

                cargoPending = true;
                enable();
                message("Cargando Cargo / CEIC…");

                try {
                    if (!form.dataset.catalogUrl) throw new Error("Falta data-catalog-url.");
                    const url = new URL(form.dataset.catalogUrl, window.location.origin);
                    url.searchParams.set("tipo_personal", String(personalTypeCode() || ""));
                    url.searchParams.set("modalidad", value("modalidad"));
                    url.searchParams.set("nivel", selected.nivel);

                    const data = await getJson(url, current);
                    if (id !== cargoRequestId) return;

                    if (nonTeaching()) {
                        // Modalidad/nivel legacy siguen funcionando, pero NO determinan el CEIC.
                        if (value("modalidad")) {
                            fillOptions(field("niveles"), data.niveles, "c_nivel", "descrip_nivel", selected.nivel);
                        }
                        // Regla histórica: CEIC 1023-1025.
                        fillOptions(field("ceic"), data.ceic, "c_ceic", "descripcion", selected.ceic);
                    } else {
                        if (value("modalidad")) {
                            fillOptions(field("niveles"), data.niveles, "c_nivel", "descrip_nivel", selected.nivel);
                        }
                        if (selected.nivel || value("niveles")) {
                            fillOptions(field("ceic"), data.ceic, "c_ceic", "descripcion", selected.ceic);
                        }
                    }
                    message("");
                } catch (error) {
                    if (id === cargoRequestId && error.name !== "AbortError") message(error.message);
                } finally {
                    if (id === cargoRequestId) {
                        cargoPending = false;
                        enable();
                    }
                }
            }

            // ============================================================
            // CIRCUITO CURRICULAR NUEVO
            // ============================================================
            async function loadCurricularCatalogs(source = "inicio") {
                if (nonTeaching()) {
                    updateCategoryUI();
                    enable();
                    return;
                }

                curricularController?.abort();
                curricularController = new AbortController();
                const current = curricularController;
                const id = ++curricularRequestId;

                const selected = {
                    nivel: value("nivel_curricular"),
                    titulacion: value("titulacion"),
                    espacio: value("espacio_curricular"),
                    grado: value("grado_anio"),
                    seccion: value("secciones")
                };

                if (source === "modalidad_curricular") {
                    ["nivel_curricular", "titulacion", "espacio_curricular", "grado_anio", "secciones"].forEach(clear);
                    selected.nivel = "";
                    selected.titulacion = "";
                    selected.espacio = "";
                    selected.grado = "";
                    selected.seccion = "";
                } else if (source === "nivel_curricular") {
                    ["titulacion", "espacio_curricular", "grado_anio", "secciones"].forEach(clear);
                    selected.titulacion = "";
                    selected.espacio = "";
                    selected.grado = "";
                    selected.seccion = "";
                } else if (source === "titulacion") {
                    clear("espacio_curricular");
                    selected.espacio = "";
                }

                if (!value("modalidad_curricular")) {
                    curricularPending = false;
                    enable();
                    return;
                }

                curricularPending = true;
                enable();
                message("Cargando ubicación curricular…");

                try {
                    if (!form.dataset.curricularUrl) throw new Error("Falta data-curricular-url.");
                    const url = new URL(form.dataset.curricularUrl, window.location.origin);
                    url.searchParams.set("tipo_personal", String(personalTypeCode() || ""));
                    url.searchParams.set("modalidad_curricular", value("modalidad_curricular"));
                    url.searchParams.set("nivel_curricular", selected.nivel);
                    url.searchParams.set("titulacion", selected.titulacion);

                    const data = await getJson(url, current);
                    if (id !== curricularRequestId) return;

                    fillOptions(
                        field("nivel_curricular"),
                        data.niveles,
                        "c_nivel",
                        "descripcion",
                        selected.nivel,
                        "Seleccione nivel curricular"
                    );

                    fillOptions(
                        field("titulacion"),
                        data.titulaciones,
                        "id_titulacion",
                        "descripcion",
                        selected.titulacion,
                        "Seleccione titulación"
                    );

                    const sourceField = field("titulacion_fuente");
                    if (sourceField) sourceField.value = data.fuente_titulacion || "";

                    fillOptions(
                        field("espacio_curricular"),
                        data.espacios,
                        "id",
                        "nombre",
                        selected.espacio,
                        "Seleccione espacio curricular"
                    );
                    fillOptions(
                        field("grado_anio"),
                        data.grados,
                        "c_grado_anio",
                        "nombre_grado_anio",
                        selected.grado,
                        "Seleccione grado/año"
                    );
                    fillOptions(
                        field("secciones"),
                        data.secciones,
                        "c_seccion",
                        "nombre_seccion",
                        selected.seccion,
                        "Seleccione sección"
                    );

                    message("");
                } catch (error) {
                    if (id === curricularRequestId && error.name !== "AbortError") message(error.message);
                } finally {
                    if (id === curricularRequestId) {
                        curricularPending = false;
                        enable();
                    }
                }
            }

            // ============================================================
            // CONDICIÓN DE ACTIVIDAD
            // ============================================================
            async function loadConditions() {
                conditionController?.abort();
                const current = new AbortController();
                conditionController = current;

                const selected = value("cond_actividad");
                clear("cond_actividad");

                if (!value("tipo_personal") || !value("sit_revista")) {
                    conditionPending = false;
                    enable();
                    return;
                }

                conditionPending = true;
                enable();
                message("Cargando condiciones de actividad…");

                try {
                    if (!form.dataset.conditionsUrl) {
                        throw new Error("Falta data-conditions-url.");
                    }

                    const url = new URL(
                        form.dataset.conditionsUrl,
                        window.location.origin
                    );
                    url.searchParams.set("tipo_personal", value("tipo_personal"));
                    url.searchParams.set("sit_revista", value("sit_revista"));

                    const data = await getJson(url, current);
                    if (conditionController !== current) return;

                    fillOptions(
                        field("cond_actividad"),
                        data.condiciones || [],
                        "id",
                        "label",
                        selected,
                        "Seleccione condición de actividad"
                    );
                    message("");
                } catch (error) {
                    if (
                        conditionController === current
                        && error.name !== "AbortError"
                    ) {
                        message(error.message);
                    }
                } finally {
                    if (conditionController === current) {
                        conditionPending = false;
                        enable();
                    }
                }
            }

            // ============================================================
            // LOCALIDADES
            // ============================================================
            async function loadLocalities() {
                localController?.abort();
                const current = new AbortController();
                localController = current;
                const selected = value("localidad");
                clear("localidad");
                localityPending = true;
                enable();

                try {
                    if (!value("provincia")) return;
                    if (!form.dataset.localitiesUrl) throw new Error("Falta data-localities-url.");
                    const url = new URL(form.dataset.localitiesUrl, window.location.origin);
                    url.searchParams.set("provincia", value("provincia"));
                    const rows = await getJson(url, current);
                    if (localController === current) {
                        fillOptions(field("localidad"), rows, "c_localidad", "descrip_localidad", selected);
                    }
                } catch (error) {
                    if (localController === current && error.name !== "AbortError") message(error.message);
                } finally {
                    if (localController === current) {
                        localityPending = false;
                        enable();
                    }
                }
            }

            // ============================================================
            // EVENTOS
            // ============================================================
            let scheduled = false;
            let changedName = "";

            function changed(event) {
                const target = event.target;
                const names = [
                    "tipo_personal",
                    "sit_revista",
                    "modalidad",
                    "niveles",
                    "modalidad_curricular",
                    "nivel_curricular",
                    "titulacion",
                    "provincia"
                ];
                const name = names.find(key => field(key) === target);
                if (!name) return;

                changedName = name;
                if (scheduled) return;
                scheduled = true;
                queueMicrotask(() => {
                    scheduled = false;
                    const currentName = changedName;

                    if (currentName === "provincia") {
                        loadLocalities();
                        return;
                    }
                    if (currentName === "tipo_personal") {
                        updateCategoryUI();
                        loadCargoCatalogs("tipo_personal");
                        loadCurricularCatalogs("tipo_personal");
                        loadConditions();
                        return;
                    }
                    if (currentName === "sit_revista") {
                        loadConditions();
                        return;
                    }
                    if (currentName === "modalidad" || currentName === "niveles") {
                        loadCargoCatalogs(currentName);
                        return;
                    }
                    loadCurricularCatalogs(currentName);
                });
            }

            form.addEventListener("change", changed);
            if (jq()) {
                jq()(form)
                    .off("change.bnhMinisterial")
                    .on("change.bnhMinisterial", "select", changed);
            }

            form.addEventListener("submit", event => {
                const cuil = field("cuil");

                if (
                    cuil
                    && normalizarCuil(cuil.value)
                    && !validarYCompletarDni()
                ) {
                    event.preventDefault();
                    cuil.focus();
                    message("Revise el CUIL antes de guardar.");
                    return;
                }

                if (personLookupPending) {
                    event.preventDefault();
                    message("Espere a que termine la consulta de la persona.");
                    return;
                }

                if (form.dataset.personCheckUrl && duplicatePersonDetected) {
                    event.preventDefault();
                    cuil?.focus();
                    message(
                        "La persona ya está registrada. Utilice la acción indicada junto al CUIL."
                    );
                    return;
                }

                if (form.dataset.personLinkUrl && !linkPersonFound) {
                    event.preventDefault();
                    cuil?.focus();
                    message(
                        "Primero ingrese un CUIL correspondiente a una persona ya registrada."
                    );
                    return;
                }

                if (
                    cargoPending
                    || curricularPending
                    || localityPending
                    || conditionPending
                ) {
                    event.preventDefault();
                    message("Espere a que termine la carga de opciones.");
                }
            });

            updateCategoryUI();
            enable();

            if (value("modalidad") || nonTeaching()) loadCargoCatalogs("inicio");
            if (!nonTeaching() && value("modalidad_curricular")) loadCurricularCatalogs("inicio");
            if (value("tipo_personal") && value("sit_revista")) loadConditions();
        });

        document.querySelectorAll("form").forEach(form => {
            if (form.dataset.bnhSubmitBound) return;
            form.dataset.bnhSubmitBound = "1";
            form.addEventListener("submit", event => {
                if (event.defaultPrevented) return;
                if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
                    event.preventDefault();
                    return;
                }
                if (form.dataset.submitting) {
                    event.preventDefault();
                    return;
                }
                form.dataset.submitting = "1";
                form.querySelectorAll('button[type="submit"],button:not([type])').forEach(button => {
                    button.disabled = true;
                });
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }

    window.addEventListener("pageshow", () => {
        document.querySelectorAll("form").forEach(form => {
            delete form.dataset.submitting;
            form.querySelectorAll('button[type="submit"],button:not([type])').forEach(button => {
                button.disabled = false;
            });
        });
    });
})();
