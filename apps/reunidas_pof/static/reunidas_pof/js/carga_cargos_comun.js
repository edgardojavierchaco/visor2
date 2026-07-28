/**
 * Normaliza el estado textual de una oferta al contrato visual compartido.
 *
 * - Reconoce los estados activos y de baja con sus variantes actuales.
 * - Devuelve siempre codigo, texto y clase para las tarjetas de oferta.
 * - No consulta campos ni modifica el objeto de origen.
 */
function normalizarEstadoOferta(valorEstado) {
    const normalizado = normalizarTextoOferta(valorEstado).toUpperCase();

    if (normalizado === "A" || normalizado.includes("ACTIVA") || normalizado.includes("ACTIVO") || normalizado.includes("VIGENTE")) {
        return { codigo: "ACTIVA", texto: "ACTIVA", clase: "pof-offer-status-active" };
    }

    if (normalizado === "B" || normalizado.includes("BAJA")) {
        return { codigo: "BAJA", texto: "BAJA", clase: "pof-offer-status-low" };
    }

    return { codigo: "SIN_DATO", texto: "SIN DATO", clase: "pof-offer-status-unknown" };
}

/**
 * Construye el badge HTML a partir de un estado de oferta ya normalizado.
 *
 * - Conserva las clases y el texto visibles usados por ambos flujos.
 * - Recibe solo el contrato de estado, sin acceder al DOM de una pantalla.
 * - No modifica el objeto de estado ni otros datos de la oferta.
 */
function renderizarBadgeEstadoOfertaComun(estado) {
    return `<span class="pof-offer-status-badge ${estado.clase}">${estado.texto}</span>`;
}

/**
 * Genera la clave estable para identificar un cargo temporal por CEIC y unidad.
 *
 * - Normaliza el CEIC como número y la unidad en mayúsculas.
 * - Mantiene el contrato usado para detectar cargos repetidos o consolidarlos.
 * - No muta los cargos ni el array temporal.
 */
function claveCargoTemporal(ceic, unidadCantidad) {
    return `${Number(ceic || 0)}|${String(unidadCantidad || "").toUpperCase()}`;
}

/**
 * Detecta cargos de horas cátedra por el comienzo de su denominación.
 *
 * - Tolera mayúsculas, minúsculas y tildes.
 * - Reconoce únicamente HORA u HORAS como primera palabra.
 * - Evita clasificar como horas los cargos que contienen esa palabra más adelante.
 */
function cargoEmpiezaConHoraCatedra(nombreCargo) {
    const normalizado = String(nombreCargo || "")
        .trim()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toUpperCase();

    return /^HORAS?\b/.test(normalizado);
}

/**
 * Crea el control compartido del panel opcional de observación de un cargo.
 *
 * - Muestra y oculta el panel usando las clases visuales POF existentes.
 * - Reubica la acción principal para conservar el flujo de Reunida y Proyecto Especial.
 * - Permite limpiar la observación solo cuando la persona usuaria lo solicita.
 */
function crearControlObservacionCargo({
    panel,
    botonMostrar,
    accionesPanel,
    botonPrincipal,
    textarea,
}) {
    return {
        mostrar() {
            panel.classList.remove("pof-hidden");
            botonMostrar.classList.add("pof-hidden");
            accionesPanel.appendChild(botonPrincipal);
            textarea.focus();
        },
        ocultar(limpiar = false) {
            if (limpiar) {
                textarea.value = "";
            }

            panel.classList.add("pof-hidden");
            botonMostrar.classList.remove("pof-hidden");
            botonMostrar.parentElement.appendChild(botonPrincipal);
        },
    };
}


/**
 * Construye un CUEANEXO a partir de CUE y Anexo.
 *
 * - Normaliza el CUE a un máximo de 7 dígitos.
 * - Normaliza el Anexo a un máximo de 2 dígitos.
 * - Si el Anexo está vacío, usa "00" para construir el CUEANEXO.
 * - Solo devuelve CUEANEXO cuando el CUE tiene 7 dígitos y el Anexo efectivo 2.
 * - No modifica el DOM ni los valores recibidos.
 */
function construirCueanexoDesdePartes(cueValor, anexoValor) {
    const cue = String(cueValor || "")
        .replace(/\D/g, "")
        .slice(0, 7);

    const anexo = String(anexoValor || "")
        .replace(/\D/g, "")
        .slice(0, 2);

    const anexoEfectivo = anexo || "00";

    return {
        cue,
        anexo,
        cueanexo:
            cue.length === 7 && anexoEfectivo.length === 2
                ? cue + anexoEfectivo
                : "",
    };
}
