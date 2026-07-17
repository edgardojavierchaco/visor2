    const cargarCargosReunidaConfigElement = document.getElementById("cargarCargosReunidaConfig");
    if (!cargarCargosReunidaConfigElement) {
        throw new Error("Falta la configuracion de Alta de Cargos de Reunida.");
    }
    const CARGAR_CARGOS_REUNIDA_CONFIG = JSON.parse(cargarCargosReunidaConfigElement.textContent || "{}");
    const URLS_CARGAR_CARGOS_REUNIDA = CARGAR_CARGOS_REUNIDA_CONFIG.urls || {};
    const URL_VALIDAR_REUNIDA = URLS_CARGAR_CARGOS_REUNIDA.validarReunida;
    const URL_BUSCAR_PADRON = URLS_CARGAR_CARGOS_REUNIDA.buscarPadron;
    const URL_BUSCAR_CEIC = URLS_CARGAR_CARGOS_REUNIDA.buscarCeic;
    const URL_CATALOGO_CEIC = URLS_CARGAR_CARGOS_REUNIDA.catalogoCeic;
    const URL_GUARDAR_CARGA_POF = URLS_CARGAR_CARGOS_REUNIDA.guardarCargaPof;
    const URL_DETALLE_REUNIDA = URLS_CARGAR_CARGOS_REUNIDA.detalleReunida;
    if (!URL_VALIDAR_REUNIDA || !URL_BUSCAR_PADRON || !URL_BUSCAR_CEIC || !URL_CATALOGO_CEIC || !URL_GUARDAR_CARGA_POF || !URL_DETALLE_REUNIDA) {
        throw new Error("La configuracion de Alta de Cargos de Reunida esta incompleta.");
    }
    let cabeceraReunidaValidada = false;
    let cabeceraReunida = null;
    let padronSeleccionado = null;
    let ofertasPadronSeleccionadas = [];
    let resultadosPadronActuales = [];
    let ofertaAbiertaIndex = null;
    let mostrarOtrasOfertas = false;
    let filtroOfertaTexto = "";
    let filtroOfertaEstado = "TODOS";
    let cargosTemporales = [];
    let temporizadorCeic = null;
    let ultimoTextoCeic = "";
    let secuenciaBusquedaCeic = 0;
    let catalogoCeic = [];
    let catalogoCeicNivelCargado = "";
    let catalogoCeicCargado = false;
    let catalogoCeicCargando = false;
    let catalogoCeicPromise = null;
    let guardandoCarga = false;
    let modoCeicOtros = false;
    let ceicSeleccionadoFueraSugerencia = false;
    let unidadAutoSeleccionadaPorCeic = false;
    const LIMITE_RESULTADOS_CEIC = 5;
    const CAMPOS_HISTORICOS_EDITABLES = [
        { clave: "establecimiento", etiqueta: "Establecimiento", campos: ["nom_est", "establecimiento", "nombre_establecimiento"], principal: "nom_est" },
        { clave: "localidad", etiqueta: "Localidad", campos: ["localidad"], principal: "localidad" },
        { clave: "departamento", etiqueta: "Departamento", campos: ["departamento"], principal: "departamento" },
        { clave: "categoria", etiqueta: "Categoría", campos: ["categoria", "categoria_loc"], principal: "categoria" },
        { clave: "jornada", etiqueta: "Jornada", campos: ["jornada", "jornada_loc"], principal: "jornada" },
    ];

    // DOM Elements - Cabecera
    const anioInput = document.getElementById("anio");
    const nivelSelect = document.getElementById("nivel");
    const cabeceraReunidaCampos = document.getElementById("cabeceraReunidaCampos");
    const cabeceraReunidaIdInput = document.getElementById("cabecera_reunida_id");
    const anioValidadoInput = document.getElementById("anio_validado");
    const nivelValidadoInput = document.getElementById("nivel_validado");
    const btnValidarReunida = document.getElementById("btnValidarReunida");
    const btnCambiarReunida = document.getElementById("btnCambiarReunida");
    const estadoCabecera = document.getElementById("estadoCabecera");

    // DOM Elements - Padron
    const cueBaseInput = document.getElementById("cueBase");
    const anexoInput = document.getElementById("anexo");
    const cueanexoInput = document.getElementById("cueanexo");
    const btnBuscarPadron = document.getElementById("btnBuscarPadron");

    // DOM Elements - Otros Bloques
    const estadoBusqueda = document.getElementById("estadoBusqueda");
    const bloqueBusquedaPadron = document.getElementById("bloqueBusquedaPadron");
    const bloquePadron = document.getElementById("bloquePadron");
    const resultadosPadron = document.getElementById("resultadosPadron");
    const bloqueSeleccion = document.getElementById("bloqueSeleccion");
    const detalleSeleccion = document.getElementById("detalleSeleccion");
    const bloqueCargos = document.getElementById("bloqueCargos");
    const cargoListaWrapper = document.getElementById("cargoListaWrapper");
    const cargoInfoGeneral = document.getElementById("cargoInfoGeneral");
    const tablaCargos = document.getElementById("tablaCargos");
    const cargoTotalPuntos = document.getElementById("cargoTotalPuntos");
    const bloqueGuardarCarga = document.getElementById("bloqueGuardarCarga");
    const btnGuardarCarga = document.getElementById("btnGuardarCarga");
    const estadoGuardado = document.getElementById("estadoGuardado");
    const modalConfirmarCarga = document.getElementById("modalConfirmarCarga");
    const tablaConfirmarCarga = document.getElementById("tablaConfirmarCarga");
    const modalCargoTotalPuntos = document.getElementById("modalCargoTotalPuntos");
    const btnConfirmarGuardarCarga = document.getElementById("btnConfirmarGuardarCarga");
    const hayAniosReunidaDisponibles = Array.from(anioInput.options).some(option => option.value);

    // DOM Elements - Cargos
    const ceicBusqueda = document.getElementById("ceicBusqueda");
    const ceicLoading = document.getElementById("ceicLoading");
    const ceicSeleccionado = document.getElementById("ceicSeleccionado");
    const cargoSeleccionado = document.getElementById("cargoSeleccionado");
    const cantidadCargo = document.getElementById("cantidadCargo");
    const unidadCargo = document.getElementById("unidadCargo");
    const puntosCargo = document.getElementById("puntosCargo");
    const totalCargo = document.getElementById("totalCargo");
    const observacionCargo = document.getElementById("observacionCargo");
    const observationCargoActions = document.getElementById("observationCargoActions");
    const btnAgregarCargoLista = document.getElementById("btnAgregarCargoLista");
    const panelObservacionCargo = document.getElementById("panelObservacionCargo");
    const btnMostrarObservacion = document.getElementById("btnMostrarObservacion");
    const btnQuitarObservacion = document.getElementById("btnQuitarObservacion");
    const sugerenciasCeic = document.getElementById("sugerenciasCeic");
    const modoCeicRadios = document.querySelectorAll('input[name="modoCeic"]');
    const mensajeCeic = document.getElementById("mensajeCeic");
    const controlObservacionCargo = crearControlObservacionCargo({
        panel: panelObservacionCargo,
        botonMostrar: btnMostrarObservacion,
        accionesPanel: observationCargoActions,
        botonPrincipal: btnAgregarCargoLista,
        textarea: observacionCargo,
    });

    function valor(dato) {
        if (dato === null || dato === undefined || dato === "") {
            return "—";
        }

        return dato;
    }

    function valorHtml(dato) {
        if (dato === null || dato === undefined || dato === "") {
            return "-";
        }
        return escaparHtml(dato);
    }

    function formatearTotalPuntos(total) {
        const numero = Number(total || 0);
        return numero.toFixed(2).replace(".", ",");
    }

    function obtenerCantidadCargoTemporal(cargo) {
        const cantidad = Number(cargo && cargo.cantidad);
        return Number.isInteger(cantidad) && cantidad > 0 ? cantidad : 0;
    }

    function calcularTotalCargoTemporal(cargo) {
        const cantidad = obtenerCantidadCargoTemporal(cargo);
        const puntos = Number(cargo && cargo.puntos_asignados);
        return cantidad * (Number.isFinite(puntos) ? puntos : 0);
    }

    function actualizarTotalCargoTemporal(cargo) {
        if (!cargo) {
            return "0.00";
        }

        cargo.total = calcularTotalCargoTemporal(cargo).toFixed(2);
        return cargo.total;
    }

    function ordenarCargosTemporales() {
        cargosTemporales.sort((cargoA, cargoB) => {
            const ceicA = Number(cargoA && cargoA.ceic);
            const ceicB = Number(cargoB && cargoB.ceic);
            const valorA = Number.isFinite(ceicA) ? ceicA : Infinity;
            const valorB = Number.isFinite(ceicB) ? ceicB : Infinity;

            if (valorA !== valorB) {
                return valorA - valorB;
            }

            return String(cargoA && cargoA.unidad_cantidad || "").localeCompare(
                String(cargoB && cargoB.unidad_cantidad || "")
            );
        });
    }

    function calcularTotalPuntosCargos() {
        return cargosTemporales.reduce((total, cargo) => {
            return total + calcularTotalCargoTemporal(cargo);
        }, 0);
    }

    /**
     * Devuelve el nivel CEIC de la cabecera Reunida que debe usar el autocompletado.
     *
     * - Toma el nivel validado cuando la cabecera ya quedó bloqueada.
     * - Devuelve cadena vacía cuando todavía no hay una Reunida válida para filtrar CEIC.
     */
    function obtenerNivelCeicActivo() {
        if (!cabeceraReunidaValidada) {
            return "";
        }

        return String(
            nivelValidadoInput.value
            || (cabeceraReunida && cabeceraReunida.nivel)
            || nivelSelect.value
            || ""
        ).trim();
    }

    /**
     * Limpia el catálogo CEIC cargado para forzar una recarga al cambiar la cabecera.
     *
     * - Borra la caché en memoria y cualquier sugerencia visible.
     * - También invalida búsquedas en curso para evitar cruces entre niveles.
     * - No toca la lista de cargos ya cargada ni el resto del formulario.
     */
    function reiniciarCatalogoCeic() {
        clearTimeout(temporizadorCeic);
        secuenciaBusquedaCeic += 1;
        ultimoTextoCeic = "";
        catalogoCeic = [];
        catalogoCeicNivelCargado = "";
        catalogoCeicCargado = false;
        catalogoCeicCargando = false;
        catalogoCeicPromise = null;
        sugerenciasCeic.innerHTML = "";
        sugerenciasCeic.classList.add("pof-hidden");
        cambiarModoCeic(false);
    }

    /**
     * Muestra mensajes cortos bajo el campo CEIC sin interrumpir el flujo.
     *
     * - Reutiliza `pof-field-hint` y `pof-hidden` del sistema visual actual.
     * - Evita alertas para validaciones de búsqueda y selección CEIC.
     * - Mantiene el texto cerca del control que originó el estado.
     */
    function mostrarMensajeCeic(mensaje) {
        mensajeCeic.textContent = mensaje || "";
        mensajeCeic.classList.toggle("pof-hidden", !mensaje);
    }

    function mostrarCargaCeic(cargando) {
        ceicLoading.classList.toggle("pof-hidden", !cargando);
        ceicLoading.setAttribute("aria-hidden", cargando ? "false" : "true");
    }

    /**
     * Limpia la selección CEIC vigente cuando cambia el modo o el texto.
     *
     * - Evita guardar un CEIC seleccionado bajo un modo anterior.
     * - Conserva cantidad, unidad y observación porque no pertenecen al CEIC.
     * - Oculta sugerencias vencidas y reinicia el total calculado del cargo actual.
     */
    function limpiarSeleccionCeicActual() {
        clearTimeout(temporizadorCeic);
        secuenciaBusquedaCeic += 1;
        ceicSeleccionado.value = "";
        ceicSeleccionadoFueraSugerencia = false;
        cargoSeleccionado.value = "";
        puntosCargo.value = "";
        totalCargo.value = "0";
        unidadCargo.value = "CARGO";
        unidadAutoSeleccionadaPorCeic = false;
        sugerenciasCeic.innerHTML = "";
        sugerenciasCeic.classList.add("pof-hidden");
    }

    function mensajeModoCeicActual() {
        return modoCeicOtros
            ? "Fuera de sugerencia. Revisá antes de guardar."
            : "CEIC sugeridos para este nivel.";
    }

    /**
     * Cambia entre CEIC sugeridos y Otros CEIC sin borrar el texto ingresado.
     *
     * - El modo solo define el origen de búsqueda, no es un dato del cargo.
     * - Limpia la selección oficial previa porque puede no corresponder al nuevo modo.
     * - Puede relanzar la búsqueda con el mismo código visible cuando el usuario cambia radio.
     */
    function cambiarModoCeic(usarOtros, opciones = {}) {
        const limpiarTexto = Boolean(opciones.limpiarTexto);
        const relanzarBusqueda = Boolean(opciones.relanzarBusqueda);

        modoCeicOtros = Boolean(usarOtros);
        modoCeicRadios.forEach(radio => {
            radio.checked = modoCeicOtros
                ? radio.value === "otros"
                : radio.value === "sugeridos";
        });

        if (limpiarTexto) {
            ceicBusqueda.value = "";
        }

        ultimoTextoCeic = "";
        limpiarSeleccionCeicActual();
        mostrarMensajeCeic(mensajeModoCeicActual());

        if (relanzarBusqueda && ceicBusqueda.value.trim()) {
            buscarCeicDinamico();
        }
    }

    /**
     * Normaliza el texto ingresado en CEIC para buscar solo por código.
     *
     * - Elimina cualquier carácter no numérico.
     * - Limita el valor visible a 3 dígitos.
     * - Devuelve si hubo corrección para mostrar la advertencia correspondiente.
     */
    function normalizarEntradaCeic(valorOriginal) {
        const valor = String(valorOriginal || "");
        const normalizado = valor.replace(/\D/g, "").slice(0, 3);
        return {
            valor: normalizado,
            corregido: valor !== normalizado,
        };
    }

    /**
     * Autoselecciona la unidad al elegir un CEIC de horas cátedra.
     *
     * - Solo se ejecuta al seleccionar un CEIC de la lista.
     * - No observa cambios manuales posteriores del usuario.
     * - No fuerza unidad cuando el cargo no comienza con HORA/HORAS.
     */
    function aplicarUnidadPorCargoSeleccionado(nombreCargo) {
        if (cargoEmpiezaConHoraCatedra(nombreCargo)) {
            unidadCargo.value = "HORA_CATEDRA";
            unidadAutoSeleccionadaPorCeic = true;
            return;
        }

        if (unidadAutoSeleccionadaPorCeic) {
            unidadCargo.value = "CARGO";
            unidadAutoSeleccionadaPorCeic = false;
        }
    }

    function obtenerCui(item) {
        return item.cui || item.CUI || item.cui_loc || "";
    }

    function campoHistoricoModificado(item, clave) {
        return Boolean(item && Array.isArray(item.campos_modificados) && item.campos_modificados.includes(clave));
    }

    function claseCampoHistoricoModificado(item, clave) {
        return campoHistoricoModificado(item, clave) ? " pof-history-modified" : "";
    }

    function renderizarDatoOferta(item, etiqueta, dato, claveHistorica = "") {
        if (dato === null || dato === undefined || dato === "") {
            return "";
        }

        return `
            <div class="pof-data-item pof-offer-detail-item${claseCampoHistoricoModificado(item, claveHistorica)}">
                <span>${escaparHtml(etiqueta)}</span>
                <strong>${escaparHtml(dato)}</strong>
                ${campoHistoricoModificado(item, claveHistorica) ? '<em class="pof-history-modified-tag">Modificado</em>' : ''}
            </div>
        `;
    }

    function obtenerCampoOferta(item, campos) {
        if (!item) {
            return "";
        }

        const claves = Object.keys(item);
        for (const campo of campos) {
            if (item[campo] !== null && item[campo] !== undefined && item[campo] !== "") {
                return item[campo];
            }

            const claveEncontrada = claves.find(clave => clave.toLowerCase() === campo.toLowerCase());
            if (claveEncontrada && item[claveEncontrada] !== null && item[claveEncontrada] !== undefined && item[claveEncontrada] !== "") {
                return item[claveEncontrada];
            }
        }

        return "";
    }

    function obtenerEstadoOferta(item) {
        const estado = obtenerCampoOferta(item, [
            "estado_oferta",
            "est_oferta",
            "estado",
            "estado_localizacion",
            "estado_loc",
        ]);
        return normalizarEstadoOferta(estado);
    }

    function obtenerOrigenOferta(item) {
        const origen = obtenerCampoOferta(item, ["origen_datos", "origen", "fuente", "source"]);
        const normalizado = normalizarTextoOferta(origen);

        if (!normalizado || normalizado.includes("padron")) {
            return "PADRÓN";
        }

        if (normalizado.includes("manual")) {
            return "MANUAL";
        }

        return String(origen).toUpperCase();
    }

    function obtenerOfertaReal(item) {
        if (item && Object.prototype.hasOwnProperty.call(item, "oferta_real")) {
            return item.oferta_real || "";
        }

        return obtenerCampoOferta(item, ["oferta"]);
    }

    function clonarDatoPlano(dato) {
        return JSON.parse(JSON.stringify(dato || {}));
    }

    function normalizarValorHistorico(valor) {
        return String(valor || "").trim();
    }

    function obtenerValorHistorico(item, config) {
        return normalizarValorHistorico(obtenerCampoOferta(item, config.campos));
    }

    function armarDatosUsadosPof(item) {
        return {
            establecimiento: obtenerValorHistorico(item, CAMPOS_HISTORICOS_EDITABLES[0]),
            localidad: obtenerValorHistorico(item, CAMPOS_HISTORICOS_EDITABLES[1]),
            departamento: obtenerValorHistorico(item, CAMPOS_HISTORICOS_EDITABLES[2]),
            categoria: obtenerValorHistorico(item, CAMPOS_HISTORICOS_EDITABLES[3]),
            jornada: obtenerValorHistorico(item, CAMPOS_HISTORICOS_EDITABLES[4]),
        };
    }

    function sincronizarEdicionHistorica(item) {
        if (!item) {
            return;
        }
        item.campos_modificados = [];
        item.origen_datos = "PADRON";
        item.datos_usados_pof = armarDatosUsadosPof(item);
    }

    function normalizarPadronSeleccionado(item) {
        const ofertaReal = obtenerOfertaReal(item);
        const padronBase = {
            ...item,
            oferta_real: ofertaReal,
            oferta: ofertaReal,
        };
        const original = clonarDatoPlano(padronBase);
        padronBase.datos_originales_padron = original;
        sincronizarEdicionHistorica(padronBase);
        return padronBase;
    }

    function claveOfertaPadron(item) {
        return [
            obtenerCampoOferta(item, ["id_oferta_local", "id"]),
            obtenerCampoOferta(item, ["id_localizacion"]),
            obtenerCampoOferta(item, ["cuof_loc", "cuof"]),
        ].map(valorClave => String(valorClave || "").trim()).join("|");
    }

    function ofertaPadronEstaSeleccionada(item) {
        const clave = claveOfertaPadron(item);
        return ofertasPadronSeleccionadas.some(oferta => claveOfertaPadron(oferta) === clave);
    }

    function construirPadronSeleccionadoMultiple() {
        if (ofertasPadronSeleccionadas.length === 0) {
            return null;
        }

        const ofertasNormalizadas = ofertasPadronSeleccionadas.map(normalizarPadronSeleccionado);
        const nombresOfertas = [];
        ofertasNormalizadas.forEach(oferta => {
            const nombre = obtenerOfertaReal(oferta);
            if (nombre && !nombresOfertas.includes(nombre)) {
                nombresOfertas.push(nombre);
            }
        });

        const ofertaPrincipal = ofertasNormalizadas[0];
        return normalizarPadronSeleccionado({
            ...ofertaPrincipal,
            oferta_real: nombresOfertas.join(", "),
            oferta: nombresOfertas.join(", "),
            ofertas_seleccionadas: ofertasNormalizadas.map(oferta => ({
                id_localizacion: oferta.id_localizacion,
                id_oferta_local: oferta.id_oferta_local,
                padron_cueanexo: oferta.padron_cueanexo,
                cueanexo: oferta.cueanexo,
                cuof_loc: oferta.cuof_loc,
                cuof: oferta.cuof,
            })),
        });
    }

    function obtenerLineaPrincipalOferta(item, icono = "📌") {
        const oferta = obtenerOfertaReal(item);
        const establecimiento = obtenerCampoOferta(item, ["nom_est", "establecimiento", "nombre_establecimiento"]);
        const partes = [];

        if (icono) {
            partes.push(icono);
        }

        partes.push(oferta || "Oferta sin identificar");

        if (establecimiento) {
            partes.push(`— ${establecimiento}`);
        }

        return partes.join(" ");
    }

    function obtenerLineaSecundariaOferta(item) {
        const cuof = obtenerCampoOferta(item, ["cuof_loc", "cuof"]);
        const categoria = obtenerCampoOferta(item, ["categoria", "categoria_loc"]);
        const jornada = obtenerCampoOferta(item, ["jornada", "jornada_loc"]);
        const partes = [
            cuof ? `CUOF: ${cuof}` : "",
            obtenerCampoOferta(item, ["localidad", "departamento", "ref_loc"]),
            categoria ? `Categoría: ${categoria}` : "",
            jornada ? `Jornada: ${jornada}` : "",
        ].filter(Boolean);

        return partes.join(" · ") || "Sin datos complementarios";
    }

    function obtenerTextoBusquedaOferta(item) {
        return normalizarTextoOferta([
            obtenerOfertaReal(item),
            obtenerCampoOferta(item, ["cuof_loc", "cuof"]),
            obtenerCampoOferta(item, ["localidad"]),
            obtenerCampoOferta(item, ["categoria", "categoria_loc"]),
            obtenerCampoOferta(item, ["jornada", "jornada_loc"]),
        ].join(" "));
    }

    function renderizarBadgeEstadoOferta(item) {
        const estado = obtenerEstadoOferta(item);
        return renderizarBadgeEstadoOfertaComun(estado);
    }

    function renderizarGrupoDetalleOferta(titulo, campos) {
        const items = campos
            .map(config => renderizarDatoOferta(config.item, config.etiqueta, config.valor, config.clave || ""))
            .join("");

        if (!items) {
            return "";
        }

        return `
            <section class="pof-offer-detail-section">
                <h3>${titulo}</h3>
                <div class="pof-offer-detail-section-grid">${items}</div>
            </section>
        `;
    }

    function renderizarDetalleOferta(item) {
        const detalle = [
            renderizarGrupoDetalleOferta("Identificación", [
                { item, etiqueta: "CUEANEXO", valor: obtenerCampoOferta(item, ["padron_cueanexo", "cueanexo", "cue_anexo"]) },
                { item, etiqueta: "CUE", valor: obtenerCampoOferta(item, ["cue"]) },
                { item, etiqueta: "Anexo", valor: obtenerCampoOferta(item, ["anexo"]) },
                { item, etiqueta: "CUOF", valor: obtenerCampoOferta(item, ["cuof_loc", "cuof"]) },
                { item, etiqueta: "CUI", valor: obtenerCui(item) },
            ]),
            renderizarGrupoDetalleOferta("Establecimiento", [
                { item, etiqueta: "Nombre", valor: obtenerCampoOferta(item, ["nom_est", "establecimiento", "nombre_establecimiento"]), clave: "establecimiento" },
                { item, etiqueta: "Número", valor: obtenerCampoOferta(item, ["nro_est", "numero_establecimiento"]) },
                { item, etiqueta: "Región", valor: obtenerCampoOferta(item, ["region_loc", "region", "regional_actual"]) },
                { item, etiqueta: "Localidad", valor: obtenerCampoOferta(item, ["localidad"]), clave: "localidad" },
                { item, etiqueta: "Departamento", valor: obtenerCampoOferta(item, ["departamento"]), clave: "departamento" },
                { item, etiqueta: "Zona", valor: obtenerCampoOferta(item, ["zona", "zona_loc", "zona_provincial"]) },
            ]),
            renderizarGrupoDetalleOferta("Oferta", [
                { item, etiqueta: "Oferta", valor: obtenerOfertaReal(item) },
                { item, etiqueta: "Acrónimo", valor: obtenerCampoOferta(item, ["acronimo"]) },
                { item, etiqueta: "Ámbito", valor: obtenerCampoOferta(item, ["ambito"]) },
                { item, etiqueta: "Categoría", valor: obtenerCampoOferta(item, ["categoria", "categoria_loc"]), clave: "categoria" },
                { item, etiqueta: "Jornada", valor: obtenerCampoOferta(item, ["jornada", "jornada_loc"]), clave: "jornada" },
                { item, etiqueta: "Ubicación", valor: obtenerCampoOferta(item, ["ubicacion", "ref_loc", "domicilio_ppal", "calle"]) },
            ]),
            renderizarGrupoDetalleOferta("Estados", [
                { item, etiqueta: "Localización", valor: obtenerCampoOferta(item, ["estado_loc", "estado_localizacion_padron", "estado_localizacion"]) },
                { item, etiqueta: "Oferta", valor: obtenerCampoOferta(item, ["est_oferta", "estado_oferta_padron", "estado_oferta", "oferta_estado"]) },
                { item, etiqueta: "Establecimiento", valor: obtenerCampoOferta(item, ["estado_est", "estado_establecimiento_padron", "estado_establecimiento"]) },
            ]),
        ].join("");

        if (obtenerEstadoOferta(item).codigo !== "BAJA") {
            return detalle;
        }

        const mensajeBaja = "Esta oferta figura como baja en el padrón actual. Verifique si corresponde usarla para la Reunida seleccionada.";

        return `
            ${detalle}
            <div class="pof-offer-warning">
                ${escaparHtml(mensajeBaja)}
            </div>
        `;
    }

    function limpiarFiltrosOfertas() {
        filtroOfertaTexto = "";
        filtroOfertaEstado = "TODOS";
        ofertaAbiertaIndex = null;
        mostrarOtrasOfertas = false;
    }

    function mostrarEstado(tipo, mensaje) {
        estadoBusqueda.className = "pof-status " + tipo;
        estadoBusqueda.textContent = mensaje;
    }

    function limpiarEstado() {
        estadoBusqueda.className = "pof-status";
        estadoBusqueda.textContent = "";
    }

    function mostrarEstadoCabecera(tipo, mensaje) {
        estadoCabecera.className = "pof-status " + tipo;
        estadoCabecera.textContent = mensaje;
    }

    function limpiarEstadoCabecera() {
        estadoCabecera.className = "pof-status";
        estadoCabecera.textContent = "";
    }

    function mostrarEstadoGuardado(tipo, mensaje) {
        estadoGuardado.className = "pof-status " + tipo;
        estadoGuardado.textContent = mensaje;
    }

    function limpiarEstadoGuardado() {
        estadoGuardado.className = "pof-status";
        estadoGuardado.textContent = "";
    }

    function formatearErroresBackend(errores) {
        if (!errores) {
            return "";
        }

        if (Array.isArray(errores)) {
            return errores.join(" ");
        }

        if (typeof errores === "object") {
            return Object.entries(errores).map(([campo, detalle]) => {
                return `${campo}: ${formatearErroresBackend(detalle)}`;
            }).join(" ");
        }

        return String(errores);
    }

    function actualizarEstadoBotonGuardar() {
        const puedeGuardar = cabeceraReunidaValidada && padronSeleccionado && cargosTemporales.length > 0;
        bloqueGuardarCarga.classList.toggle("pof-hidden", !puedeGuardar);
        btnGuardarCarga.disabled = !puedeGuardar || guardandoCarga;
    }

    function construirUrlDetalleGuardado(data) {
        const params = new URLSearchParams();

        const anio = (
            cabeceraReunida && cabeceraReunida.anio
        ) || anioValidadoInput.value || anioInput.value;

        const nivel = (
            cabeceraReunida && cabeceraReunida.nivel
        ) || nivelValidadoInput.value || nivelSelect.value;

        if (!anio || !nivel) {
            return "";
        }

        params.set("anio", anio);
        params.set("nivel", nivel);

        const cueanexoDetalle = obtenerCampoOferta(padronSeleccionado, ["padron_cueanexo", "cueanexo", "cue_anexo"]);
        const cuofDetalle = obtenerCampoOferta(padronSeleccionado, ["cuof_loc", "cuof"]);

        if (cueanexoDetalle && cuofDetalle) {
            params.set("cueanexo", cueanexoDetalle);
            params.set("cuof", cuofDetalle);
        }

        return `${URL_DETALLE_REUNIDA}?${params.toString()}`;
    }

    function mostrarExitoGuardado(data) {
        estadoGuardado.className = "pof-status ok";
        estadoGuardado.innerHTML = "";

        const mensaje = document.createElement("div");
        mensaje.textContent = data.mensaje || "Carga guardada correctamente.";

        const urlDetalle = construirUrlDetalleGuardado(data);

        estadoGuardado.appendChild(mensaje);

        if (urlDetalle) {
            const acciones = document.createElement("div");
            acciones.className = "pof-actions pof-mt-2 pof-post-save-actions";

            const linkDetalle = document.createElement("a");
            linkDetalle.className = "pof-btn pof-btn-light";
            linkDetalle.href = urlDetalle;
            linkDetalle.textContent = "Ver en detalle de la reunida";

            acciones.appendChild(linkDetalle);
            estadoGuardado.appendChild(acciones);
        }
    }

    function limpiarAnio(valor) {
        return String(valor || "").replace(/\D/g, "").slice(0, 4);
    }

    function aplicarEstadoBusquedaPadron(habilitado) {
        bloqueBusquedaPadron.classList.toggle("pof-hidden", !habilitado);
        cueBaseInput.disabled = !habilitado;
        anexoInput.disabled = !habilitado;
        cueanexoInput.disabled = !habilitado;
        btnBuscarPadron.disabled = !habilitado;
    }

    function limpiarDatosDependientes() {
        padronSeleccionado = null;
        ofertasPadronSeleccionadas = [];
        resultadosPadronActuales = [];
        limpiarFiltrosOfertas();
        cargosTemporales = [];
        reiniciarCatalogoCeic();
        cueBaseInput.value = "";
        anexoInput.value = "";
        cueanexoInput.value = "";
        bloquePadron.classList.add("pof-hidden");
        bloqueSeleccion.classList.add("pof-hidden");
        bloqueCargos.classList.add("pof-hidden");
        resultadosPadron.innerHTML = "";
        detalleSeleccion.innerHTML = "";
        limpiarCargoActual();
        renderizarTablaCargos();
        limpiarEstado();
        limpiarEstadoGuardado();
    }

    function marcarCabeceraEditable() {
        anioInput.disabled = !hayAniosReunidaDisponibles;
        nivelSelect.disabled = false;
        cabeceraReunidaCampos.classList.remove("pof-cabecera-locked");
        anioInput.classList.remove("pof-locked-control");
        nivelSelect.classList.remove("pof-locked-control");
        
        btnValidarReunida.disabled = false;
        btnValidarReunida.classList.remove("pof-hidden");
        btnCambiarReunida.classList.add("pof-hidden");
    }

    function limpiarCabeceraValidada() {
        cabeceraReunidaValidada = false;
        cabeceraReunida = null;
        cabeceraReunidaIdInput.value = "";
        anioValidadoInput.value = "";
        nivelValidadoInput.value = "";
        marcarCabeceraEditable();
        aplicarEstadoBusquedaPadron(false);
        actualizarEstadoBotonGuardar();
    }

    function bloquearCabeceraValidada(reunida) {
        cabeceraReunidaValidada = true;
        cabeceraReunida = reunida;
        cabeceraReunidaIdInput.value = reunida.id || "";
        anioValidadoInput.value = reunida.anio || "";
        nivelValidadoInput.value = reunida.nivel || "";
        anioInput.value = reunida.anio || anioInput.value;
        nivelSelect.value = reunida.nivel || nivelSelect.value;

        anioInput.disabled = true;
        nivelSelect.disabled = true;
        cabeceraReunidaCampos.classList.add("pof-cabecera-locked");
        anioInput.classList.add("pof-locked-control");
        nivelSelect.classList.add("pof-locked-control");
        btnValidarReunida.classList.add("pof-hidden");
        btnCambiarReunida.classList.remove("pof-hidden");
        aplicarEstadoBusquedaPadron(true);
    }

    async function validarCabeceraReunida() {
        const anio = anioInput.value.trim();
        const nivel = nivelSelect.value;

        limpiarCabeceraValidada();
        limpiarDatosDependientes();

        if (!anio) {
            mostrarEstadoCabecera("error", "Ingresá el año de la Reunida.");
            anioInput.focus();
            return;
        }

        if (anio.length !== 4) {
            mostrarEstadoCabecera("error", "El año debe tener 4 dígitos numéricos.");
            anioInput.focus();
            return;
        }

        if (!nivel) {
            mostrarEstadoCabecera("error", "Seleccioná un nivel.");
            nivelSelect.focus();
            return;
        }

        btnValidarReunida.disabled = true;
        mostrarEstadoCabecera("warn", "Validando Cabecera de Reunida...");

        const parametros = new URLSearchParams({ anio: anio, nivel: nivel });

        try {
            const response = await fetch(`${URL_VALIDAR_REUNIDA}?${parametros.toString()}`);
            const data = await response.json();

            if (!data.ok) {
                limpiarCabeceraValidada();
                mostrarEstadoCabecera(
                    "error",
                    data.mensaje || "No existe una Reunida POF para ese año y nivel."
                );
                return;
            }

            bloquearCabeceraValidada(data.reunida);
            mostrarEstadoCabecera("ok", data.mensaje || "Cabecera de Reunida validada.");
        } catch (error) {
            limpiarCabeceraValidada();
            mostrarEstadoCabecera("error", "No se pudo validar la Cabecera de Reunida.");
        }
    }

    function cambiarCabeceraReunida() {
        const hayDatosDependientes = Boolean(
            padronSeleccionado || resultadosPadronActuales.length || cargosTemporales.length
        );

        if (hayDatosDependientes) {
            const confirmar = confirm(
                "Cambiar la cabecera limpiará el padrón seleccionado y los cargos. ¿Continuar?"
            );
            if (!confirmar) {
                return;
            }
        }

        limpiarCabeceraValidada();
        limpiarDatosDependientes();
        limpiarEstadoCabecera();
        anioInput.focus();
    }

    function limpiarDependientesPorCambioCabecera() {
        if (cabeceraReunidaValidada) {
            return;
        }

        limpiarDatosDependientes();
        aplicarEstadoBusquedaPadron(false);
    }

    function actualizarCueanexo() {
        const resultado = construirCueanexoDesdePartes(
            cueBaseInput.value,
            anexoInput.value
        );

        cueBaseInput.value = resultado.cue;
        anexoInput.value = resultado.anexo;
        cueanexoInput.value = resultado.cueanexo;
    }

    // --- Listeners de Eventos ---
    cueBaseInput.addEventListener("input", actualizarCueanexo);
    anexoInput.addEventListener("input", actualizarCueanexo);

    anioInput.addEventListener("input", function () {
        this.value = limpiarAnio(this.value);
        limpiarDependientesPorCambioCabecera();
        limpiarEstadoCabecera();
    });
    anioInput.addEventListener("paste", function (event) {
        event.preventDefault();
        const texto = event.clipboardData ? event.clipboardData.getData("text") : "";
        this.value = limpiarAnio(this.value + texto);
        limpiarDependientesPorCambioCabecera();
        limpiarEstadoCabecera();
    });
    anioInput.addEventListener("change", function () {
        limpiarDependientesPorCambioCabecera();
        limpiarEstadoCabecera();
    });
    nivelSelect.addEventListener("change", function () {
        limpiarDependientesPorCambioCabecera();
        limpiarEstadoCabecera();
    });

    btnValidarReunida.addEventListener("click", validarCabeceraReunida);
    btnCambiarReunida.addEventListener("click", cambiarCabeceraReunida);
    btnBuscarPadron.addEventListener("click", buscarPadron);
    btnGuardarCarga.addEventListener("click", abrirConfirmacionCarga);
    btnConfirmarGuardarCarga.addEventListener("click", guardarCarga);

    ceicBusqueda.addEventListener("input", buscarCeicDinamico);
    modoCeicRadios.forEach(radio => {
        radio.addEventListener("change", function () {
            if (!this.checked) {
                return;
            }
            cambiarModoCeic(this.value === "otros", { relanzarBusqueda: true });
        });
    });
    cantidadCargo.addEventListener("input", calcularCargoActual);
    unidadCargo.addEventListener("change", function () {
        unidadAutoSeleccionadaPorCeic = false;
    });
    btnAgregarCargoLista.addEventListener("click", agregarCargoALista);
    btnMostrarObservacion.addEventListener("click", () => controlObservacionCargo.mostrar());
    btnQuitarObservacion.addEventListener("click", () => controlObservacionCargo.ocultar(true));
    tablaCargos.addEventListener("change", function (event) {
        const inputCantidad = event.target.closest("[data-cargo-quantity-index]");
        if (!inputCantidad) {
            return;
        }

        const index = Number(inputCantidad.dataset.cargoQuantityIndex);
        if (actualizarCantidadCargoTemporal(index, inputCantidad.value)) {
            return;
        }

        alert("La cantidad debe ser un numero entero mayor a 0.");
        renderizarTablaCargos();
    });
    tablaCargos.addEventListener("click", function (event) {
        const botonQuitar = event.target.closest("[data-cargo-remove-index]");
        if (!botonQuitar) {
            return;
        }

        const index = Number(botonQuitar.dataset.cargoRemoveIndex);
        quitarCargoTemporal(index);
    });
    document.querySelectorAll("[data-cancelar-confirmacion-carga]").forEach(boton => {
        boton.addEventListener("click", cerrarConfirmacionCarga);
    });
    modalConfirmarCarga.addEventListener("click", function (event) {
        if (event.target === modalConfirmarCarga && !guardandoCarga) {
            cerrarConfirmacionCarga();
        }
    });

    async function buscarPadron() {
        if (!cabeceraReunidaValidada) {
            mostrarEstado("error", "Primero validá la cabecera de carga.");
            return;
        }

        const anioValidado = anioValidadoInput.value || (cabeceraReunida ? cabeceraReunida.anio : "");
        const nivelValidado = nivelValidadoInput.value || (cabeceraReunida ? cabeceraReunida.nivel : "") || nivelSelect.value;

        if (!anioValidado || !nivelValidado) {
            mostrarEstado("error", "Primero validá una Cabecera de Reunida con año y nivel.");
            return;
        }

        actualizarCueanexo();

        const cueBase = cueBaseInput.value.trim();
        const anexo = anexoInput.value.trim();
        const cueanexo = cueanexoInput.value.trim();

        padronSeleccionado = null;
        ofertasPadronSeleccionadas = [];
        resultadosPadronActuales = [];
        limpiarFiltrosOfertas();
        cargosTemporales = [];

        bloquePadron.classList.add("pof-hidden");
        bloqueSeleccion.classList.add("pof-hidden");
        bloqueCargos.classList.add("pof-hidden");

        resultadosPadron.innerHTML = "";
        detalleSeleccion.innerHTML = "";
        renderizarTablaCargos();
        limpiarEstadoGuardado();

        if (!cueBase) {
            mostrarEstado("error", "Ingresá el CUE base.");
            return;
        }

        if (cueBase.length !== 7) {
            mostrarEstado("error", "El CUE base debe tener 7 dígitos.");
            return;
        }

        if (anexo && anexo.length !== 2) {
            mostrarEstado("error", "El anexo debe tener 2 dígitos. Ejemplo: 00, 01, 02.");
            return;
        }

        mostrarEstado("warn", "Buscando localización en padrón...");

        const parametros = new URLSearchParams();

        if (cueanexo) {
            parametros.append("cueanexo", cueanexo);
        } else {
            parametros.append("cue", cueBase);
        }
        parametros.append("cabecera_tipo", "REUNIDA");
        parametros.append("anio", anioValidado);
        parametros.append("nivel", nivelValidado);

        try {
            const response = await fetch(`${URL_BUSCAR_PADRON}?${parametros.toString()}`);
            const data = await response.json();

            if (!data.ok) {
                mostrarEstado("error", data.mensaje || "No se encontraron datos en padrón.");
                return;
            }

            const textoBusqueda = cueanexo ? `CUEANEXO ${cueanexo}` : `CUE ${cueBase}`;
            const cantidadResultados = renderizarResultadosPadron(data.resultados);

            if (cantidadResultados > 0) {
                mostrarEstado("ok", `Se encontraron ${cantidadResultados} oferta(s) para ${textoBusqueda}.`);
            }

        } catch (error) {
            mostrarEstado("error", "No se pudo realizar la búsqueda en padrón.");
        }
    }

    /**
     * Indica si la fila de padrón quedó sugerida por el backend para la cabecera activa.
     *
     * - Respeta la marca centralizada `oferta_sugerida` cuando viene informada.
     * - Mantiene como sugeridas las filas sin marca para conservar el contrato del padrón.
     * - Evita duplicar reglas de nivel/oferta en el template.
     */
    function ofertaEsSugerida(item) {
        if (!item || !Object.prototype.hasOwnProperty.call(item, "oferta_sugerida")) {
            return true;
        }
        return item.oferta_sugerida === true;
    }

    /**
     * Detecta si la respuesta del padrón trae clasificación sugerida/otras ofertas.
     *
     * - Activa la separación solo cuando el backend envía la marca `oferta_sugerida`.
     * - Evita modificar la visualización cuando el backend no envía clasificación.
     * - No infiere compatibilidad en frontend.
     */
    function usaSeparacionOfertas(resultados) {
        return resultados.some(item => item && Object.prototype.hasOwnProperty.call(item, "oferta_sugerida"));
    }

    /**
     * Aplica los filtros visuales actuales a las ofertas del padrón.
     *
     * - Conserva el índice global para que apertura y selección sigan apuntando al resultado original.
     * - Filtra por texto libre y estado sin alterar la lista base recibida.
     * - Reutiliza los helpers existentes de normalización y estado de oferta.
     */
    function filtrarOfertasVisibles(resultados) {
        const filtroTextoNormalizado = normalizarTextoOferta(filtroOfertaTexto);
        return resultados
            .map((item, index) => ({ item, index }))
            .filter(({ item }) => {
                const coincideTexto = !filtroTextoNormalizado || obtenerTextoBusquedaOferta(item).includes(filtroTextoNormalizado);
                const estado = obtenerEstadoOferta(item);
                const coincideEstado = filtroOfertaEstado === "TODOS" || estado.codigo === filtroOfertaEstado;
                return coincideTexto && coincideEstado;
            });
    }

    /**
     * Renderiza las tarjetas de oferta reutilizando exactamente el diseño actual.
     *
     * - Recibe pares `{ item, index }` ya filtrados o clasificados.
     * - Mantiene el mismo flujo de apertura y selección por índice global.
     * - Devuelve el estado vacío indicado cuando el grupo no tiene resultados visibles.
     */
    function renderizarListaTarjetasOferta(ofertasVisibles, mensajeVacio) {
        if (ofertasVisibles.length === 0) {
            return `
                <div class="pof-empty-error">
                    ${escaparHtml(mensajeVacio)}
                </div>
            `;
        }

        return `
            <div class="pof-offer-list">
                ${ofertasVisibles.map(({ item, index }) => {
                    const abierta = ofertaAbiertaIndex === index;
                    const seleccionada = ofertaPadronEstaSeleccionada(item);

                    return `
                        <div class="pof-offer-card${abierta ? " pof-offer-card-open" : ""}${seleccionada ? " pof-offer-selected" : ""}" data-oferta-index="${index}">
                            <button type="button"
                                    class="pof-offer-card-header"
                                    aria-expanded="${abierta ? "true" : "false"}"
                                    onclick="alternarOfertaPadron(${index})">
                                <span class="pof-offer-card-heading">
                                    <span class="pof-offer-card-main">
                                        <span class="pof-offer-card-title">${escaparHtml(obtenerLineaPrincipalOferta(item))}</span>
                                        ${renderizarBadgeEstadoOferta(item)}
                                    </span>
                                    <span class="pof-offer-card-meta">${escaparHtml(obtenerLineaSecundariaOferta(item))}</span>
                                </span>
                                <span class="pof-offer-card-toggle" aria-hidden="true">${abierta ? "🔽" : "▶️"}</span>
                            </button>

                            <div class="pof-offer-card-body${abierta ? "" : " pof-hidden"}">
                                <div class="pof-offer-detail-compact pof-offer-detail-grid">
                                    ${renderizarDetalleOferta(item)}
                                </div>

                                <div class="pof-mt-2">
                                    <button type="button" class="pof-btn ${seleccionada ? "pof-btn-light" : "pof-btn-primary"}" onclick="seleccionarPadron(${index})">
                                        ${seleccionada ? "Quitar selección" : "Seleccionar oferta"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    /**
     * Renderiza los resultados de padrón separando sugeridas y otras ofertas cuando aplica.
     *
     * - Muestra primero las ofertas sugeridas para el nivel validado de la Reunida.
     * - Mantiene ocultas las otras ofertas hasta que el usuario las despliega.
     * - Reutiliza las mismas tarjetas y filtros existentes para ambos grupos.
     */
    function renderizarResultadosPadron(resultados, conservarApertura = false, mantenerFocoFiltro = false) {
        bloquePadron.classList.remove("pof-hidden");
        const resultadosRecibidos = Array.isArray(resultados) ? resultados : [];
        resultadosPadronActuales = resultadosRecibidos;

        if (!conservarApertura) {
            ofertaAbiertaIndex = null;
        }

        if (resultadosPadronActuales.length === 0) {
            resultadosPadron.innerHTML = `
                <div class="pof-status warn">
                    No se encontraron ofertas para la búsqueda ingresada.
                </div>
            `;
            return 0;
        }

        const separarOfertas = usaSeparacionOfertas(resultadosPadronActuales);
        const ofertasVisibles = filtrarOfertasVisibles(resultadosPadronActuales);
        const ofertasSugeridas = separarOfertas
            ? ofertasVisibles.filter(({ item }) => ofertaEsSugerida(item))
            : ofertasVisibles;
        const otrasOfertas = separarOfertas
            ? ofertasVisibles.filter(({ item }) => !ofertaEsSugerida(item))
            : [];
        const totalSugeridas = separarOfertas
            ? resultadosPadronActuales.filter(item => ofertaEsSugerida(item)).length
            : resultadosPadronActuales.length;
        const totalOtras = separarOfertas
            ? resultadosPadronActuales.length - totalSugeridas
            : 0;
        const mensajeSinSugeridas = separarOfertas && totalSugeridas === 0
            ? "No hay ofertas sugeridas para el nivel de la Reunida. Podés revisar Otras ofertas del mismo CUEANEXO."
            : "No hay ofertas sugeridas que coincidan con el filtro aplicado.";

        resultadosPadron.innerHTML = `
            <div class="pof-offer-results-shell pof-aura-card">
                <div class="pof-offer-results-head">
                    <div>
                        <strong>Se encontraron ${resultadosPadronActuales.length} ofertas para esta búsqueda.</strong>
                        <span class="pof-offer-results-count">Mostrando ${ofertasVisibles.length} de ${resultadosPadronActuales.length} ofertas.</span>
                    </div>
                </div>

                <div class="pof-actions pof-mt-2">
                    <button type="button" class="pof-btn pof-btn-primary" onclick="confirmarOfertasPadron()"${ofertasPadronSeleccionadas.length ? "" : " disabled"}>
                        Continuar con ${ofertasPadronSeleccionadas.length} oferta(s)
                    </button>
                </div>

                <div class="pof-offer-filter-bar">
                    <input type="search"
                           id="filtroOfertaTexto"
                           class="pof-form-control pof-offer-filter-search"
                           placeholder="Filtrar por oferta real, CUOF, categoría, jornada o localidad"
                           value="${escaparHtml(filtroOfertaTexto)}"
                           autocomplete="off">
                    <select id="filtroOfertaEstado" class="pof-form-select pof-offer-filter-status">
                        <option value="TODOS"${filtroOfertaEstado === "TODOS" ? " selected" : ""}>Todos</option>
                        <option value="ACTIVA"${filtroOfertaEstado === "ACTIVA" ? " selected" : ""}>Activa</option>
                        <option value="BAJA"${filtroOfertaEstado === "BAJA" ? " selected" : ""}>Baja</option>
                        <option value="SIN_DATO"${filtroOfertaEstado === "SIN_DATO" ? " selected" : ""}>Sin dato</option>
                    </select>
                </div>

                <div class="pof-offer-list-scroll">
                    ${separarOfertas ? `
                        <div class="pof-mb-2">
                            <strong>Ofertas sugeridas</strong>
                        </div>
                        ${renderizarListaTarjetasOferta(ofertasSugeridas, mensajeSinSugeridas)}
                        ${totalOtras > 0 ? `
                            <div class="pof-actions pof-mt-2">
                                <button type="button" class="pof-btn pof-btn-light" onclick="alternarOtrasOfertas()">
                                    Otras ofertas
                                </button>
                            </div>
                            <div class="${mostrarOtrasOfertas ? "" : "pof-hidden"}">
                                ${renderizarListaTarjetasOferta(otrasOfertas, "No hay otras ofertas que coincidan con el filtro aplicado.")}
                            </div>
                        ` : `
                            <div class="pof-status warn pof-mt-2">
                                No hay otras ofertas para este CUEANEXO.
                            </div>
                        `}
                    ` : `
                        ${renderizarListaTarjetasOferta(ofertasVisibles, "No hay ofertas que coincidan con el filtro aplicado.")}
                    `}
                </div>
            </div>
        `;

        vincularFiltrosOfertas(mantenerFocoFiltro);
        return resultadosPadronActuales.length;
    }

    function vincularFiltrosOfertas(mantenerFocoFiltro = false) {
        const filtroTextoInput = document.getElementById("filtroOfertaTexto");
        const filtroEstadoSelect = document.getElementById("filtroOfertaEstado");

        if (filtroTextoInput) {
            filtroTextoInput.addEventListener("input", () => {
                filtroOfertaTexto = filtroTextoInput.value;
                ofertaAbiertaIndex = null;
                renderizarResultadosPadron(resultadosPadronActuales, true, true);
            });

            if (mantenerFocoFiltro) {
                filtroTextoInput.focus();
                filtroTextoInput.setSelectionRange(filtroTextoInput.value.length, filtroTextoInput.value.length);
            }
        }

        if (filtroEstadoSelect) {
            filtroEstadoSelect.addEventListener("change", () => {
                filtroOfertaEstado = filtroEstadoSelect.value;
                ofertaAbiertaIndex = null;
                renderizarResultadosPadron(resultadosPadronActuales, true);
            });
        }
    }

    function alternarOfertaPadron(index) {
        ofertaAbiertaIndex = ofertaAbiertaIndex === index ? null : index;
        renderizarResultadosPadron(resultadosPadronActuales, true);

        if (ofertaAbiertaIndex !== null) {
            requestAnimationFrame(() => {
                const detalleAbierto = resultadosPadron.querySelector(`[data-oferta-index="${index}"] .pof-offer-card-body`);
                if (detalleAbierto) {
                    detalleAbierto.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
            });
        }
    }

    /**
     * Alterna la visibilidad del grupo de otras ofertas reales del mismo CUEANEXO.
     *
     * - No cambia la lista base ni vuelve a consultar el padrón.
     * - Cierra cualquier tarjeta abierta para evitar estados visuales inconsistentes.
     * - Mantiene el mismo flujo de selección que las ofertas sugeridas.
     */
    function alternarOtrasOfertas() {
        mostrarOtrasOfertas = !mostrarOtrasOfertas;
        ofertaAbiertaIndex = null;
        renderizarResultadosPadron(resultadosPadronActuales, true);
    }

    function renderizarOfertaSeleccionada() {
        if (!padronSeleccionado) {
            detalleSeleccion.innerHTML = "";
            return;
        }
        const cantidadOfertas = Array.isArray(padronSeleccionado.ofertas_seleccionadas)
            ? padronSeleccionado.ofertas_seleccionadas.length
            : 1;
        const seleccionMultiple = cantidadOfertas > 1;
        const estadoSeleccionado = obtenerEstadoOferta(padronSeleccionado);
        const detalleSugerencia = ofertaEsSugerida(padronSeleccionado)
            ? ""
            : " · Oferta fuera de sugerencia";
        detalleSeleccion.innerHTML = `
            <div class="pof-offer-selected-card">
                <div class="pof-offer-selected-head">
                    <span class="pof-offer-selected-title">✅ ${cantidadOfertas} oferta(s) seleccionada(s)</span>
                </div>
                <div class="pof-offer-card-main">
                    <span class="pof-offer-selected-main${claseCampoHistoricoModificado(padronSeleccionado, "establecimiento")}">${escaparHtml(obtenerLineaPrincipalOferta(padronSeleccionado, ""))}</span>
                    ${seleccionMultiple ? "" : renderizarBadgeEstadoOferta(padronSeleccionado)}
                </div>
                <div class="pof-offer-selected-meta">${escaparHtml(obtenerLineaSecundariaOferta(padronSeleccionado))}</div>
                <div class="pof-offer-selected-origin">
                    ${seleccionMultiple ? `Selección múltiple de ${cantidadOfertas} ofertas` : `Estado: ${escaparHtml(estadoSeleccionado.texto)}`} · Origen: ${escaparHtml(obtenerOrigenOferta(padronSeleccionado))}${seleccionMultiple ? "" : detalleSugerencia}
                </div>
                ${seleccionMultiple ? "" : `
                    <div class="pof-offer-detail-compact pof-offer-detail-grid pof-mt-2">
                        ${renderizarDetalleOferta(padronSeleccionado)}
                    </div>
                `}
            </div>

            <div class="pof-actions pof-mt-2 pof-offer-selected-actions">
                <button type="button" class="pof-btn pof-btn-light" onclick="cambiarOfertaSeleccionada()">
                    Cambiar oferta
                </button>
            </div>
        `;
    }

    function seleccionarPadron(index) {
        const oferta = resultadosPadronActuales[index];
        if (!oferta) {
            mostrarEstado("error", "La oferta seleccionada no está disponible.");
            return;
        }

        const clave = claveOfertaPadron(oferta);
        const indiceSeleccionado = ofertasPadronSeleccionadas.findIndex(item => claveOfertaPadron(item) === clave);
        if (indiceSeleccionado >= 0) {
            ofertasPadronSeleccionadas.splice(indiceSeleccionado, 1);
        } else {
            const cueanexoOferta = obtenerCampoOferta(oferta, ["padron_cueanexo", "cueanexo"]);
            const cueanexoInicial = obtenerCampoOferta(ofertasPadronSeleccionadas[0], ["padron_cueanexo", "cueanexo"]);
            if (cueanexoInicial && cueanexoOferta !== cueanexoInicial) {
                mostrarEstado("error", "Las ofertas seleccionadas deben pertenecer al mismo CUEANEXO.");
                return;
            }
            ofertasPadronSeleccionadas.push(oferta);
        }
        ofertaAbiertaIndex = null;
        renderizarResultadosPadron(resultadosPadronActuales, true);
        mostrarEstado(
            ofertasPadronSeleccionadas.length ? "ok" : "warn",
            ofertasPadronSeleccionadas.length
                ? `${ofertasPadronSeleccionadas.length} oferta(s) seleccionada(s). Confirmá para continuar.`
                : "Seleccioná al menos una oferta.",
        );
    }

    function confirmarOfertasPadron() {
        padronSeleccionado = construirPadronSeleccionadoMultiple();
        if (!padronSeleccionado) {
            mostrarEstado("error", "Seleccioná al menos una oferta del padrón.");
            return;
        }

        bloquePadron.classList.add("pof-hidden");
        bloqueSeleccion.classList.remove("pof-hidden");
        bloqueCargos.classList.remove("pof-hidden");

        cargosTemporales = [];
        limpiarCargoActual();
        renderizarTablaCargos();
        limpiarEstadoGuardado();
        renderizarOfertaSeleccionada();

        mostrarEstado("ok", `${ofertasPadronSeleccionadas.length} oferta(s) confirmada(s): ${valor(padronSeleccionado.oferta)}.`);
    }

    function cambiarOfertaSeleccionada() {
        if (!padronSeleccionado) {
            return;
        }

        padronSeleccionado = null;
        cargosTemporales = [];
        bloqueSeleccion.classList.add("pof-hidden");
        bloqueCargos.classList.add("pof-hidden");
        detalleSeleccion.innerHTML = "";
        limpiarCargoActual();
        renderizarTablaCargos();
        limpiarEstadoGuardado();
        limpiarFiltrosOfertas();

        if (resultadosPadronActuales.length > 0) {
            renderizarResultadosPadron(resultadosPadronActuales);
            mostrarEstado("warn", "Modificá la selección de ofertas y volvé a confirmarla.");
        }
    }

    /**
     * Restablece el formulario de un cargo sin alterar la Reunida ni la lista temporal.
     *
     * - Invalida búsquedas CEIC y restituye los campos calculados a su estado inicial.
     * - Cierra la observación mediante el control compartido de ambos flujos.
     * - Conserva los modos y reglas de CEIC específicos de Reunida.
     */
    function limpiarCargoActual() {
        clearTimeout(temporizadorCeic);
        ultimoTextoCeic = "";
        secuenciaBusquedaCeic += 1;
        ceicBusqueda.value = "";
        ceicSeleccionado.value = "";
        ceicSeleccionadoFueraSugerencia = false;
        cargoSeleccionado.value = "";
        cantidadCargo.value = "1";
        unidadCargo.value = "CARGO";
        puntosCargo.value = "";
        totalCargo.value = "0";
        observacionCargo.value = "";
        controlObservacionCargo.ocultar();
        sugerenciasCeic.innerHTML = "";
        sugerenciasCeic.classList.add("pof-hidden");
        cambiarModoCeic(false);
    }

    function limpiarCargaTemporalPostGuardado() {
        cargosTemporales = [];
        limpiarCargoActual();
        renderizarTablaCargos();
        actualizarEstadoBotonGuardar();
    }

    async function cargarCatalogoCeic() {
        const nivelCeicActivo = obtenerNivelCeicActivo();

        if (!nivelCeicActivo) {
            catalogoCeic = [];
            catalogoCeicNivelCargado = "";
            catalogoCeicCargado = false;
            return;
        }

        if (catalogoCeicCargado && catalogoCeicNivelCargado === nivelCeicActivo) {
            return;
        }

        if (catalogoCeicPromise) {
            await catalogoCeicPromise;
            return;
        }

        catalogoCeicCargando = true;
        catalogoCeicNivelCargado = nivelCeicActivo;
        const nivelSolicitud = nivelCeicActivo;

        catalogoCeicPromise = (async function () {
            try {
                const parametros = new URLSearchParams({ nivel: nivelCeicActivo });
                const response = await fetch(`${URL_CATALOGO_CEIC}?${parametros.toString()}`, {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });

                const data = await response.json();
                const payload = data.data || data;

                if (catalogoCeicNivelCargado !== nivelSolicitud) {
                    return;
                }

                if (!response.ok || !data.ok) {
                    catalogoCeic = [];
                    catalogoCeicCargado = false;
                    return;
                }

                catalogoCeic = Array.isArray(payload.resultados)
                    ? payload.resultados
                    : [];

                catalogoCeicCargado = true;
            } catch (error) {
                if (catalogoCeicNivelCargado !== nivelSolicitud) {
                    return;
                }
                catalogoCeic = [];
                catalogoCeicCargado = false;
            } finally {
                catalogoCeicCargando = false;
                catalogoCeicPromise = null;
            }
        })();

        await catalogoCeicPromise;
    }

    function filtrarCatalogoCeic(query) {
        return catalogoCeic
            .filter(item => String(item.ceic || "").startsWith(query))
            .slice(0, LIMITE_RESULTADOS_CEIC);
    }

    function renderizarSugerenciasCeic(resultados) {
        if (!resultados.length) {
            sugerenciasCeic.classList.add("pof-hidden");
            sugerenciasCeic.innerHTML = "";
            mostrarMensajeCeic("No se encontró un CEIC activo.");
            return;
        }

        sugerenciasCeic.innerHTML = resultados.map(item => {
            const descripcion = item.cargo || item.descripcion_ceic || "";
            const puntos = item.puntos || "0";
            const nivel = item.nivel || "";
            const esSugerido = item.es_sugerido !== false;
            const textoNivel = nivel ? `<span>${escaparHtml(nivel)}</span>` : "";

            return `
                <div class="pof-suggestion"
                     data-ceic="${escaparHtml(item.ceic)}"
                     data-cargo="${escaparHtml(descripcion)}"
                     data-puntos="${escaparHtml(puntos)}"
                     data-nivel="${escaparHtml(nivel)}"
                     data-es-sugerido="${esSugerido ? "true" : "false"}">
                    <strong>${escaparHtml(item.ceic)}</strong> - ${escaparHtml(descripcion)}
                    ${textoNivel}
                </div>
            `;
        }).join("");

        sugerenciasCeic.classList.remove("pof-hidden");

        sugerenciasCeic.querySelectorAll(".pof-suggestion").forEach(opcion => {
            opcion.addEventListener("click", function () {
                seleccionarCeic(this);
            });
        });
    }

    function buscarCeicDinamico() {
        const entrada = normalizarEntradaCeic(ceicBusqueda.value);
        if (ceicBusqueda.value !== entrada.valor) {
            ceicBusqueda.value = entrada.valor;
        }
        const query = entrada.valor;
        const nivelCeicActivo = obtenerNivelCeicActivo();

        if (query === ultimoTextoCeic) {
            if (entrada.corregido) {
                limpiarSeleccionCeicActual();
                mostrarMensajeCeic("Ingresá solo números, hasta 3 dígitos.");
            }
            return;
        }

        ultimoTextoCeic = query;
        ceicSeleccionado.value = "";
        cargoSeleccionado.value = "";
        puntosCargo.value = "";
        totalCargo.value = "0";
        clearTimeout(temporizadorCeic);
        secuenciaBusquedaCeic += 1;
        const secuenciaActual = secuenciaBusquedaCeic;

        if (!query) {
            mostrarCargaCeic(false);
            sugerenciasCeic.classList.add("pof-hidden");
            sugerenciasCeic.innerHTML = "";
            mostrarMensajeCeic(
                entrada.corregido
                    ? "Ingresá solo números, hasta 3 dígitos."
                    : mensajeModoCeicActual()
            );
            return;
        }

        if (!nivelCeicActivo) {
            sugerenciasCeic.classList.add("pof-hidden");
            sugerenciasCeic.innerHTML = "";
            mostrarMensajeCeic("Debe indicar un nivel de Reunida válido para buscar CEIC.");
            return;
        }

        mostrarCargaCeic(true);

        if (entrada.corregido) {
            mostrarMensajeCeic("Ingresá solo números, hasta 3 dígitos.");
        }

        temporizadorCeic = setTimeout(async function () {
            try {
                if (modoCeicOtros) {
                    try {
                        const parametros = new URLSearchParams({
                            nivel: nivelCeicActivo,
                            q: query,
                            modo: "otros",
                        });

                        const response = await fetch(`${URL_BUSCAR_CEIC}?${parametros.toString()}`, {
                            headers: {
                                "X-Requested-With": "XMLHttpRequest",
                            },
                        });

                        const data = await response.json();
                        const payload = data.data || data;

                        if (secuenciaActual !== secuenciaBusquedaCeic) {
                            return;
                        }

                        if (!response.ok || !data.ok) {
                            sugerenciasCeic.classList.add("pof-hidden");
                            sugerenciasCeic.innerHTML = "";
                            mostrarMensajeCeic(data.mensaje || "Ingresá solo números, hasta 3 dígitos.");
                            return;
                        }

                        renderizarSugerenciasCeic(
                            Array.isArray(payload.resultados)
                                ? payload.resultados
                                : []
                        );

                        return;
                    } catch (error) {
                        if (secuenciaActual !== secuenciaBusquedaCeic) {
                            return;
                        }

                        sugerenciasCeic.classList.add("pof-hidden");
                        sugerenciasCeic.innerHTML = "";
                        mostrarMensajeCeic("No se encontró un CEIC activo.");
                        return;
                    }
                }

                await cargarCatalogoCeic();

                if (secuenciaActual !== secuenciaBusquedaCeic) {
                    return;
                }

                const resultados = filtrarCatalogoCeic(query);
                renderizarSugerenciasCeic(resultados);

            } finally {
                if (secuenciaActual === secuenciaBusquedaCeic) {
                    mostrarCargaCeic(false);
                }
            }
        }, 120);
    }

    function seleccionarCeic(opcion) {
        const ceic = opcion.dataset.ceic;
        const cargo = opcion.dataset.cargo;
        const puntos = opcion.dataset.puntos;
        const esSugerido = opcion.dataset.esSugerido !== "false";
        ceicBusqueda.value = ceic;
        clearTimeout(temporizadorCeic);
        ultimoTextoCeic = ceicBusqueda.value.trim();
        secuenciaBusquedaCeic += 1;
        ceicSeleccionado.value = ceic;
        ceicSeleccionadoFueraSugerencia = !esSugerido;
        cargoSeleccionado.value = cargo;
        puntosCargo.value = puntos;
        aplicarUnidadPorCargoSeleccionado(cargo);

        sugerenciasCeic.classList.add("pof-hidden");
        sugerenciasCeic.innerHTML = "";
        mostrarMensajeCeic(
            esSugerido
                ? "CEIC sugerido para este nivel."
                : "Fuera de sugerencia. Revisá antes de guardar."
        );
        calcularCargoActual();
    }

    function calcularCargoActual() {
        const cantidad = parseFloat(cantidadCargo.value || "0");
        const puntos = parseFloat(puntosCargo.value || "0");

        totalCargo.value = (cantidad * puntos).toFixed(2);
    }

    function agregarCargoALista() {
        if (!cabeceraReunidaValidada) {
            mostrarEstado("error", "Primero validá la cabecera de carga.");
            return;
        }

        if (!padronSeleccionado) {
            mostrarEstado("error", "Primero seleccioná una oferta del padrón.");
            return;
        }

        calcularCargoActual();

        if (!ceicSeleccionado.value) {
            mostrarMensajeCeic("Ingresá solo números, hasta 3 dígitos.");
            return;
        }

        const nombreCargo = cargoSeleccionado.value.trim();
        if (!nombreCargo) {
            alert("El nombre del cargo es obligatorio.");
            return;
        }

        const cantidad = Number(cantidadCargo.value || "0");

        if (!Number.isInteger(cantidad) || cantidad <= 0) {
            alert("La cantidad debe ser un número entero mayor a 0.");
            return;
        }

        const puntos = Number(puntosCargo.value || "");
        if (!puntosCargo.value.trim() || !Number.isFinite(puntos) || puntos < 0) {
            alert("Los puntos asignados son obligatorios y deben ser un numero mayor o igual a 0.");
            return;
        }

        const cargoNuevo = {
            ceic: ceicSeleccionado.value,
            cargo: nombreCargo,
            observacion: observacionCargo.value.trim(),
            cantidad: String(cantidad),
            unidad_cantidad: unidadCargo.value,
            unidad_texto: unidadCargo.selectedOptions[0].textContent,
            puntos_asignados: puntosCargo.value,
            total: "0.00",
            ceic_fuera_sugerencia: ceicSeleccionadoFueraSugerencia,
        };
        actualizarTotalCargoTemporal(cargoNuevo);

        cargosTemporales.push(cargoNuevo);

        renderizarTablaCargos();
        limpiarCargoActual();
        limpiarEstadoGuardado();
    }

    function quitarCargoTemporal(index) {
        if (!Number.isInteger(index) || index < 0 || index >= cargosTemporales.length) {
            return;
        }

        cargosTemporales.splice(index, 1);
        renderizarTablaCargos();
        limpiarEstadoGuardado();
    }

    function actualizarCantidadCargoTemporal(index, valorCantidad) {
        if (!Number.isInteger(index) || index < 0 || index >= cargosTemporales.length) {
            return false;
        }

        const cantidad = Number(valorCantidad);
        if (!Number.isInteger(cantidad) || cantidad <= 0) {
            return false;
        }

        const cargo = cargosTemporales[index];
        cargo.cantidad = String(cantidad);
        actualizarTotalCargoTemporal(cargo);
        renderizarTablaCargos();
        limpiarEstadoGuardado();
        return true;
    }

    function renderizarInfoGeneralCargos() {
        const cabeceraValor = valor(cabeceraReunida && cabeceraReunida.anio);
        const nivelValor = valor(cabeceraReunida && (cabeceraReunida.nivel_nombre || cabeceraReunida.nivel));

        cargoInfoGeneral.innerHTML = `
            <div class="pof-cargos-info-item">
                <span>Reunida</span>
                <strong>${escaparHtml(cabeceraValor)}</strong>
            </div>
            <div class="pof-cargos-info-item">
                <span>Nivel</span>
                <strong>${escaparHtml(nivelValor)}</strong>
            </div>
            <div class="pof-cargos-info-item">
                <span>CUEANEXO</span>
                <strong>${escaparHtml(valor(padronSeleccionado && padronSeleccionado.padron_cueanexo))}</strong>
            </div>
            <div class="pof-cargos-info-item${claseCampoHistoricoModificado(padronSeleccionado, "establecimiento")}">
                <span>Establecimiento</span>
                <strong>${escaparHtml(valor(padronSeleccionado && padronSeleccionado.nom_est))}</strong>
                ${campoHistoricoModificado(padronSeleccionado, "establecimiento") ? '<em class="pof-history-modified-tag">Modificado</em>' : ''}
            </div>
            <div class="pof-cargos-info-item">
                <span>Oferta</span>
                <strong>${escaparHtml(valor(padronSeleccionado && padronSeleccionado.oferta))}</strong>
            </div>
        `;
    }

    function renderizarTotalPuntosCargos() {
        const totalPuntos = formatearTotalPuntos(calcularTotalPuntosCargos());
        cargoTotalPuntos.innerHTML = `
            <span>Total puntos</span>
            <strong>${escaparHtml(totalPuntos)}</strong>
        `;
    }

    function renderizarTablaCargos() {
        if (cargosTemporales.length === 0) {
            cargoListaWrapper.classList.add("pof-hidden");
            cargoInfoGeneral.innerHTML = "";
            cargoTotalPuntos.textContent = "";
            tablaCargos.innerHTML = `
                <tr>
                    <td colspan="8" class="pof-empty-row">
                        Todavía no agregaste cargos.
                    </td>
                </tr>
            `;
            actualizarEstadoBotonGuardar();
            return;
        }

        ordenarCargosTemporales();
        cargoListaWrapper.classList.remove("pof-hidden");
        renderizarInfoGeneralCargos();
        renderizarTotalPuntosCargos();
        tablaCargos.innerHTML = cargosTemporales.map((cargo, index) => `
            <tr>
                <td>${valorHtml(cargo.ceic)}</td>
                <td>${valorHtml(cargo.cargo)}</td>
                <td>
                    <input
                        type="number"
                        class="pof-cargo-quantity-input"
                        min="1"
                        step="1"
                        value="${escaparHtml(obtenerCantidadCargoTemporal(cargo) || 1)}"
                        data-cargo-quantity-index="${index}"
                        aria-label="Cantidad del cargo ${escaparHtml(cargo.cargo)}">
                </td>
                <td>${valorHtml(cargo.unidad_texto)}</td>
                <td>${valorHtml(cargo.puntos_asignados)}</td>
                <td>${valorHtml(calcularTotalCargoTemporal(cargo).toFixed(2))}</td>
                <td class="pof-cargo-observation-cell">${cargo.observacion ? escaparHtml(cargo.observacion) : "-"}</td>
                <td class="pof-cargo-action-cell">
                    <button type="button" class="pof-cargo-remove-btn" title="Quitar cargo" aria-label="Quitar cargo" data-cargo-remove-index="${index}">
                        ❌
                    </button>
                </td>
            </tr>
        `).join("");
        actualizarEstadoBotonGuardar();
    }

    function armarPayloadGuardado() {
        return {
            cabecera_tipo: "REUNIDA",
            anio: cabeceraReunida.anio,
            nivel: cabeceraReunida.nivel,
            proyecto_especial_id: null,
            tipo_operacion: "ALTA",
            padron: padronSeleccionado,
            cargos: cargosTemporales.map(cargo => ({
                ceic: cargo.ceic,
                ceic_fuera_sugerencia: Boolean(cargo.ceic_fuera_sugerencia),
                observacion: cargo.observacion || "",
                cantidad: cargo.cantidad,
                unidad_cantidad: cargo.unidad_cantidad,
            })),
        };
    }

    function cerrarConfirmacionCarga() {
        modalConfirmarCarga.classList.add("pof-hidden");
        modalConfirmarCarga.setAttribute("aria-hidden", "true");
        modalCargoTotalPuntos.textContent = "";
    }

    function abrirConfirmacionCarga() {
        if (!cabeceraReunidaValidada || !padronSeleccionado || cargosTemporales.length === 0) {
            mostrarEstadoGuardado("error", "Validá la cabecera, seleccioná padrón y agregá al menos un cargo.");
            actualizarEstadoBotonGuardar();
            return;
        }

        ordenarCargosTemporales();
        tablaConfirmarCarga.innerHTML = cargosTemporales.map(cargo => `
            <tr>
                <td>${valorHtml(cargo.ceic)}</td>
                <td>${valorHtml(padronSeleccionado && padronSeleccionado.oferta)}</td>
                <td>${valorHtml(cargo.cargo)}</td>
                <td>${valorHtml(cargo.cantidad)}</td>
                <td>${valorHtml(cargo.unidad_texto)}</td>
                <td>${valorHtml(cargo.puntos_asignados)}</td>
                <td>${valorHtml(calcularTotalCargoTemporal(cargo).toFixed(2))}</td>
                <td>${cargo.observacion ? escaparHtml(cargo.observacion) : "-"}</td>
            </tr>
        `).join("");
        modalCargoTotalPuntos.innerHTML = `
            <span>Total puntos</span>
            <strong>${escaparHtml(formatearTotalPuntos(calcularTotalPuntosCargos()))}</strong>
        `;
        modalConfirmarCarga.classList.remove("pof-hidden");
        modalConfirmarCarga.setAttribute("aria-hidden", "false");
    }

    async function guardarCarga() {
        if (guardandoCarga) {
            return;
        }

        if (!cabeceraReunidaValidada || !padronSeleccionado || cargosTemporales.length === 0) {
            mostrarEstadoGuardado("error", "Validá la cabecera, seleccioná padrón y agregá al menos un cargo.");
            actualizarEstadoBotonGuardar();
            return;
        }

        guardandoCarga = true;
        btnGuardarCarga.disabled = true;
        btnConfirmarGuardarCarga.disabled = true;
        mostrarEstadoGuardado("warn", "Guardando carga POF...");

        try {
            const response = await fetch(URL_GUARDAR_CARGA_POF, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": obtenerCsrfToken(),
                },
                body: JSON.stringify(armarPayloadGuardado()),
            });
            const data = await response.json();

            if (!response.ok || !data.ok) {
                const detalleErrores = formatearErroresBackend(data.errores);
                mostrarEstadoGuardado("error", detalleErrores || data.mensaje || "No se pudo guardar la carga.");
                return;
            }

            limpiarCargaTemporalPostGuardado();
            cerrarConfirmacionCarga();
            mostrarExitoGuardado(data);
        } catch (error) {
            mostrarEstadoGuardado("error", "No se pudo guardar la carga.");
        } finally {
            guardandoCarga = false;
            btnConfirmarGuardarCarga.disabled = false;
            actualizarEstadoBotonGuardar();
        }
    }

    document.addEventListener("click", function (event) {
        if (!event.target.closest(".pof-autocomplete")) {
            document.querySelectorAll(".pof-suggestions").forEach(caja => {
                caja.classList.add("pof-hidden");
            });
        }
    });

    // --- Inicialización y estado inicial ---
    aplicarEstadoBusquedaPadron(false);
    renderizarTablaCargos();

    if (anioInput.value && nivelSelect.value) {
        validarCabeceraReunida();
    }
