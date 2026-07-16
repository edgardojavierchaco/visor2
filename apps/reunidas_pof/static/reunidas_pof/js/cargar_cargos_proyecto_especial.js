    const cargarCargosProyectoEspecialConfigElement = document.getElementById("cargarCargosProyectoEspecialConfig");
    if (!cargarCargosProyectoEspecialConfigElement) {
        throw new Error("Falta la configuracion de Alta de Cargos de Proyecto Especial.");
    }
    const CARGAR_CARGOS_PROYECTO_ESPECIAL_CONFIG = JSON.parse(cargarCargosProyectoEspecialConfigElement.textContent || "{}");
    const PROYECTO_ESPECIAL = Object.assign({ id: "", anio: "", nombre: "", resolucion: "" }, CARGAR_CARGOS_PROYECTO_ESPECIAL_CONFIG.proyectoEspecial || {});
    const PROYECTOS_ESPECIALES = Array.isArray(CARGAR_CARGOS_PROYECTO_ESPECIAL_CONFIG.proyectosEspeciales) ? CARGAR_CARGOS_PROYECTO_ESPECIAL_CONFIG.proyectosEspeciales : [];
    const URLS_CARGAR_CARGOS_PROYECTO_ESPECIAL = CARGAR_CARGOS_PROYECTO_ESPECIAL_CONFIG.urls || {};
    const URL_BUSCAR_PADRON_PE = URLS_CARGAR_CARGOS_PROYECTO_ESPECIAL.buscarPadron;
    const URL_CATALOGOS_MANUAL_PE = URLS_CARGAR_CARGOS_PROYECTO_ESPECIAL.catalogosManual;
    const URL_BUSCAR_CUOF_MANUAL_PE = URLS_CARGAR_CARGOS_PROYECTO_ESPECIAL.buscarCuofManual;
    const URL_CATALOGO_CEIC_PE = URLS_CARGAR_CARGOS_PROYECTO_ESPECIAL.catalogoCeic;
    const URL_GUARDAR_CARGA_PE = URLS_CARGAR_CARGOS_PROYECTO_ESPECIAL.guardarCarga;
    const URL_DETALLE_REUNIDA = URLS_CARGAR_CARGOS_PROYECTO_ESPECIAL.detalleReunida;
    if (!URL_BUSCAR_PADRON_PE || !URL_CATALOGOS_MANUAL_PE || !URL_BUSCAR_CUOF_MANUAL_PE || !URL_CATALOGO_CEIC_PE || !URL_GUARDAR_CARGA_PE || !URL_DETALLE_REUNIDA) {
        throw new Error("La configuracion de Alta de Cargos de Proyecto Especial esta incompleta.");
    }
    const MENSAJE_ERROR_GENERAL_CABECERA = "No se pudo validar la cabecera. Revisá los campos marcados.";
    const MENSAJE_ERROR_PROYECTO = "Seleccioná un Proyecto Especial POF.";
    const SIN_INFORMACION = "Sin información";

    const MODO_PADRON = "PADRON";
    const MODO_MANUAL = "MANUAL_CONTROLADO";
    const CAMPOS_CATALOGOS_MANUAL = [
        "region", "localidad", "departamento",
        "acronimo", "ambito", "categoria", "jornada"
    ];
    const CAMPOS_SELECT2_MANUAL = [
        "region", "localidad", "departamento",
        "acronimo", "ambito", "categoria", "jornada"
    ];
    const CAMPOS_ESTADOS_MANUAL = ["estado_localizacion_padron"];

    let modoPadronActual = "";
    let padronSeleccionado = null;
    let resultadosPadronActuales = [];
    let catalogosManual = null;
    let cargandoCatalogos = false;
    let cargosTemporales = [];
    let guardandoCarga = false;
    let temporizadorCeic = null;
    let secuenciaBusquedaCeic = 0;
    let unidadAutoSeleccionadaPorCeic = false;
    let catalogoCeic = [];
    let catalogoCeicCargado = false;
    let catalogoCeicPromise = null;
    let temporizadorCuofManual = null;
    let secuenciaBusquedaCuofManual = 0;
    let resultadosCuofManualActuales = [];
    let datosCuofManualAutocompletados = null;
    let cuofManualRequierePadron = null;
    let cabeceraEditable = false;
    let ofertaAbiertaIndex = null;
    let filtroOfertaTexto = "";
    let filtroOfertaEstado = "TODOS";
    const LIMITE_RESULTADOS_CEIC = 5;

    const proyectoEspecialSelect = document.getElementById("proyectoEspecialSelect");
    const proyectoEspecialId = document.getElementById("proyectoEspecialId");
    const proyectoHint = document.getElementById("proyectoHint");
    const btnValidarCabeceraProyecto = document.getElementById("btnValidarCabeceraProyecto");
    const btnCambiarCabecera = document.getElementById("btnCambiarCabecera");
    const bloqueOrigenProyecto = document.getElementById("bloqueOrigenProyecto");
    const estadoCabecera = document.getElementById("estadoCabecera");
    const btnModoPadron = document.getElementById("btnModoPadron");
    const btnModoManual = document.getElementById("btnModoManual");
    const bloquePadron = document.getElementById("bloquePadron");
    const bloqueManual = document.getElementById("bloqueManual");
    const bloqueCamposManual = document.getElementById("bloqueCamposManual");
    const resultadosPadron = document.getElementById("resultadosPadron");
    const bloqueSeleccion = document.getElementById("bloqueSeleccion");
    const detalleSeleccion = document.getElementById("detalleSeleccion");
    const bloqueCargos = document.getElementById("bloqueCargos");
    const bloqueGuardarCarga = document.getElementById("bloqueGuardarCarga");
    const estadoOrigen = document.getElementById("estadoOrigen");
    const estadoPadron = document.getElementById("estadoPadron");
    const estadoManual = document.getElementById("estadoManual");
    const estadoGuardado = document.getElementById("estadoGuardado");
    const cueBaseInput = document.getElementById("cueBase");
    const anexoInput = document.getElementById("anexo");
    const cueanexoInput = document.getElementById("cueanexo");
    const ceicBusqueda = document.getElementById("ceicBusqueda");
    const ceicSeleccionado = document.getElementById("ceicSeleccionado");
    const cargoSeleccionado = document.getElementById("cargoSeleccionado");
    const cantidadCargo = document.getElementById("cantidadCargo");
    const unidadCargo = document.getElementById("unidadCargo");
    const puntosCargo = document.getElementById("puntosCargo");
    const totalCargo = document.getElementById("totalCargo");
    const observacionCargo = document.getElementById("observacionCargo");
    const observationCargoActions = document.getElementById("observationCargoActions");
    const panelObservacionCargo = document.getElementById("panelObservacionCargo");
    const btnMostrarObservacion = document.getElementById("btnMostrarObservacion");
    const btnQuitarObservacion = document.getElementById("btnQuitarObservacion");
    const ceicLoading = document.getElementById("ceicLoading");
    const sugerenciasCeic = document.getElementById("sugerenciasCeic");
    const mensajeCeic = document.getElementById("mensajeCeic");
    const manualCuofLoading = document.getElementById("manualCuofLoading");
    const sugerenciasCuofManual = document.getElementById("sugerenciasCuofManual");
    const mensajeCuofManual = document.getElementById("mensajeCuofManual");
    const accionCuofPadronManual = document.getElementById("accionCuofPadronManual");
    const cargoListaWrapper = document.getElementById("cargoListaWrapper");
    const cargoInfoGeneral = document.getElementById("cargoInfoGeneral");
    const tablaCargos = document.getElementById("tablaCargos");
    const cargoTotalPuntos = document.getElementById("cargoTotalPuntos");
    const btnGuardarCarga = document.getElementById("btnGuardarCarga");
    const modalConfirmarCarga = document.getElementById("modalConfirmarCarga");
    const tablaConfirmarCarga = document.getElementById("tablaConfirmarCarga");
    const modalCargoTotalPuntos = document.getElementById("modalCargoTotalPuntos");
    const btnConfirmarGuardarCarga = document.getElementById("btnConfirmarGuardarCarga");
    const btnBuscarPadron = document.getElementById("btnBuscarPadron");
    const btnConfirmarManual = document.getElementById("btnConfirmarManual");
    const btnAgregarCargoLista = document.getElementById("btnAgregarCargoLista");
    const controlObservacionCargo = crearControlObservacionCargo({
        panel: panelObservacionCargo,
        botonMostrar: btnMostrarObservacion,
        accionesPanel: observationCargoActions,
        botonPrincipal: btnAgregarCargoLista,
        textarea: observacionCargo,
    });

    const manualInputs = {
        cuof: document.getElementById("manualCuof"),
        cui: document.getElementById("manualCui"),
        nombre: document.getElementById("manualNombre"),
        numero: document.getElementById("manualNumero"),
        region: document.getElementById("manualRegion"),
        localidad: document.getElementById("manualLocalidad"),
        departamento: document.getElementById("manualDepartamento"),
        acronimo: document.getElementById("manualAcronimo"),
        ambito: document.getElementById("manualAmbito"),
        categoria: document.getElementById("manualCategoria"),
        jornada: document.getElementById("manualJornada"),
        estado_localizacion_padron: document.getElementById("manualEstadoLocalizacion"),
    };
    const CAMPOS_REFERENCIA_MANUAL = [
        "cui",
        "nombre",
        "numero",
        "region",
        "localidad",
        "departamento",
        "acronimo",
        "ambito",
        "categoria",
        "jornada",
        "estado_localizacion_padron"
    ];
    const CAMPOS_TEXTO_MANUAL = {
        cuof: {
            maxLength: 100,
            obligatorio: true,
            mensajeObligatorio: "El CUOF es obligatorio."
        },
        cui: {
            maxLength: 100,
            obligatorio: false
        },
        numero: {
            maxLength: 100,
            obligatorio: false
        },
        nombre: {
            maxLength: 255,
            obligatorio: false
        }
    };
    const MENSAJES_CAMPOS_CATALOGO_MANUAL = {
        region: "Debe seleccionar una región válida.",
        localidad: "Debe seleccionar una localidad válida.",
        departamento: "Debe seleccionar un departamento válido.",
        acronimo: "Debe seleccionar un acrónimo válido.",
        ambito: "Debe seleccionar un ámbito válido.",
        categoria: "Debe seleccionar una categoría válida.",
        jornada: "Debe seleccionar una jornada válida.",
        estado_localizacion_padron: "Debe seleccionar un estado de localización válido."
    };
    const CAMPOS_CATALOGO_MANUAL_VALIDABLES = [
        "region",
        "localidad",
        "departamento",
        "acronimo",
        "ambito",
        "categoria",
        "jornada",
        "estado_localizacion_padron"
    ];

    function valor(dato) {
        const texto = String(dato || "").trim();
        return texto || "-";
    }

    function valorHtml(dato) {
        return escaparHtml(valor(dato));
    }

    function esPlaceholderManual(valorTexto) {
        const texto = String(valorTexto || "").trim().toLowerCase();
        return (
            !texto
            || texto.startsWith("seleccioná")
            || texto.startsWith("selecciona")
            || texto.startsWith("seleccione")
        );
    }

    function mostrarEstado(elemento, tipo, mensaje) {
        elemento.className = tipo ? `pof-status ${tipo}` : "pof-status";
        elemento.textContent = mensaje || "";
    }

    function esErrorGeneralCamposManualActivo() {
        return estadoManual.textContent.trim() === "Revisá los campos informados antes de continuar.";
    }

    function obtenerContenedorCampoManual(campo) {
        const input = manualInputs[campo];
        return input ? input.closest(".pof-field") : null;
    }

    function obtenerNodoErrorCampoManual(campo) {
        const contenedor = obtenerContenedorCampoManual(campo);
        return contenedor ? contenedor.querySelector(`[data-manual-error-for="${campo}"]`) : null;
    }

    function mostrarErrorCampoManual(campo, mensaje) {
        const contenedor = obtenerContenedorCampoManual(campo);
        if (!contenedor) {
            return;
        }
        contenedor.classList.add("pof-filter-field-error");
        let ayuda = obtenerNodoErrorCampoManual(campo);
        if (!ayuda) {
            ayuda = document.createElement("span");
            ayuda.className = "pof-filter-field-help";
            ayuda.dataset.manualErrorFor = campo;
            contenedor.appendChild(ayuda);
        }
        ayuda.textContent = mensaje;
    }

    function limpiarErrorCampoManual(campo) {
        const contenedor = obtenerContenedorCampoManual(campo);
        if (!contenedor) {
            return;
        }
        contenedor.classList.remove("pof-filter-field-error");
        const ayuda = obtenerNodoErrorCampoManual(campo);
        if (ayuda) {
            ayuda.remove();
        }
    }

    function limpiarErroresCamposManual() {
        Object.keys(manualInputs).forEach(campo => {
            limpiarErrorCampoManual(campo);
        });
        if (esErrorGeneralCamposManualActivo()) {
            mostrarEstado(estadoManual, "", "");
        }
    }

    function obtenerCampo(item, campos) {
        if (!item) {
            return "";
        }
        for (const campo of campos) {
            if (item[campo] !== null && item[campo] !== undefined && item[campo] !== "") {
                return item[campo];
            }
        }
        return "";
    }

    function formatearErroresBackend(errores) {
        if (!errores) {
            return "";
        }
        if (Array.isArray(errores)) {
            return errores.join(" ");
        }
        if (typeof errores === "object") {
            return Object.values(errores).map(formatearErroresBackend).filter(Boolean).join(" ");
        }
        return String(errores);
    }

    function obtenerProyectoPorId(id) {
        return PROYECTOS_ESPECIALES.find(proyecto => String(proyecto.id) === String(id));
    }

    function cabeceraProyectoSeleccionada() {
        return Boolean(String(PROYECTO_ESPECIAL.id || "").trim() && String(proyectoEspecialId.value || "").trim());
    }

    function actualizarDisponibilidadFlujoPorCabecera() {
        const habilitado = cabeceraProyectoSeleccionada();
        bloqueOrigenProyecto.classList.toggle("pof-hidden", !habilitado);
        btnModoPadron.disabled = !habilitado;
        btnModoManual.disabled = !habilitado;
        btnBuscarPadron.disabled = !habilitado;
        btnConfirmarManual.disabled = !habilitado;
        btnAgregarCargoLista.disabled = !habilitado;
        actualizarEstadoBotonGuardar();
    }

    function obtenerContenedorCabeceraProyecto() {
        return proyectoEspecialSelect ? proyectoEspecialSelect.closest(".pof-field") : null;
    }

    function limpiarErrorCabeceraProyecto() {
        const contenedor = obtenerContenedorCabeceraProyecto();
        if (contenedor) {
            contenedor.classList.remove("pof-filter-field-error");
        }
        proyectoHint.textContent = "";
        proyectoHint.className = "pof-field-hint";
        if (estadoCabecera.classList.contains("error") || estadoCabecera.textContent.trim() === MENSAJE_ERROR_GENERAL_CABECERA) {
            mostrarEstado(estadoCabecera, "", "");
        }
    }

    function mostrarErrorCabeceraProyecto(estadoDestino = null) {
        const contenedor = obtenerContenedorCabeceraProyecto();
        if (contenedor) {
            contenedor.classList.add("pof-filter-field-error");
        }
        proyectoHint.textContent = MENSAJE_ERROR_PROYECTO;
        proyectoHint.className = "pof-filter-field-help";
        mostrarEstado(estadoCabecera, "error", MENSAJE_ERROR_GENERAL_CABECERA);
        if (estadoDestino && estadoDestino !== estadoCabecera) {
            mostrarEstado(estadoDestino, "error", "Seleccioná un Proyecto Especial POF antes de continuar.");
        }
    }
    function exigirCabeceraProyectoSeleccionada(estadoDestino = null) {
        if (cabeceraProyectoSeleccionada()) {
            return true;
        }
        mostrarErrorCabeceraProyecto(estadoDestino);
        if (!cabeceraEditable) {
            habilitarCambioCabecera();
        } else {
            proyectoEspecialSelect.focus();
        }
        return false;
    }

    function hayDatosDependientesCabecera() {
        return Boolean(
            padronSeleccionado
            || resultadosPadronActuales.length
            || cargosTemporales.length
            || modoPadronActual
        );
    }

    function actualizarSelect2Proyecto() {
        if (!window.jQuery || !window.jQuery.fn.select2 || !proyectoEspecialSelect) {
            return;
        }
        window.jQuery(proyectoEspecialSelect)
            .prop("disabled", proyectoEspecialSelect.disabled)
            .trigger("change.select2");
    }

    function bloquearCabeceraProyecto() {
        cabeceraEditable = false;
        proyectoEspecialSelect.disabled = true;
        proyectoEspecialSelect.classList.add("pof-locked-control");
        proyectoEspecialId.value = PROYECTO_ESPECIAL.id;
        proyectoEspecialSelect.value = PROYECTO_ESPECIAL.id;
        limpiarErrorCabeceraProyecto();
        btnValidarCabeceraProyecto.classList.add("pof-hidden");
        btnCambiarCabecera.classList.remove("pof-hidden");
        actualizarSelect2Proyecto();
        mostrarEstado(estadoCabecera, "ok", "Cabecera de Proyecto Especial validada.");
        actualizarDisponibilidadFlujoPorCabecera();
    }
    function validarCabeceraProyecto() {
        const proyecto = obtenerProyectoPorId(proyectoEspecialSelect.value);
        if (!proyecto) {
            proyectoEspecialId.value = "";
            actualizarDisponibilidadFlujoPorCabecera();
            mostrarErrorCabeceraProyecto();
            return;
        }
        PROYECTO_ESPECIAL.id = proyecto.id;
        PROYECTO_ESPECIAL.anio = proyecto.anio;
        PROYECTO_ESPECIAL.nombre = proyecto.nombre;
        PROYECTO_ESPECIAL.resolucion = proyecto.resolucion || "";
        limpiarErrorCabeceraProyecto();
        bloquearCabeceraProyecto();
    }

    function inicializarCabeceraProyecto() {
        if (PROYECTO_ESPECIAL.id) {
            bloquearCabeceraProyecto();
            return;
        }

        cabeceraEditable = true;
        proyectoEspecialSelect.disabled = false;
        proyectoEspecialSelect.classList.remove("pof-locked-control");
        proyectoEspecialId.value = "";
        proyectoEspecialSelect.value = "";
        limpiarErrorCabeceraProyecto();
        btnValidarCabeceraProyecto.classList.remove("pof-hidden");
        btnCambiarCabecera.classList.add("pof-hidden");
        mostrarEstado(estadoCabecera, "", "");
        actualizarDisponibilidadFlujoPorCabecera();
    }

    function habilitarCambioCabecera() {
        if (hayDatosDependientesCabecera()) {
            const confirmar = confirm(
                "Cambiar la cabecera limpiará la localización seleccionada y los cargos. ¿Continuar?"
            );
            if (!confirmar) {
                return;
            }
        }

        limpiarDatosCarga();
        modoPadronActual = "";
        cueBaseInput.value = "";
        anexoInput.value = "";
        cueanexoInput.value = "";
        manualInputs.cuof.value = "";
        cerrarConfirmacionCarga();
        bloquePadron.classList.add("pof-hidden");
        bloqueManual.classList.add("pof-hidden");
        mostrarEstado(estadoOrigen, "", "");
        mostrarEstado(estadoPadron, "", "");
        mostrarEstado(estadoManual, "", "");
        establecerDisponibilidadCuofManual(false);

        cabeceraEditable = true;
        proyectoEspecialSelect.disabled = false;
        proyectoEspecialSelect.classList.remove("pof-locked-control");
        PROYECTO_ESPECIAL.id = "";
        PROYECTO_ESPECIAL.anio = "";
        PROYECTO_ESPECIAL.nombre = "";
        PROYECTO_ESPECIAL.resolucion = "";
        proyectoEspecialId.value = "";
        proyectoEspecialSelect.value = "";
        limpiarErrorCabeceraProyecto();
        btnValidarCabeceraProyecto.classList.remove("pof-hidden");
        btnCambiarCabecera.classList.add("pof-hidden");
        mostrarEstado(estadoCabecera, "", "");
        actualizarSelect2Proyecto();
        actualizarDisponibilidadFlujoPorCabecera();
    }

    function limpiarDatosCarga() {
        padronSeleccionado = null;
        resultadosPadronActuales = [];
        ofertaAbiertaIndex = null;
        filtroOfertaTexto = "";
        filtroOfertaEstado = "TODOS";
        cargosTemporales = [];
        detalleSeleccion.innerHTML = "";
        resultadosPadron.innerHTML = "";
        bloqueSeleccion.classList.add("pof-hidden");
        resultadosPadron.classList.add("pof-hidden");
        bloqueCargos.classList.add("pof-hidden");
        bloqueGuardarCarga.classList.add("pof-hidden");
        clearTimeout(temporizadorCuofManual);
        secuenciaBusquedaCuofManual += 1;
        datosCuofManualAutocompletados = null;
        cuofManualRequierePadron = null;
        limpiarSugerenciasCuofManual();
        mostrarMensajeCuofManual("");
        limpiarAccionCuofPadronManual();
        ocultarBloqueCamposManual();
        desbloquearCamposReferenciaManual();
        limpiarCamposReferenciaManual();
        mostrarCargaCuofManual(false);
        limpiarCargoActual();
        renderizarTablaCargos();
        mostrarEstado(estadoGuardado, "", "");
    }

    function activarModoPadron() {
        if (!exigirCabeceraProyectoSeleccionada(estadoOrigen)) {
            return;
        }
        modoPadronActual = MODO_PADRON;
        limpiarDatosCarga();
        bloquePadron.classList.remove("pof-hidden");
        bloqueManual.classList.add("pof-hidden");
        mostrarEstado(estadoOrigen, "ok", "Buscá una oferta oficial del padrón para asociarla al Proyecto Especial.");
        cueBaseInput.focus();
    }

    async function activarModoManual() {
        if (!exigirCabeceraProyectoSeleccionada(estadoOrigen)) {
            return;
        }
        modoPadronActual = MODO_MANUAL;
        limpiarDatosCarga();
        bloquePadron.classList.add("pof-hidden");
        resultadosPadron.classList.add("pof-hidden");
        bloqueManual.classList.remove("pof-hidden");
        mostrarEstado(estadoOrigen, "ok", "Completá el ingreso manual controlado sin consultar padrón.");
        establecerDisponibilidadCuofManual(false);
        const catalogosListos = await cargarCatalogosManual();
        if (catalogosListos && cabeceraProyectoSeleccionada() && modoPadronActual === MODO_MANUAL) {
            establecerDisponibilidadCuofManual(true);
            manualInputs.cuof.focus();
        }
    }

    function limpiarDigitos(valor, maxLength) {
        return String(valor || "").replace(/\D/g, "").slice(0, maxLength);
    }

    function actualizarCueanexoDesdePartes() {
        const resultado = construirCueanexoDesdePartes(
            cueBaseInput.value,
            anexoInput.value
        );

        cueBaseInput.value = resultado.cue;
        anexoInput.value = resultado.anexo;
        cueanexoInput.value = resultado.cueanexo;
    }

    function normalizarPadronOficial(item) {
        const ofertaReal = obtenerCampo(item, ["oferta_real", "oferta"]);
        return {
            ...item,
            oferta_real: ofertaReal,
            oferta: ofertaReal,
            origen_datos: "PADRON",
            estado_padron: "VIGENTE"
        };
    }

    function obtenerOfertaReal(item) {
        return obtenerCampo(item, ["oferta_real", "oferta"]);
    }

    function obtenerEstadoOferta(item) {
        const estado = obtenerCampo(item, [
            "estado_oferta",
            "est_oferta",
            "estado",
            "estado_localizacion",
            "estado_loc",
        ]);
        return normalizarEstadoOferta(estado);
    }

    function renderizarBadgeEstadoOferta(item) {
        const estado = obtenerEstadoOferta(item);
        return renderizarBadgeEstadoOfertaComun(estado);
    }

    function obtenerLineaPrincipalOferta(item, icono = "\uD83D\uDCCC") {
        const oferta = obtenerOfertaReal(item);
        const establecimiento = obtenerCampo(item, ["nom_est", "establecimiento", "nombre_establecimiento"]);
        const partes = [];

        if (icono) {
            partes.push(icono);
        }
        partes.push(oferta || "Oferta sin identificar");
        if (establecimiento) {
            partes.push(`- ${establecimiento}`);
        }
        return partes.join(" ");
    }

    function obtenerLineaPrincipalManual(item) {
        return obtenerCampo(item, ["nom_est", "nombre_establecimiento"]) || "Referencia manual";
    }

    function obtenerLineaSecundariaLocalizacion(item) {
        const cuof = obtenerCampo(item, ["cuof_loc", "cuof"]);
        const categoria = obtenerCampo(item, ["categoria", "categoria_loc"]);
        const jornada = obtenerCampo(item, ["jornada", "jornada_loc"]);
        const partes = [
            cuof ? `CUOF: ${cuof}` : "",
            obtenerCampo(item, ["localidad", "departamento", "ref_loc"]),
            categoria ? `Categoría: ${categoria}` : "",
            jornada ? `Jornada: ${jornada}` : "",
        ].filter(Boolean);

        return partes.join(" · ") || "Sin datos complementarios";
    }

    function obtenerTextoBusquedaOferta(item) {
        return normalizarTextoOferta([
            obtenerOfertaReal(item),
            obtenerCampo(item, ["cuof_loc", "cuof"]),
            obtenerCampo(item, ["localidad"]),
            obtenerCampo(item, ["categoria", "categoria_loc"]),
            obtenerCampo(item, ["jornada", "jornada_loc"]),
        ].join(" "));
    }

    function renderizarDatoResumen(etiqueta, dato) {
        if (dato === null || dato === undefined || dato === "") {
            return "";
        }
        return `
            <div class="pof-data-item pof-offer-detail-item">
                <span>${escaparHtml(etiqueta)}</span>
                <strong>${escaparHtml(dato)}</strong>
            </div>
        `;
    }

    function renderizarGrupoDetalleLocalizacion(titulo, campos) {
        const items = campos
            .map(config => renderizarDatoResumen(config.etiqueta, config.valor))
            .join("");

        if (!items) {
            return "";
        }

        return `
            <section class="pof-offer-detail-section">
                <h3>${escaparHtml(titulo)}</h3>
                <div class="pof-offer-detail-section-grid">${items}</div>
            </section>
        `;
    }

    /**
     * Renderiza el detalle de una oferta oficial con la estructura sectorizada usada por Alta de Cargos.
     *
     * - Muestra solo campos disponibles del padrón.
     * - Conserva datos de identificación, establecimiento, oferta y estados separados.
     * - Reutiliza la advertencia visual existente cuando la oferta figura en BAJA.
     * - No se usa para referencias manuales, porque MANUAL_CONTROLADO no admite oferta/CUEANEXO.
     */
    function renderizarDetallePadron(item) {
        const detalle = [
            renderizarGrupoDetalleLocalizacion("Identificación", [
                { etiqueta: "CUEANEXO", valor: obtenerCampo(item, ["padron_cueanexo", "cueanexo", "cue_anexo"]) },
                { etiqueta: "CUE", valor: obtenerCampo(item, ["cue"]) },
                { etiqueta: "Anexo", valor: obtenerCampo(item, ["anexo"]) },
                { etiqueta: "CUOF", valor: obtenerCampo(item, ["cuof_loc", "cuof"]) },
                { etiqueta: "CUI", valor: obtenerCampo(item, ["cui_loc", "cui"]) },
            ]),
            renderizarGrupoDetalleLocalizacion("Establecimiento", [
                { etiqueta: "Nombre", valor: obtenerCampo(item, ["nom_est", "establecimiento", "nombre_establecimiento"]) },
                { etiqueta: "Número", valor: obtenerCampo(item, ["nro_est", "numero_establecimiento"]) },
                { etiqueta: "Región", valor: obtenerCampo(item, ["region_loc", "region", "regional_actual"]) },
                { etiqueta: "Localidad", valor: obtenerCampo(item, ["localidad"]) },
                { etiqueta: "Departamento", valor: obtenerCampo(item, ["departamento"]) },
            ]),
            renderizarGrupoDetalleLocalizacion("Oferta", [
                { etiqueta: "Oferta educativa", valor: obtenerOfertaReal(item) },
                { etiqueta: "Acrónimo", valor: obtenerCampo(item, ["acronimo"]) },
                { etiqueta: "Ámbito", valor: obtenerCampo(item, ["ambito"]) },
                { etiqueta: "Categoría", valor: obtenerCampo(item, ["categoria", "categoria_loc"]) },
                { etiqueta: "Jornada", valor: obtenerCampo(item, ["jornada", "jornada_loc"]) },
            ]),
            renderizarGrupoDetalleLocalizacion("Estados", [
                { etiqueta: "Estado localización", valor: obtenerCampo(item, ["estado_loc", "estado_localizacion_padron", "estado_localizacion"]) },
                { etiqueta: "Estado oferta", valor: obtenerCampo(item, ["est_oferta", "estado_oferta_padron", "estado_oferta", "oferta_estado"]) },
                { etiqueta: "Estado establecimiento", valor: obtenerCampo(item, ["estado_est", "estado_establecimiento_padron", "estado_establecimiento"]) },
            ]),
        ].join("");

        if (obtenerEstadoOferta(item).codigo !== "BAJA") {
            return detalle;
        }

        return `
            ${detalle}
            <div class="pof-offer-warning">
                Esta oferta figura como baja en el padrón actual. Verifique si corresponde usarla para el Proyecto Especial seleccionado.
            </div>
        `;
    }

    /**
     * Renderiza una referencia MANUAL_CONTROLADO sin mezclar campos exclusivos de padrón.
     *
     * - Omite CUE, Anexo, CUEANEXO, oferta educativa y estados de oferta/establecimiento.
     * - Usa nombre, CUOF, CUI y catálogos manuales como fuente visual principal.
     * - Mantiene la misma grilla sectorizada que el resumen de padrón.
     */
    function renderizarDetalleManual(item) {
        return [
            renderizarGrupoDetalleLocalizacion("Identificación", [
                { etiqueta: "CUOF", valor: obtenerCampo(item, ["cuof_loc", "cuof"]) },
                { etiqueta: "CUI", valor: obtenerCampo(item, ["cui_loc", "cui"]) },
            ]),
            renderizarGrupoDetalleLocalizacion("Establecimiento / referencia", [
                { etiqueta: "Nombre", valor: obtenerCampo(item, ["nom_est", "nombre_establecimiento"]) },
                { etiqueta: "Número", valor: obtenerCampo(item, ["nro_est", "numero_establecimiento"]) },
                { etiqueta: "Región", valor: obtenerCampo(item, ["region_loc", "region"]) },
                { etiqueta: "Localidad", valor: obtenerCampo(item, ["localidad"]) },
                { etiqueta: "Departamento", valor: obtenerCampo(item, ["departamento"]) },
            ]),
            renderizarGrupoDetalleLocalizacion("Características", [
                { etiqueta: "Acrónimo", valor: obtenerCampo(item, ["acronimo"]) },
                { etiqueta: "Ámbito", valor: obtenerCampo(item, ["ambito"]) },
                { etiqueta: "Categoría", valor: obtenerCampo(item, ["categoria", "categoria_loc"]) },
                { etiqueta: "Jornada", valor: obtenerCampo(item, ["jornada", "jornada_loc"]) },
            ]),
            renderizarGrupoDetalleLocalizacion("Estado", [
                { etiqueta: "Estado localización", valor: obtenerCampo(item, ["estado_loc", "estado_localizacion_padron", "estado_localizacion"]) },
            ]),
        ].join("");
    }

    async function buscarPadron() {
        if (!exigirCabeceraProyectoSeleccionada(estadoPadron)) {
            return;
        }
        limpiarDatosCarga();
        modoPadronActual = MODO_PADRON;

        cueanexoInput.value = limpiarDigitos(cueanexoInput.value, 9);
        const cue = limpiarDigitos(cueBaseInput.value, 7);
        const anexo = limpiarDigitos(anexoInput.value, 2);
        const cueanexo = cueanexoInput.value;

        if (!cue && !cueanexo) {
            mostrarEstado(estadoPadron, "error", "Ingresá un CUE, Anexo o CUEANEXO para buscar en padrón.");
            return;
        }
        if (cueanexo && cueanexo.length !== 9) {
            mostrarEstado(estadoPadron, "error", "El CUEANEXO debe tener 9 dígitos.");
            return;
        }
        if (!cueanexo && cue && cue.length !== 7) {
            mostrarEstado(estadoPadron, "error", "El CUE debe tener 7 dígitos.");
            return;
        }
        if (!cueanexo && anexo && anexo.length !== 2) {
            mostrarEstado(estadoPadron, "error", "El anexo debe tener 2 dígitos.");
            return;
        }

        mostrarEstado(estadoPadron, "warn", "Buscando ofertas oficiales en padrón...");
        const parametros = new URLSearchParams();
        if (cueanexo) {
            parametros.append("cueanexo", cueanexo);
        } else {
            parametros.append("cue", cue);
            if (anexo) {
                parametros.append("anexo", anexo);
            }
        }

        try {
            const response = await fetch(`${URL_BUSCAR_PADRON_PE}?${parametros.toString()}`);
            const data = await response.json();

            if (!response.ok || !data.ok) {
                mostrarEstado(estadoPadron, "error", data.mensaje || "No se encontraron ofertas en padrón para la búsqueda indicada. Podés usar ingreso manual controlado si corresponde.");
                return;
            }

            resultadosPadronActuales = Array.isArray(data.resultados) ? data.resultados : [];
            renderizarResultadosPadron(resultadosPadronActuales);

            if (resultadosPadronActuales.length > 0) {
                cueBaseInput.disabled = true;
            }

            mostrarEstado(estadoPadron, "ok", `Se encontraron ${resultadosPadronActuales.length} oferta(s) oficiales.`);
        } catch (error) {
            mostrarEstado(estadoPadron, "error", "No se pudo realizar la búsqueda en padrón.");
        }
    }

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

    function renderizarListaTarjetasOferta(ofertasVisibles, mensajeVacio) {
        if (!ofertasVisibles.length) {
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

                    return `
                        <div class="pof-offer-card${abierta ? " pof-offer-card-open" : ""}" data-oferta-index="${index}">
                            <button type="button"
                                    class="pof-offer-card-header"
                                    aria-expanded="${abierta ? "true" : "false"}"
                                    data-oferta-toggle-index="${index}">
                                <span class="pof-offer-card-heading">
                                    <span class="pof-offer-card-main">
                                        <span class="pof-offer-card-title">${escaparHtml(obtenerLineaPrincipalOferta(item))}</span>
                                        ${renderizarBadgeEstadoOferta(item)}
                                    </span>
                                    <span class="pof-offer-card-meta">${escaparHtml(obtenerLineaSecundariaLocalizacion(item))}</span>
                                </span>
                                <span class="pof-offer-card-toggle" aria-hidden="true">${abierta ? "\uD83D\uDD3D" : "\u25B6\uFE0F"}</span>
                            </button>

                            <div class="pof-offer-card-body${abierta ? "" : " pof-hidden"}">
                                <div class="pof-offer-detail-compact pof-offer-detail-grid">
                                    ${renderizarDetallePadron(item)}
                                </div>

                                <div class="pof-mt-2">
                                    <button type="button" class="pof-btn pof-btn-primary" data-seleccionar-oferta-index="${index}">
                                        Seleccionar oferta
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
     * Renderiza los resultados de padrón de Proyecto Especial con tarjetas expandibles.
     *
     * - Reutiliza las clases visuales de Alta de Cargos de Reunidas.
     * - Mantiene todas las ofertas en un único listado, sin secciones por sugerencia de nivel.
     * - Preserva filtros y tarjeta abierta cuando el usuario interactúa con la lista.
     */
    function renderizarResultadosPadron(resultados, conservarApertura = false, mantenerFocoFiltro = false) {
        resultadosPadron.classList.remove("pof-hidden");
        const resultadosRecibidos = Array.isArray(resultados) ? resultados : [];
        resultadosPadronActuales = resultadosRecibidos;

        if (!conservarApertura) {
            ofertaAbiertaIndex = null;
        }

        if (!resultadosRecibidos.length) {
            resultadosPadron.innerHTML = `
                <div class="pof-status warn">
                    No se encontraron ofertas en padrón para la búsqueda indicada. Podés usar ingreso manual controlado si corresponde.
                </div>
            `;
            return;
        }

        const ofertasVisibles = filtrarOfertasVisibles(resultadosPadronActuales);
        resultadosPadron.innerHTML = `
            <div class="pof-offer-results-shell pof-aura-card">
                <div class="pof-offer-results-head">
                    <div>
                        <strong>Se encontraron ${resultadosPadronActuales.length} ofertas para esta búsqueda.</strong>
                        <span class="pof-offer-results-count">Mostrando ${ofertasVisibles.length} de ${resultadosPadronActuales.length} ofertas.</span>
                    </div>
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
                    ${renderizarListaTarjetasOferta(ofertasVisibles, "No hay ofertas que coincidan con el filtro aplicado.")}
                </div>
            </div>
        `;
        vincularFiltrosOfertas(mantenerFocoFiltro);
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

    function seleccionarOfertaPadron(index) {
        const oferta = resultadosPadronActuales[index];
        if (!oferta) {
            mostrarEstado(estadoPadron, "error", "La oferta seleccionada no está disponible.");
            return;
        }
        modoPadronActual = MODO_PADRON;
        padronSeleccionado = normalizarPadronOficial(oferta);
        cargosTemporales = [];
        limpiarCargoActual();
        resultadosPadron.classList.add("pof-hidden");
        bloquePadron.classList.add("pof-hidden");
        bloqueSeleccion.classList.remove("pof-hidden");
        bloqueCargos.classList.remove("pof-hidden");
        renderizarSeleccion();
        renderizarTablaCargos();
        mostrarEstado(estadoPadron, "ok", "Oferta oficial seleccionada. Podés continuar con la carga de cargos.");
    }

    function llenarSelect(select, opciones, etiqueta) {
        const valores = Array.isArray(opciones) ? opciones : [];
        select.innerHTML = [
            `<option value="">Seleccioná ${escaparHtml(etiqueta)}</option>`,
            ...valores.map(opcion => `<option value="${escaparHtml(opcion)}">${escaparHtml(opcion)}</option>`)
        ].join("");
    }

    /**
     * Carga una dependencia de Select2 solo si la pantalla todavia no la tiene disponible.
     *
     * - Reutiliza los ids del patron existente para evitar cargas duplicadas.
     * - Inicializa los selects manuales cuando jQuery y Select2 estan listos.
     * - Mantiene tags desactivado para aceptar solo opciones del catalogo.
     */
    function cargarScriptSelect2Manual(url, callback) {
        const scriptExistente = Array.from(document.scripts).find(script => script.src === url);
        if (scriptExistente) {
            scriptExistente.addEventListener("load", callback, { once: true });
            return;
        }
        const script = document.createElement("script");
        script.type = "text/javascript";
        script.src = url;
        script.onload = callback;
        document.head.appendChild(script);
    }

    function inicializarDependenciasSelect2Manual() {
        if (!document.getElementById("select2-cdn-css")) {
            const link = document.createElement("link");
            link.id = "select2-cdn-css";
            link.rel = "stylesheet";
            link.href = "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css";
            document.head.appendChild(link);
        }

        if (!window.jQuery) {
            cargarScriptSelect2Manual("https://code.jquery.com/jquery-3.6.0.min.js", inicializarDependenciasSelect2Manual);
            return;
        }
        if (!window.jQuery.fn.select2) {
            cargarScriptSelect2Manual("https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js", inicializarDependenciasSelect2Manual);
            return;
        }
        inicializarSelect2Proyecto();
        inicializarSelect2Manual();
    }

    function inicializarSelect2Proyecto() {
        if (!window.jQuery || !window.jQuery.fn.select2 || !proyectoEspecialSelect) {
            return;
        }
        const $select = window.jQuery(proyectoEspecialSelect);
        if ($select.data("select2")) {
            $select.trigger("change.select2");
            return;
        }
        $select.select2({
            width: "100%",
            placeholder: proyectoEspecialSelect.dataset.placeholder || "Seleccioná un Proyecto Especial POF...",
            allowClear: false,
            closeOnSelect: true,
            dropdownParent: window.jQuery(proyectoEspecialSelect.closest(".pof-project-filter-search") || document.body),
            dropdownCssClass: "pof-project-select2-dropdown",
            selectionCssClass: "pof-project-select2-selection",
            minimumResultsForSearch: 0,
            tags: false,
            templateResult: function (opcion) {
                return opcion.text;
            },
            templateSelection: function (opcion) {
                return opcion.text;
            },
            language: {
                noResults: function () {
                    return "No se encontraron proyectos.";
                },
                searching: function () {
                    return "Buscando...";
                }
            }
        });
    }

    function inicializarSelect2Manual() {
        if (!window.jQuery || !window.jQuery.fn.select2) {
            return;
        }
        if (!bloqueCamposManualVisible()) {
            return;
        }
        CAMPOS_SELECT2_MANUAL.forEach(campo => {
            const select = manualInputs[campo];
            if (!select) {
                return;
            }
            const $select = window.jQuery(select);
            if ($select.data("select2")) {
                $select.trigger("change.select2");
                return;
            }
            const etiqueta = select.dataset.catalogo || campo;
            $select.select2({
                width: "100%",
                placeholder: `Seleccioná ${etiqueta}`,
                allowClear: false,
                closeOnSelect: true,
                dropdownParent: window.jQuery(bloqueManual),
                dropdownCssClass: "pof-project-select2-dropdown",
                minimumResultsForSearch: 0,
                tags: false,
                language: {
                    noResults: function () {
                        return "No se encontraron opciones.";
                    },
                    searching: function () {
                        return "Buscando...";
                    }
                }
            });
        });
    }

    function ocultarBloqueCamposManual() {
        bloqueCamposManual.classList.add("pof-hidden");
    }

    function mostrarBloqueCamposManual() {
        bloqueCamposManual.classList.remove("pof-hidden");
        inicializarDependenciasSelect2Manual();
    }

    function bloqueCamposManualVisible() {
        return !bloqueCamposManual.classList.contains("pof-hidden");
    }

    /**
     * Controla si el CUOF manual puede usarse mientras se preparan los catálogos.
     *
     * - Bloquea escritura y sugerencias hasta que los selects tengan opciones válidas.
     * - Reutiliza el estilo locked existente para mostrar el estado temporal.
     * - Evita búsquedas manuales con catálogos incompletos o fallidos.
     */
    function establecerDisponibilidadCuofManual(disponible) {
        manualInputs.cuof.disabled = !disponible;
        manualInputs.cuof.classList.toggle("pof-locked-control", !disponible);
        if (!disponible) {
            limpiarSugerenciasCuofManual();
            mostrarMensajeCuofManual("");
        }
    }

    async function cargarCatalogosManual() {
        if (catalogosManual) {
            return true;
        }
        if (cargandoCatalogos) {
            return false;
        }
        cargandoCatalogos = true;
        mostrarEstado(estadoManual, "", "");
        mostrarCargaCuofManual(true);
        try {
            const response = await fetch(URL_CATALOGOS_MANUAL_PE);
            const data = await response.json();
            if (!response.ok || !data.ok) {
                mostrarEstado(estadoManual, "error", data.mensaje || "No se pudieron cargar los catálogos de ingreso manual.");
                return false;
            }
            catalogosManual = data.catalogos || {};
            CAMPOS_CATALOGOS_MANUAL.forEach(campo => {
                llenarSelect(manualInputs[campo], catalogosManual[campo], campo);
            });
            CAMPOS_ESTADOS_MANUAL.forEach(campo => {
                llenarSelect(manualInputs[campo], catalogosManual[campo], "estado");
            });
            mostrarEstado(estadoManual, "", "");
            return true;
        } catch (error) {
            mostrarEstado(estadoManual, "error", "No se pudieron cargar los catálogos de ingreso manual.");
            return false;
        } finally {
            cargandoCatalogos = false;
            mostrarCargaCuofManual(false);
            establecerDisponibilidadCuofManual(
                Boolean(catalogosManual) && cabeceraProyectoSeleccionada() && modoPadronActual === MODO_MANUAL
            );
        }
    }

    function mostrarCargaCuofManual(cargando) {
        manualCuofLoading.classList.toggle("pof-hidden", !cargando);
        manualCuofLoading.setAttribute("aria-hidden", cargando ? "false" : "true");
    }

    function mostrarMensajeCuofManual(mensaje) {
        mensajeCuofManual.textContent = mensaje || "";
        mensajeCuofManual.classList.toggle("pof-hidden", !mensaje);
    }

    function limpiarAccionCuofPadronManual() {
        accionCuofPadronManual.innerHTML = "";
        accionCuofPadronManual.classList.add("pof-hidden");
    }

    function cueanexoDesdeItemManual(item) {
        return limpiarDigitos(obtenerCampo(item, ["padron_cueanexo", "cueanexo", "cue_anexo"]), 9);
    }

    function itemRequierePadron(item) {
        return Boolean(
            item
            && (
                item.requiere_padron
                || item.tiene_cueanexo
                || cueanexoDesdeItemManual(item)
            )
        );
    }

    function actualizarBloqueoCamposReferenciaManual(camposEditables) {
        const editables = new Set(camposEditables || []);
        CAMPOS_REFERENCIA_MANUAL.forEach(campo => {
            const input = manualInputs[campo];
            if (!input) {
                return;
            }
            const debeQuedarEditable = editables.has(campo);
            input.disabled = !debeQuedarEditable;
            input.classList.toggle("pof-locked-control", !debeQuedarEditable);
            if (window.jQuery && window.jQuery.fn.select2 && input.tagName === "SELECT") {
                window.jQuery(input).trigger("change.select2");
            }
        });
    }

    function bloquearCamposReferenciaManual() {
        actualizarBloqueoCamposReferenciaManual([]);
    }

    function desbloquearCamposReferenciaManual() {
        actualizarBloqueoCamposReferenciaManual(CAMPOS_REFERENCIA_MANUAL);
    }

    function limpiarCamposReferenciaManual() {
        CAMPOS_REFERENCIA_MANUAL.forEach(campo => {
            const input = manualInputs[campo];
            if (!input) {
                return;
            }
            input.value = "";
            if (window.jQuery && window.jQuery.fn.select2 && input.tagName === "SELECT") {
                window.jQuery(input).trigger("change");
            }
        });
        limpiarErroresCamposManual();
    }

    function limpiarSeleccionManualConfirmada() {
        if (!padronSeleccionado && !cargosTemporales.length) {
            return;
        }
        padronSeleccionado = null;
        cargosTemporales = [];
        detalleSeleccion.innerHTML = "";
        bloqueSeleccion.classList.add("pof-hidden");
        bloqueCargos.classList.add("pof-hidden");
        bloqueGuardarCarga.classList.add("pof-hidden");
        limpiarCargoActual();
        renderizarTablaCargos();
        mostrarEstado(estadoGuardado, "", "");
    }

    function mostrarAccionCuofPadronManual(item, mensaje) {
        const cueanexo = cueanexoDesdeItemManual(item);
        cuofManualRequierePadron = item || null;
        datosCuofManualAutocompletados = null;
        mostrarMensajeCuofManual("");
        limpiarSeleccionManualConfirmada();
        bloqueSeleccion.classList.add("pof-hidden");
        bloqueCargos.classList.add("pof-hidden");
        bloqueGuardarCarga.classList.add("pof-hidden");
        accionCuofPadronManual.innerHTML = `
            <div>${escaparHtml(mensaje || "Este CUOF tiene CUEANEXO. Debe cargarse desde padrón.")}</div>
            ${cueanexo ? `<div class="pof-field-hint">CUEANEXO: ${escaparHtml(cueanexo)}</div>` : ""}
            <div class="pof-actions pof-mt-2">
                <button type="button" class="pof-btn pof-btn-light" data-cuof-padron-actual>
                    Buscar en padrón
                </button>
            </div>
        `;
        accionCuofPadronManual.classList.remove("pof-hidden");
        ocultarBloqueCamposManual();
    }

    function irABusquedaPadronDesdeCuof(item) {
        const cueanexo = cueanexoDesdeItemManual(item);
        if (!cueanexo || cueanexo.length !== 9) {
            mostrarMensajeCuofManual("No se pudo obtener un CUEANEXO válido para buscar en padrón.");
            return;
        }
        activarModoPadron();
        cueBaseInput.value = "";
        anexoInput.value = "";
        cueanexoInput.value = cueanexo;
        mostrarEstado(estadoPadron, "warn", "Buscando en padrón con el CUEANEXO del CUOF seleccionado...");
        buscarPadron();
    }

    function limpiarSugerenciasCuofManual() {
        sugerenciasCuofManual.classList.add("pof-hidden");
        sugerenciasCuofManual.innerHTML = "";
        resultadosCuofManualActuales = [];
    }

    function asignarValorSelectManual(campo, valorTexto) {
        const select = manualInputs[campo];
        const valorSeleccion = String(valorTexto || "").trim();
        if (!select) {
            return;
        }
        if (!valorSeleccion) {
            select.value = "";
            if (window.jQuery && window.jQuery.fn.select2) {
                window.jQuery(select).trigger("change");
            }
            return;
        }
        const existe = Array.from(select.options).some(opcion => opcion.value === valorSeleccion);
        if (!existe) {
            select.value = "";
            if (window.jQuery && window.jQuery.fn.select2) {
                window.jQuery(select).trigger("change");
            }
            return;
        }
        select.value = valorSeleccion;
        if (window.jQuery && window.jQuery.fn.select2) {
            window.jQuery(select).trigger("change");
        }
    }

    function validarCampoTextoManual(campo) {
        const config = CAMPOS_TEXTO_MANUAL[campo];
        const valorTexto = String(manualInputs[campo].value || "").trim();
        if (esPlaceholderManual(valorTexto)) {
            return config.obligatorio
                ? { ok: false, mensaje: config.mensajeObligatorio }
                : { ok: true, valor: "" };
        }
        if (!textoSeguro(valorTexto, config.maxLength)) {
            return { ok: false, mensaje: "Revise la longitud y los caracteres permitidos." };
        }
        return { ok: true, valor: valorTexto };
    }

    function validarCampoCatalogoManual(campo) {
        const valorTexto = String(manualInputs[campo].value || "").trim();
        if (esPlaceholderManual(valorTexto)) {
            return { ok: true, valor: "" };
        }
        if (campo === "estado_localizacion_padron") {
            const estadoValido = ["Activo", "Baja"].some(
                estado => estado.toLowerCase() === valorTexto.toLowerCase()
            );
            return estadoValido
                ? { ok: true, valor: valorTexto }
                : { ok: false, mensaje: MENSAJES_CAMPOS_CATALOGO_MANUAL[campo] };
        }
        const opciones = new Set((catalogosManual && catalogosManual[campo]) || []);
        return opciones.has(valorTexto)
            ? { ok: true, valor: valorTexto }
            : { ok: false, mensaje: MENSAJES_CAMPOS_CATALOGO_MANUAL[campo] };
    }

    function obtenerCamposManualObligatoriosInvalidos() {
        const invalidos = [];
        Object.keys(CAMPOS_TEXTO_MANUAL).forEach(campo => {
            if (!validarCampoTextoManual(campo).ok) {
                invalidos.push(campo);
            }
        });
        CAMPOS_CATALOGO_MANUAL_VALIDABLES.forEach(campo => {
            if (!validarCampoCatalogoManual(campo).ok) {
                invalidos.push(campo);
            }
        });
        return invalidos;
    }

    function enfocarCampoManual(campo) {
        const input = manualInputs[campo];
        if (!input || input.disabled) {
            return;
        }
        if (window.jQuery && window.jQuery.fn.select2 && input.tagName === "SELECT" && window.jQuery(input).data("select2")) {
            window.jQuery(input).select2("open");
            return;
        }
        input.focus();
    }

    /**
     * Valida los campos obligatorios del ingreso manual antes de confirmar.
     *
     * - Rechaza vacíos y placeholders reales del selector.
     * - Devuelve el primer campo inválido para ubicar foco sin habilitar cargos.
     * - Reutiliza las mismas reglas para entradas nuevas y referencias históricas incompletas.
     */
    function validarCamposManualObligatorios() {
        const camposInvalidos = obtenerCamposManualObligatoriosInvalidos();
        if (!camposInvalidos.length) {
            return { ok: true, camposInvalidos: [] };
        }
        const primerCampo = camposInvalidos[0];
        const mensaje = primerCampo in CAMPOS_TEXTO_MANUAL
            ? CAMPOS_TEXTO_MANUAL[primerCampo].mensajeObligatorio
            : MENSAJES_CAMPOS_CATALOGO_MANUAL[primerCampo];
        return {
            ok: false,
            campo: primerCampo,
            mensaje,
            camposInvalidos
        };
    }

    function revalidarCampoManual(campo) {
        const resultado = campo in CAMPOS_TEXTO_MANUAL
            ? validarCampoTextoManual(campo)
            : validarCampoCatalogoManual(campo);
        if (resultado.ok) {
            limpiarErrorCampoManual(campo);
        } else {
            mostrarErrorCampoManual(campo, resultado.mensaje);
        }
        if (!obtenerCamposManualObligatoriosInvalidos().length && esErrorGeneralCamposManualActivo()) {
            mostrarEstado(estadoManual, "", "");
        }
    }

    function aplicarDatosCuofManual(item, mensaje) {
        if (!item) {
            return;
        }
        if (itemRequierePadron(item)) {
            mostrarMensajeCuofManual("");
            mostrarAccionCuofPadronManual(item);
            desbloquearCamposReferenciaManual();
            return;
        }
        limpiarAccionCuofPadronManual();
        cuofManualRequierePadron = null;
        datosCuofManualAutocompletados = item;
        manualInputs.cuof.value = obtenerCampo(item, ["cuof_loc", "cuof"]);
        manualInputs.cui.value = obtenerCampo(item, ["cui_loc", "cui"]);
        manualInputs.nombre.value = obtenerCampo(item, ["nom_est", "nombre_establecimiento"]);
        manualInputs.numero.value = obtenerCampo(item, ["nro_est", "numero_establecimiento"]);
        asignarValorSelectManual("region", obtenerCampo(item, ["region_loc", "region"]));
        asignarValorSelectManual("localidad", obtenerCampo(item, ["localidad"]));
        asignarValorSelectManual("departamento", obtenerCampo(item, ["departamento"]));
        asignarValorSelectManual("acronimo", obtenerCampo(item, ["acronimo"]));
        asignarValorSelectManual("ambito", obtenerCampo(item, ["ambito"]));
        asignarValorSelectManual("categoria", obtenerCampo(item, ["categoria"]));
        asignarValorSelectManual("jornada", obtenerCampo(item, ["jornada"]));
        asignarValorSelectManual("estado_localizacion_padron", obtenerCampo(item, ["estado_localizacion_padron", "estado_loc"]));
        limpiarSugerenciasCuofManual();
        mostrarBloqueCamposManual();
        const camposInvalidos = obtenerCamposManualObligatoriosInvalidos();
        if (camposInvalidos.length) {
            actualizarBloqueoCamposReferenciaManual(camposInvalidos);
            Object.keys(manualInputs).forEach(campo => {
                limpiarErrorCampoManual(campo);
            });
            camposInvalidos.forEach(campo => {
                const resultado = campo in CAMPOS_TEXTO_MANUAL
                    ? validarCampoTextoManual(campo)
                    : validarCampoCatalogoManual(campo);
                mostrarErrorCampoManual(campo, resultado.mensaje);
            });
            mostrarMensajeCuofManual("CUOF encontrado como referencia manual existente. Complete los campos obligatorios faltantes para continuar.");
            return;
        }
        limpiarErroresCamposManual();
        mostrarMensajeCuofManual(mensaje || "CUOF encontrado como referencia manual existente. Se usarán los datos ya cargados. Puede agregar cargos.");
        bloquearCamposReferenciaManual();
    }

    function renderizarSugerenciasCuofManual(resultados) {
        resultadosCuofManualActuales = Array.isArray(resultados) ? resultados : [];
        if (!resultadosCuofManualActuales.length) {
            limpiarSugerenciasCuofManual();
            return;
        }
        sugerenciasCuofManual.innerHTML = resultadosCuofManualActuales.map((item, index) => {
            const requierePadron = itemRequierePadron(item);
            const cueanexo = cueanexoDesdeItemManual(item);
            const resolucion = item.proyecto_resolucion ? ` · ${escaparHtml(item.proyecto_resolucion)}` : "";
            const detalle = [
                obtenerCampo(item, ["localidad"]),
                obtenerCampo(item, ["departamento"])
            ].filter(Boolean).map(escaparHtml).join(" · ");
            const textoAccion = requierePadron ? "Buscar en padrón" : "Usar datos manuales";
            const textoEstado = requierePadron
                ? "Este CUOF tiene CUEANEXO. Debe cargarse desde padrón."
                : "Referencia manual disponible para reutilizar.";
            const cueanexoInfo = requierePadron && cueanexo ? `<span>CUEANEXO: ${escaparHtml(cueanexo)}</span>` : "";
            return `
                <div class="pof-suggestion" data-cuof-manual-index="${index}">
                    <strong>CUOF encontrado en Proyecto Especial ${escaparHtml(item.proyecto_anio)} · ${escaparHtml(item.proyecto_nombre)}${resolucion}</strong>
                    ${detalle ? `<span>${detalle}</span>` : ""}
                    <span>${escaparHtml(textoEstado)}</span>
                    ${cueanexoInfo}
                    <button type="button" class="pof-btn pof-btn-light" data-cuof-manual-usar-index="${index}">
                        ${escaparHtml(textoAccion)}
                    </button>
                </div>
            `;
        }).join("");
        sugerenciasCuofManual.classList.remove("pof-hidden");
    }

    async function buscarCuofManualDinamico() {
        if (!cabeceraProyectoSeleccionada()) {
            mostrarMensajeCuofManual("Selecciona un Proyecto Especial POF antes de buscar CUOF.");
            return;
        }
        if (!catalogosManual || cargandoCatalogos) {
            return;
        }
        const cuof = manualInputs.cuof.value.trim();
        clearTimeout(temporizadorCuofManual);
        secuenciaBusquedaCuofManual += 1;
        const secuenciaActual = secuenciaBusquedaCuofManual;
        datosCuofManualAutocompletados = null;
        cuofManualRequierePadron = null;
        limpiarAccionCuofPadronManual();
        limpiarSeleccionManualConfirmada();
        ocultarBloqueCamposManual();
        limpiarCamposReferenciaManual();

        if (!cuof) {
            mostrarCargaCuofManual(false);
            limpiarSugerenciasCuofManual();
            mostrarMensajeCuofManual("");
            desbloquearCamposReferenciaManual();
            return;
        }

        if (!textoSeguro(cuof, 100)) {
            mostrarCargaCuofManual(false);
            limpiarSugerenciasCuofManual();
            mostrarMensajeCuofManual("El CUOF contiene caracteres no permitidos.");
            desbloquearCamposReferenciaManual();
            return;
        }

        desbloquearCamposReferenciaManual();
        mostrarCargaCuofManual(true);
        limpiarSugerenciasCuofManual();
        mostrarMensajeCuofManual(`Buscando CUOF en Proyectos Especiales ${PROYECTO_ESPECIAL.anio}...`);

        temporizadorCuofManual = setTimeout(async function () {
            try {
                const parametros = new URLSearchParams({
                    proyecto_especial_id: PROYECTO_ESPECIAL.id,
                    cuof: cuof
                });
                const response = await fetch(`${URL_BUSCAR_CUOF_MANUAL_PE}?${parametros.toString()}`);
                const data = await response.json();
                if (secuenciaActual !== secuenciaBusquedaCuofManual) {
                    return;
                }

                if (!response.ok || !data.ok) {
                    mostrarMensajeCuofManual("No se pudo verificar el CUOF. Intente nuevamente antes de continuar.");
                    limpiarSugerenciasCuofManual();
                    return;
                }

                if (!data.encontrado) {
                    mostrarMensajeCuofManual("No hay datos previos para este CUOF. Complete la referencia manual.");
                    limpiarSugerenciasCuofManual();
                    desbloquearCamposReferenciaManual();
                    mostrarBloqueCamposManual();
                    return;
                }

                const coincidencias = Array.isArray(data.coincidencias) ? data.coincidencias : [];
                const coincidenciaActual = coincidencias.find(item => item.misma_cabecera);
                if (coincidenciaActual) {
                    if (itemRequierePadron(coincidenciaActual)) {
                        limpiarSugerenciasCuofManual();
                        mostrarMensajeCuofManual("");
                        mostrarAccionCuofPadronManual(coincidenciaActual);
                    } else {
                        aplicarDatosCuofManual(
                            coincidenciaActual,
                            "CUOF encontrado como referencia manual existente. Se usarán los datos ya cargados. Puede agregar cargos."
                        );
                    }
                    return;
                }

                const coincidenciaPadron = coincidencias.find(itemRequierePadron);
                if (coincidenciaPadron) {
                    limpiarSugerenciasCuofManual();
                    mostrarMensajeCuofManual("");
                    mostrarAccionCuofPadronManual(coincidenciaPadron);
                    return;
                }

                renderizarSugerenciasCuofManual(coincidencias);
                mostrarMensajeCuofManual(`CUOF encontrado en otros Proyectos Especiales ${PROYECTO_ESPECIAL.anio}. Podés usar esos datos o completar manualmente.`);
                desbloquearCamposReferenciaManual();
                mostrarBloqueCamposManual();
            } catch (error) {
                if (secuenciaActual !== secuenciaBusquedaCuofManual) {
                    return;
                }
                mostrarMensajeCuofManual("No se pudo verificar el CUOF. Intente nuevamente antes de continuar.");
                limpiarSugerenciasCuofManual();
            } finally {
                if (secuenciaActual === secuenciaBusquedaCuofManual) {
                    mostrarCargaCuofManual(false);
                }
            }
        }, 300);
    }

    function textoSeguro(valorTexto, maxLength) {
        const texto = String(valorTexto || "").trim();
        if (texto.length > maxLength) {
            return false;
        }
        return !/[\x00-\x1f\x7f<>]/.test(texto);
    }

    function confirmarManual() {
        if (!exigirCabeceraProyectoSeleccionada(estadoManual)) {
            return;
        }
        if (!catalogosManual) {
            mostrarEstado(estadoManual, "error", "No se pudieron cargar los catálogos de ingreso manual.");
            return;
        }

        const cuof = manualInputs.cuof.value.trim();
        if (!cuof) {
            mostrarEstado(estadoManual, "error", "El CUOF es obligatorio para el ingreso manual controlado.");
            manualInputs.cuof.focus();
            return;
        }
        if (!textoSeguro(cuof, 100)) {
            mostrarEstado(estadoManual, "error", "El CUOF contiene caracteres no permitidos.");
            manualInputs.cuof.focus();
            return;
        }
        if (!textoSeguro(manualInputs.cui.value, 100) || !textoSeguro(manualInputs.nombre.value, 255) || !textoSeguro(manualInputs.numero.value, 100)) {
            mostrarEstado(estadoManual, "error", "Revisá los campos manuales: no pueden superar el máximo ni contener < o >.");
            return;
        }

        if (cuofManualRequierePadron) {
            mostrarEstado(estadoManual, "error", "Este CUOF tiene CUEANEXO. Debe cargarse desde padrón.");
            mostrarAccionCuofPadronManual(cuofManualRequierePadron);
            return;
        }
        if (!bloqueCamposManualVisible()) {
            mostrarEstado(estadoManual, "error", "Primero espere la validación del CUOF para continuar con el ingreso manual.");
            return;
        }
        const validacionManual = validarCamposManualObligatorios();
        if (!validacionManual.ok) {
            mostrarEstado(estadoManual, "error", "Revisá los campos informados antes de continuar.");
            Object.keys(manualInputs).forEach(campo => {
                limpiarErrorCampoManual(campo);
            });
            validacionManual.camposInvalidos.forEach(campo => {
                const resultado = campo in CAMPOS_TEXTO_MANUAL
                    ? validarCampoTextoManual(campo)
                    : validarCampoCatalogoManual(campo);
                mostrarErrorCampoManual(campo, resultado.mensaje);
            });
            enfocarCampoManual(validacionManual.campo);
            return;
        }
        limpiarErroresCamposManual();

        const cui = manualInputs.cui.value.trim() || SIN_INFORMACION;
        const nombre = manualInputs.nombre.value.trim() || SIN_INFORMACION;
        const numero = manualInputs.numero.value.trim() || SIN_INFORMACION;
        const region = manualInputs.region.value.trim() || SIN_INFORMACION;
        const localidad = manualInputs.localidad.value.trim() || SIN_INFORMACION;
        const departamento = manualInputs.departamento.value.trim() || SIN_INFORMACION;
        const acronimo = manualInputs.acronimo.value.trim() || SIN_INFORMACION;
        const ambito = manualInputs.ambito.value.trim() || SIN_INFORMACION;
        const categoria = manualInputs.categoria.value.trim() || SIN_INFORMACION;
        const jornada = manualInputs.jornada.value.trim() || SIN_INFORMACION;
        const estadoLocalizacion = manualInputs.estado_localizacion_padron.value.trim() || SIN_INFORMACION;

        modoPadronActual = MODO_MANUAL;
        padronSeleccionado = {
            cueanexo: "",
            padron_cueanexo: "",
            cue_anexo: "",
            cue: "",
            anexo: "",
            oferta: "",
            oferta_real: "",
            estado_oferta_padron: "",
            est_oferta: "",
            estado_establecimiento_padron: "",
            estado_est: "",
            cuof: cuof,
            cuof_loc: cuof,
            cui: cui,
            cui_loc: cui,
            nombre_establecimiento: nombre,
            nom_est: nombre,
            numero_establecimiento: numero,
            nro_est: numero,
            region: region,
            region_loc: region,
            localidad: localidad,
            departamento: departamento,
            acronimo: acronimo,
            ambito: ambito,
            categoria: categoria,
            jornada: jornada,
            estado_loc: estadoLocalizacion,
            estado_localizacion_padron: estadoLocalizacion,
            origen_datos: "MANUAL",
            estado_padron: "NO_ENCONTRADO"
        };

        cargosTemporales = [];
        limpiarCargoActual();
        bloqueManual.classList.add("pof-hidden");
        ocultarBloqueCamposManual();
        bloqueSeleccion.classList.remove("pof-hidden");
        bloqueCargos.classList.remove("pof-hidden");
        renderizarSeleccion();
        renderizarTablaCargos();
        mostrarEstado(estadoManual, "ok", "Ingreso manual controlado preparado. Podés continuar con la carga de cargos.");
    }

    /**
     * Muestra la localización o referencia confirmada antes de cargar cargos.
     *
     * - Usa resumen de oferta para PADRON y resumen de referencia para MANUAL_CONTROLADO.
     * - Evita mostrar datos de oferta cuando la referencia es manual.
     * - Incluye la acción de cambio que limpia cargos dependientes de la selección anterior.
     */
    function renderizarSeleccion() {
        if (!padronSeleccionado) {
            detalleSeleccion.innerHTML = "";
            return;
        }
        const esManual = modoPadronActual === MODO_MANUAL;
        const titulo = esManual ? "Referencia manual seleccionada" : "Oferta seleccionada";
        const origen = esManual ? "Manual" : "Padrón";
        const datoPrincipal = esManual
            ? obtenerLineaPrincipalManual(padronSeleccionado)
            : obtenerLineaPrincipalOferta(padronSeleccionado, "");
        const detalle = esManual
            ? renderizarDetalleManual(padronSeleccionado)
            : renderizarDetallePadron(padronSeleccionado);
        const estado = esManual ? "" : renderizarBadgeEstadoOferta(padronSeleccionado);
        const accion = esManual ? "Cambiar referencia" : "Cambiar oferta";
        const accionModo = esManual ? "manual" : "padron";
        detalleSeleccion.innerHTML = `
            <div class="pof-offer-selected-card">
                <div class="pof-offer-selected-head">
                    <span class="pof-offer-selected-title">✅ ${escaparHtml(titulo)}</span>
                </div>
                <div class="pof-offer-card-main">
                    <span class="pof-offer-selected-main">${valorHtml(datoPrincipal)}</span>
                    ${estado}
                </div>
                <div class="pof-offer-selected-meta">${escaparHtml(obtenerLineaSecundariaLocalizacion(padronSeleccionado))}</div>
                <div class="pof-offer-selected-origin">Origen: ${escaparHtml(origen)}</div>
                <div class="pof-offer-detail-compact pof-offer-detail-grid pof-mt-2">
                    ${detalle}
                </div>
            </div>

            <div class="pof-actions pof-mt-2 pof-offer-selected-actions">
                <button type="button" class="pof-btn pof-btn-light" data-cambiar-seleccion="${accionModo}">
                    ${escaparHtml(accion)}
                </button>
            </div>
        `;
    }

    function limpiarSeleccionConfirmada() {
        limpiarSeleccionManualConfirmada();
    }

    function cambiarOfertaSeleccionada() {
        limpiarSeleccionConfirmada();
        modoPadronActual = MODO_PADRON;
        bloqueManual.classList.add("pof-hidden");
        bloquePadron.classList.remove("pof-hidden");
        if (resultadosPadronActuales.length) {
            renderizarResultadosPadron(resultadosPadronActuales, true);
        } else {
            resultadosPadron.classList.add("pof-hidden");
        }
        mostrarEstado(estadoPadron, "warn", "Seleccioná nuevamente una oferta del padrón.");
        cueBaseInput.focus();
    }

    function cambiarReferenciaManual() {
        limpiarSeleccionConfirmada();
        modoPadronActual = MODO_MANUAL;
        resultadosPadron.classList.add("pof-hidden");
        bloquePadron.classList.add("pof-hidden");
        bloqueManual.classList.remove("pof-hidden");
        mostrarBloqueCamposManual();
        limpiarAccionCuofPadronManual();
        mostrarEstado(estadoManual, "warn", "Revisá la referencia manual y confirmala nuevamente.");
        manualInputs.cuof.focus();
    }

    function mostrarMensajeCeic(mensaje) {
        mensajeCeic.textContent = mensaje || "";
        mensajeCeic.classList.toggle("pof-hidden", !mensaje);
    }

    function mostrarCargaCeic(cargando) {
        ceicLoading.classList.toggle("pof-hidden", !cargando);
        ceicLoading.setAttribute("aria-hidden", cargando ? "false" : "true");
    }

    /**
     * Restablece el formulario de un cargo luego de agregarlo o cambiar de origen.
     *
     * - Cancela búsquedas CEIC pendientes y evita que una respuesta anterior repueble el formulario.
     * - Restituye los valores iniciales de cantidad, unidad, total y observación.
     * - Conserva intacta la lista temporal y la localización ya seleccionada.
     */
    function limpiarCargoActual() {
        clearTimeout(temporizadorCeic);
        secuenciaBusquedaCeic += 1;
        ceicBusqueda.value = "";
        ceicSeleccionado.value = "";
        cargoSeleccionado.value = "";
        puntosCargo.value = "";
        totalCargo.value = "0";
        cantidadCargo.value = "1";
        unidadCargo.value = "CARGO";
        unidadAutoSeleccionadaPorCeic = false;
        observacionCargo.value = "";
        controlObservacionCargo.ocultar();
        sugerenciasCeic.classList.add("pof-hidden");
        sugerenciasCeic.innerHTML = "";
        mostrarMensajeCeic("");
        mostrarCargaCeic(false);
    }

    /**
     * Ajusta la unidad al CEIC seleccionado sin pisar una elección manual posterior.
     *
     * - Usa el detector común de cargos HORA/HORAS para asignar Horas Cátedra.
     * - Restaura Cargo al pasar de una unidad automática de horas a un cargo común.
     * - Mantiene una unidad elegida manualmente por la persona usuaria.
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

    function calcularCargoActual() {
        const cantidad = Number(cantidadCargo.value || "0");
        const puntos = Number(puntosCargo.value || "0");
        totalCargo.value = (cantidad * puntos).toFixed(2);
    }

    /**
     * Limpia los datos derivados del CEIC cuando el texto deja de representar la selección vigente.
     *
     * - Conserva cantidad y observación, como la edición actual de Reunida.
     * - Restablece Cargo solo si Horas Cátedra fue asignada automáticamente.
     * - Evita que nombre, puntos o total de un CEIC anterior queden visibles.
     */
    function limpiarSeleccionCeicActual() {
        ceicSeleccionado.value = "";
        cargoSeleccionado.value = "";
        puntosCargo.value = "";
        totalCargo.value = "0";

        if (unidadAutoSeleccionadaPorCeic) {
            unidadCargo.value = "CARGO";
            unidadAutoSeleccionadaPorCeic = false;
        }
    }

    /**
     * Carga una única vez el catálogo de CEIC activos de Proyecto Especial.
     *
     * - Usa el endpoint de catálogo sin filtros por nivel.
     * - Reutiliza la promesa pendiente para no duplicar solicitudes concurrentes.
     * - Mantiene el catálogo solo en memoria de la pantalla actual.
     */
    async function cargarCatalogoCeic() {
        if (catalogoCeicCargado) {
            return true;
        }

        if (catalogoCeicPromise) {
            return catalogoCeicPromise;
        }

        catalogoCeicPromise = (async function () {
            try {
                const response = await fetch(URL_CATALOGO_CEIC_PE, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await response.json();
                const payload = data.data || data;

                if (!response.ok || !data.ok) {
                    catalogoCeic = [];
                    return false;
                }

                catalogoCeic = Array.isArray(payload.resultados) ? payload.resultados : [];
                catalogoCeicCargado = true;
                return true;
            } catch (error) {
                catalogoCeic = [];
                return false;
            } finally {
                catalogoCeicPromise = null;
            }
        })();

        return catalogoCeicPromise;
    }

    /**
     * Filtra en memoria los CEIC activos por el prefijo ingresado.
     *
     * - Mantiene el orden entregado por el catálogo oficial.
     * - No aplica filtros por nivel ni modos exclusivos de Reunida.
     * - Limita las sugerencias visibles al máximo usado por Reunida.
     */
    function filtrarCatalogoCeic(query) {
        return catalogoCeic
            .filter(item => String(item.ceic || "").startsWith(query))
            .slice(0, LIMITE_RESULTADOS_CEIC);
    }

    /**
     * Busca CEIC localmente luego de preparar el catálogo activo una sola vez.
     *
     * - Normaliza el código a números de hasta tres dígitos.
     * - Conserva el debounce y la protección contra resultados vencidos.
     * - No realiza consultas por cada tecla luego de cargar el catálogo.
     */
    function buscarCeicDinamico() {
        const valorOriginal = ceicBusqueda.value;
        const query = limpiarDigitos(valorOriginal, 3);
        if (valorOriginal !== query) {
            ceicBusqueda.value = query;
        }
        limpiarSeleccionCeicActual();
        clearTimeout(temporizadorCeic);
        secuenciaBusquedaCeic += 1;
        const secuenciaActual = secuenciaBusquedaCeic;

        if (!query) {
            mostrarCargaCeic(false);
            sugerenciasCeic.classList.add("pof-hidden");
            sugerenciasCeic.innerHTML = "";
            mostrarMensajeCeic(
                valorOriginal !== query
                    ? "Ingresá solo números, hasta 3 dígitos."
                    : "Ingresá un CEIC para buscar el cargo."
            );
            return;
        }

        mostrarCargaCeic(true);
        temporizadorCeic = setTimeout(async function () {
            try {
                const catalogoDisponible = await cargarCatalogoCeic();
                if (secuenciaActual !== secuenciaBusquedaCeic) {
                    return;
                }
                if (!catalogoDisponible) {
                    sugerenciasCeic.classList.add("pof-hidden");
                    sugerenciasCeic.innerHTML = "";
                    mostrarMensajeCeic("No se pudo cargar el catálogo de CEIC activos.");
                    return;
                }
                renderizarSugerenciasCeic(filtrarCatalogoCeic(query));
            } catch (error) {
                if (secuenciaActual !== secuenciaBusquedaCeic) {
                    return;
                }
                sugerenciasCeic.classList.add("pof-hidden");
                sugerenciasCeic.innerHTML = "";
                mostrarMensajeCeic("No se pudo cargar el catálogo de CEIC activos.");
            } finally {
                if (secuenciaActual === secuenciaBusquedaCeic) {
                    mostrarCargaCeic(false);
                }
            }
        }, 120);
    }

    function renderizarSugerenciasCeic(resultados) {
        if (!resultados.length) {
            sugerenciasCeic.classList.add("pof-hidden");
            sugerenciasCeic.innerHTML = "";
            mostrarMensajeCeic("No se encontró un CEIC activo.");
            return;
        }
        sugerenciasCeic.innerHTML = resultados.map(item => `
            <div class="pof-suggestion"
                 data-ceic="${escaparHtml(item.ceic)}"
                 data-cargo="${escaparHtml(item.cargo || item.descripcion_ceic || "")}"
                 data-puntos="${escaparHtml(item.puntos || "0")}">
                <strong>${escaparHtml(item.ceic)}</strong> - ${escaparHtml(item.cargo || item.descripcion_ceic || "")}
                ${item.nivel ? `<span>${escaparHtml(item.nivel)}</span>` : ""}
            </div>
        `).join("");
        sugerenciasCeic.classList.remove("pof-hidden");
    }

    /**
     * Completa el cargo actual desde una sugerencia CEIC de Proyecto Especial.
     *
     * - Conserva la búsqueda abierta para cualquier CEIC activo del catálogo propio.
     * - Invalida respuestas pendientes antes de guardar los datos oficiales seleccionados.
     * - Aplica la misma regla automática de unidad que la carga de Reunida.
     */
    function seleccionarCeic(opcion) {
        const ceic = opcion.dataset.ceic;
        const cargo = opcion.dataset.cargo;
        const puntos = opcion.dataset.puntos;
        ceicBusqueda.value = ceic;
        clearTimeout(temporizadorCeic);
        secuenciaBusquedaCeic += 1;
        ceicSeleccionado.value = ceic;
        cargoSeleccionado.value = cargo;
        puntosCargo.value = puntos;
        aplicarUnidadPorCargoSeleccionado(cargo);
        calcularCargoActual();
        sugerenciasCeic.classList.add("pof-hidden");
        sugerenciasCeic.innerHTML = "";
        mostrarCargaCeic(false);
        mostrarMensajeCeic("");
    }

    /**
     * Devuelve una cantidad temporal válida para los cálculos y la tabla de cargos.
     *
     * - Acepta únicamente enteros positivos.
     * - Evita que valores inválidos alteren totales temporales.
     * - Mantiene el mismo criterio que la carga de Reunida.
     */
    function obtenerCantidadCargoTemporal(cargo) {
        const cantidad = Number(cargo && cargo.cantidad);
        return Number.isInteger(cantidad) && cantidad > 0 ? cantidad : 0;
    }

    function calcularTotalCargoTemporal(cargo) {
        return obtenerCantidadCargoTemporal(cargo) * Number(cargo && cargo.puntos_asignados || 0);
    }

    /**
     * Recalcula y sincroniza el total de un cargo temporal a partir de cantidad y puntos.
     *
     * - Conserva dos decimales en el valor persistido temporalmente.
     * - No modifica nombre, CEIC, unidad ni observación.
     * - Centraliza el cálculo usado por duplicados y edición de cantidades.
     */
    function actualizarTotalCargoTemporal(cargo) {
        if (!cargo) {
            return "0.00";
        }

        cargo.total = calcularTotalCargoTemporal(cargo).toFixed(2);
        return cargo.total;
    }

    /**
     * Agrega o consolida un cargo temporal validado desde la selección CEIC.
     *
     * - Usa CEIC y unidad como clave de duplicado.
     * - Mantiene datos oficiales ya seleccionados y completa una observación vacía.
     * - Restablece el formulario solo después de actualizar la lista temporal.
     */
    function agregarCargoALista() {
        if (!exigirCabeceraProyectoSeleccionada(estadoGuardado)) {
            return;
        }
        if (!padronSeleccionado) {
            mostrarEstado(estadoGuardado, "error", "Primero confirmá el origen de la localización.");
            return;
        }
        calcularCargoActual();
        if (!ceicSeleccionado.value) {
            mostrarMensajeCeic("Ingresá un CEIC para buscar el cargo.");
            return;
        }
        const nombreCargo = cargoSeleccionado.value.trim();
        const cantidad = Number(cantidadCargo.value || "0");
        const puntos = Number(puntosCargo.value || "");
        if (!nombreCargo) {
            mostrarMensajeCeic("Ingresá un CEIC para buscar el cargo.");
            return;
        }
        if (!Number.isInteger(cantidad) || cantidad <= 0) {
            mostrarEstado(estadoGuardado, "error", "La cantidad debe ser un número entero mayor a 0.");
            return;
        }
        if (!puntosCargo.value.trim() || !Number.isFinite(puntos) || puntos < 0) {
            mostrarEstado(estadoGuardado, "error", "Los puntos asignados son obligatorios y deben ser un número mayor o igual a 0.");
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
            total: (cantidad * puntos).toFixed(2),
        };
        const cargoExistente = cargosTemporales.find(cargo => (
            claveCargoTemporal(cargo.ceic, cargo.unidad_cantidad) === claveCargoTemporal(cargoNuevo.ceic, cargoNuevo.unidad_cantidad)
        ));
        let mensajeDuplicado = "";
        if (cargoExistente) {
            cargoExistente.cantidad = String(Number(cargoExistente.cantidad || "0") + cantidad);
            actualizarTotalCargoTemporal(cargoExistente);
            if (!cargoExistente.observacion && cargoNuevo.observacion) {
                cargoExistente.observacion = cargoNuevo.observacion;
            }
            mensajeDuplicado = "Este CEIC ya estaba cargado con la misma unidad. Se incrementó la cantidad sin crear una fila duplicada.";
        } else {
            cargosTemporales.push(cargoNuevo);
        }
        limpiarCargoActual();
        renderizarTablaCargos();
        mostrarEstado(estadoGuardado, mensajeDuplicado ? "warn" : "", mensajeDuplicado);
    }

    /**
     * Ordena los cargos temporales por CEIC y unidad para una tabla estable.
     *
     * - Prioriza el código CEIC numérico ascendente.
     * - Desempata por unidad, como la carga de Reunida.
     * - No altera cantidades, puntos ni observaciones.
     */
    function ordenarCargosTemporales() {
        cargosTemporales.sort((cargoA, cargoB) => {
            const diferenciaCeic = Number(cargoA.ceic || 0) - Number(cargoB.ceic || 0);
            if (diferenciaCeic !== 0) {
                return diferenciaCeic;
            }
            return String(cargoA.unidad_cantidad || "").localeCompare(
                String(cargoB.unidad_cantidad || "")
            );
        });
    }

    /**
     * Quita un cargo temporal y actualiza la tabla y el estado de guardado.
     *
     * - Ignora índices fuera del arreglo temporal.
     * - Recalcula la disponibilidad de guardado mediante el renderizado existente.
     * - Limpia mensajes previos para no mostrar estados obsoletos.
     */
    function quitarCargoTemporal(index) {
        if (!Number.isInteger(index) || index < 0 || index >= cargosTemporales.length) {
            return;
        }

        cargosTemporales.splice(index, 1);
        renderizarTablaCargos();
        mostrarEstado(estadoGuardado, "", "");
    }

    /**
     * Actualiza una cantidad temporal cuando cumple la validación de entero positivo.
     *
     * - Recalcula el total del cargo antes de renderizar la tabla.
     * - Devuelve falso para restaurar visualmente valores inválidos.
     * - No modifica la unidad ni los datos oficiales del CEIC.
     */
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
        mostrarEstado(estadoGuardado, "", "");
        return true;
    }

    function renderizarInfoGeneralCargos() {
        const etiquetaReferencia = modoPadronActual === MODO_MANUAL ? "Referencia" : "Oferta";
        const valorReferencia = modoPadronActual === MODO_MANUAL
            ? obtenerCampo(padronSeleccionado, ["nom_est", "nombre_establecimiento"])
            : obtenerCampo(padronSeleccionado, ["oferta"]);
        cargoInfoGeneral.innerHTML = `
            <div class="pof-cargos-info-item">
                <span>Proyecto Especial</span>
                <strong>${escaparHtml(PROYECTO_ESPECIAL.anio)} - ${escaparHtml(PROYECTO_ESPECIAL.nombre)}</strong>
            </div>
            <div class="pof-cargos-info-item">
                <span>Origen</span>
                <strong>${modoPadronActual === MODO_MANUAL ? "Manual" : "PADRON"}</strong>
            </div>
            <div class="pof-cargos-info-item">
                <span>CUOF</span>
                <strong>${valorHtml(obtenerCampo(padronSeleccionado, ["cuof_loc", "cuof"]))}</strong>
            </div>
            <div class="pof-cargos-info-item">
                <span>${escaparHtml(etiquetaReferencia)}</span>
                <strong>${valorHtml(valorReferencia)}</strong>
            </div>
        `;
    }

    function renderizarTotalPuntosCargos() {
        const total = cargosTemporales.reduce((acumulado, cargo) => acumulado + calcularTotalCargoTemporal(cargo), 0);
        cargoTotalPuntos.innerHTML = `
            <span>Total puntos</span>
            <strong>${escaparHtml(total.toFixed(2))}</strong>
        `;
    }

    function actualizarEstadoBotonGuardar() {
        const puedeGuardar = cabeceraProyectoSeleccionada() && padronSeleccionado && cargosTemporales.length > 0 && !guardandoCarga;
        btnGuardarCarga.disabled = !puedeGuardar;
        bloqueGuardarCarga.classList.toggle("pof-hidden", !padronSeleccionado);
    }

    function renderizarTablaCargos() {
        if (!cargosTemporales.length) {
            cargoListaWrapper.classList.add("pof-hidden");
            cargoInfoGeneral.innerHTML = "";
            cargoTotalPuntos.textContent = "";
            tablaCargos.innerHTML = `
                <tr>
                    <td colspan="8" class="pof-empty-row">Todavía no agregaste cargos.</td>
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
                    <input type="number" class="pof-cargo-quantity-input" min="1" step="1" value="${escaparHtml(obtenerCantidadCargoTemporal(cargo) || 1)}" data-cargo-quantity-index="${index}" aria-label="Cantidad del cargo ${escaparHtml(cargo.cargo)}">
                </td>
                <td>${valorHtml(cargo.unidad_texto)}</td>
                <td>${valorHtml(cargo.puntos_asignados)}</td>
                <td>${valorHtml(calcularTotalCargoTemporal(cargo).toFixed(2))}</td>
                <td class="pof-cargo-observation-cell">${cargo.observacion ? escaparHtml(cargo.observacion) : "-"}</td>
                <td class="pof-cargo-action-cell">
                    <button type="button" class="pof-cargo-remove-btn" title="Quitar cargo" aria-label="Quitar cargo" data-cargo-remove-index="${index}">
                        &times;
                    </button>
                </td>
            </tr>
        `).join("");
        actualizarEstadoBotonGuardar();
    }

    function armarPayloadGuardado() {
        return {
            cabecera_tipo: "PROYECTO_ESPECIAL",
            proyecto_especial_id: PROYECTO_ESPECIAL.id,
            tipo_operacion: "ALTA",
            modo_padron: modoPadronActual,
            padron: padronSeleccionado,
            cargos: cargosTemporales.map(cargo => ({
                ceic: cargo.ceic,
                observacion: cargo.observacion || "",
                cantidad: cargo.cantidad,
                unidad_cantidad: cargo.unidad_cantidad,
            })),
        };
    }

    function abrirConfirmacionCarga() {
        if (!exigirCabeceraProyectoSeleccionada(estadoGuardado)) {
            actualizarEstadoBotonGuardar();
            return;
        }
        if (!padronSeleccionado || !cargosTemporales.length) {
            mostrarEstado(estadoGuardado, "error", "Confirmá el origen y agregá al menos un cargo.");
            actualizarEstadoBotonGuardar();
            return;
        }
        ordenarCargosTemporales();
        tablaConfirmarCarga.innerHTML = cargosTemporales.map(cargo => `
            <tr>
                <td>${valorHtml(cargo.ceic)}</td>
                <td>${valorHtml(cargo.cargo)}</td>
                <td>${valorHtml(cargo.cantidad)}</td>
                <td>${valorHtml(cargo.unidad_texto)}</td>
                <td>${valorHtml(cargo.puntos_asignados)}</td>
                <td>${valorHtml(calcularTotalCargoTemporal(cargo).toFixed(2))}</td>
                <td>${cargo.observacion ? escaparHtml(cargo.observacion) : "-"}</td>
            </tr>
        `).join("");
        const total = cargosTemporales.reduce((acumulado, cargo) => acumulado + calcularTotalCargoTemporal(cargo), 0);
        modalCargoTotalPuntos.innerHTML = `
            <span>Total puntos</span>
            <strong>${escaparHtml(total.toFixed(2))}</strong>
        `;
        modalConfirmarCarga.classList.remove("pof-hidden");
        modalConfirmarCarga.setAttribute("aria-hidden", "false");
    }

    function cerrarConfirmacionCarga() {
        modalConfirmarCarga.classList.add("pof-hidden");
        modalConfirmarCarga.setAttribute("aria-hidden", "true");
    }

    function construirUrlDetalleGuardado(data) {
        const params = new URLSearchParams();
        params.set("cabecera_tipo", "PROYECTO_ESPECIAL");
        params.set("proyecto_especial_id", (data && data.proyecto_especial_id) || PROYECTO_ESPECIAL.id);
        const cueanexo = obtenerCampo(padronSeleccionado, ["padron_cueanexo", "cueanexo", "cue_anexo"]);
        const cuof = obtenerCampo(padronSeleccionado, ["cuof_loc", "cuof"]);
        if (cueanexo) {
            params.set("cueanexo", cueanexo);
        }
        if (cuof) {
            params.set("cuof", cuof);
        }
        return `${URL_DETALLE_REUNIDA}?${params.toString()}`;
    }

    function mostrarExitoGuardado(data) {
        estadoGuardado.innerHTML = "";
        estadoGuardado.className = "pof-status ok";
        const mensaje = document.createElement("div");
        mensaje.textContent = data.mensaje || "Carga guardada correctamente.";
        estadoGuardado.appendChild(mensaje);
        const acciones = document.createElement("div");
        acciones.className = "pof-actions pof-mt-2";
        const linkDetalle = document.createElement("a");
        linkDetalle.className = "pof-btn pof-btn-light";
        linkDetalle.href = construirUrlDetalleGuardado(data);
        linkDetalle.textContent = "Ver en detalle del proyecto";
        acciones.appendChild(linkDetalle);
        estadoGuardado.appendChild(acciones);
    }

    async function guardarCarga() {
        if (guardandoCarga) {
            return;
        }
        if (!cabeceraProyectoSeleccionada()) {
            mostrarEstado(estadoGuardado, "error", "Debe seleccionar un Proyecto Especial POF valido.");
            return;
        }
        if (!padronSeleccionado || !cargosTemporales.length) {
            mostrarEstado(estadoGuardado, "error", "Confirmá el origen y agregá al menos un cargo.");
            return;
        }
        guardandoCarga = true;
        btnGuardarCarga.disabled = true;
        btnConfirmarGuardarCarga.disabled = true;
        mostrarEstado(estadoGuardado, "warn", "Guardando carga POF...");
        try {
            const response = await fetch(URL_GUARDAR_CARGA_PE, {
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
                mostrarEstado(estadoGuardado, "error", detalleErrores || data.mensaje || "No se pudo guardar la carga.");
                return;
            }
            cerrarConfirmacionCarga();
            cargosTemporales = [];
            renderizarTablaCargos();
            mostrarExitoGuardado(data);
        } catch (error) {
            mostrarEstado(estadoGuardado, "error", "No se pudo guardar la carga.");
        } finally {
            guardandoCarga = false;
            btnConfirmarGuardarCarga.disabled = false;
            actualizarEstadoBotonGuardar();
        }
    }

    btnModoPadron.addEventListener("click", activarModoPadron);
    btnModoManual.addEventListener("click", activarModoManual);
    btnBuscarPadron.addEventListener("click", buscarPadron);
    btnConfirmarManual.addEventListener("click", confirmarManual);
    btnAgregarCargoLista.addEventListener("click", agregarCargoALista);
    btnValidarCabeceraProyecto.addEventListener("click", validarCabeceraProyecto);
    btnCambiarCabecera.addEventListener("click", habilitarCambioCabecera);
    proyectoEspecialSelect.addEventListener("change", function () {
        if (!cabeceraEditable) {
            return;
        }
        proyectoEspecialId.value = "";
        limpiarErrorCabeceraProyecto();
        actualizarDisponibilidadFlujoPorCabecera();
    });
    btnGuardarCarga.addEventListener("click", abrirConfirmacionCarga);
    btnConfirmarGuardarCarga.addEventListener("click", guardarCarga);
    cueBaseInput.addEventListener("input", actualizarCueanexoDesdePartes);
    anexoInput.addEventListener("input", actualizarCueanexoDesdePartes);
    cueanexoInput.addEventListener("input", function () {
        cueanexoInput.value = limpiarDigitos(cueanexoInput.value, 9);
    });
    manualInputs.cuof.addEventListener("input", buscarCuofManualDinamico);
    Object.keys(manualInputs).forEach(campo => {
        const input = manualInputs[campo];
        const evento = input.tagName === "SELECT" ? "change" : "input";
        input.addEventListener(evento, function () {
            revalidarCampoManual(campo);
        });
    });
    accionCuofPadronManual.addEventListener("click", function (event) {
        const boton = event.target.closest("[data-cuof-padron-actual]");
        if (!boton) {
            return;
        }
        irABusquedaPadronDesdeCuof(cuofManualRequierePadron);
    });
    ceicBusqueda.addEventListener("input", buscarCeicDinamico);
    cantidadCargo.addEventListener("input", calcularCargoActual);
    unidadCargo.addEventListener("change", function () {
        unidadAutoSeleccionadaPorCeic = false;
        calcularCargoActual();
    });
    btnMostrarObservacion.addEventListener("click", () => controlObservacionCargo.mostrar());
    btnQuitarObservacion.addEventListener("click", () => controlObservacionCargo.ocultar(true));
    sugerenciasCeic.addEventListener("click", function (event) {
        const opcion = event.target.closest(".pof-suggestion");
        if (opcion) {
            seleccionarCeic(opcion);
        }
    });
    sugerenciasCuofManual.addEventListener("click", function (event) {
        const boton = event.target.closest("[data-cuof-manual-usar-index]");
        const opcion = event.target.closest("[data-cuof-manual-index]");
        const elemento = boton || opcion;
        if (!elemento) {
            return;
        }
        const index = Number(elemento.dataset.cuofManualUsarIndex || elemento.dataset.cuofManualIndex);
        if (!Number.isInteger(index) || !resultadosCuofManualActuales[index]) {
            return;
        }
        const item = resultadosCuofManualActuales[index];
        if (itemRequierePadron(item)) {
            irABusquedaPadronDesdeCuof(item);
            return;
        }
        aplicarDatosCuofManual(
            item,
            "Datos institucionales del CUOF precargados. Puede continuar con la carga manual."
        );
    });
    resultadosPadron.addEventListener("click", function (event) {
        const toggle = event.target.closest("[data-oferta-toggle-index]");
        if (toggle) {
            alternarOfertaPadron(Number(toggle.dataset.ofertaToggleIndex));
            return;
        }
        const boton = event.target.closest("[data-seleccionar-oferta-index]");
        if (boton) {
            seleccionarOfertaPadron(Number(boton.dataset.seleccionarOfertaIndex));
        }
    });
    detalleSeleccion.addEventListener("click", function (event) {
        const boton = event.target.closest("[data-cambiar-seleccion]");
        if (!boton) {
            return;
        }
        if (boton.dataset.cambiarSeleccion === "manual") {
            cambiarReferenciaManual();
            return;
        }
        cambiarOfertaSeleccionada();
    });
    tablaCargos.addEventListener("click", function (event) {
        const boton = event.target.closest("[data-cargo-remove-index]");
        if (!boton) {
            return;
        }
        quitarCargoTemporal(Number(boton.dataset.cargoRemoveIndex));
    });
    tablaCargos.addEventListener("change", function (event) {
        const input = event.target.closest("[data-cargo-quantity-index]");
        if (!input) {
            return;
        }
        const index = Number(input.dataset.cargoQuantityIndex);
        if (!actualizarCantidadCargoTemporal(index, input.value)) {
            renderizarTablaCargos();
        }
    });
    document.querySelectorAll("[data-cancelar-confirmacion-carga]").forEach(boton => {
        boton.addEventListener("click", cerrarConfirmacionCarga);
    });
    modalConfirmarCarga.addEventListener("click", function (event) {
        if (event.target === modalConfirmarCarga) {
            cerrarConfirmacionCarga();
        }
    });
    inicializarDependenciasSelect2Manual();
    inicializarCabeceraProyecto();
    renderizarTablaCargos();
