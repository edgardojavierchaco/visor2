(function () {
  "use strict";

  const api = window.pofApi || null;
  const modal = document.querySelector("[data-cargo-gestion-modal]");

  if (!api || !modal) {
    return;
  }

  const detalleUrlBase = modal.dataset.detalleUrlBase || "";
  const ofertasCatalogoUrlBase = modal.dataset.ofertasCatalogoUrlBase || "";
  const modificarUrlBase = modal.dataset.modificarUrlBase || "";
  const eliminarUrlBase = modal.dataset.eliminarUrlBase || "";
  const historialCargoUrlBase = modal.dataset.historialCargoUrlBase || "";
  const historialLocalizacionUrlBase = modal.dataset.historialLocalizacionUrlBase || "";
  const historialZonaUrlBase = modal.dataset.historialZonaUrlBase || "";
  const historialObservacionUrl = modal.dataset.historialObservacionUrl || "";
  const zonaCatalogoUrl = modal.dataset.zonaCatalogoUrl || "";
  const anexoCatalogoUrl = modal.dataset.anexoCatalogoUrl || "";
  const anexoCatalogoCrearUrl = modal.dataset.anexoCatalogoCrearUrl || "";
  const anexoAsociacionesUrl = modal.dataset.anexoAsociacionesUrl || "";
  const anexoHistorialUrl = modal.dataset.anexoHistorialUrl || "";
  const successMode = modal.dataset.successMode || "reload";

  if (
    !detalleUrlBase ||
    !ofertasCatalogoUrlBase ||
    !modificarUrlBase ||
    !eliminarUrlBase ||
    !historialCargoUrlBase ||
    !historialLocalizacionUrlBase ||
    !historialZonaUrlBase ||
    !historialObservacionUrl ||
    !zonaCatalogoUrl ||
    !anexoCatalogoUrl ||
    !anexoCatalogoCrearUrl ||
    !anexoAsociacionesUrl ||
    !anexoHistorialUrl
  ) {
    return;
  }

  const form = document.getElementById("formGestionCargo");
  const estado = document.getElementById("estadoGestionCargo");
  const pestaniasPrincipales = Array.from(
    modal.querySelectorAll("[data-cargo-main-tab]"),
  );
  const panelesPrincipales = Array.from(
    modal.querySelectorAll("[data-cargo-main-panel]"),
  );
  const pestaniasHistorial = Array.from(
    modal.querySelectorAll("[data-cargo-history-tab]"),
  );
  const panelesHistorial = Array.from(
    modal.querySelectorAll("[data-cargo-history-panel]"),
  );
  const filtrosHistorialCargo = Array.from(
    modal.querySelectorAll("[data-cargo-history-filter]"),
  );
  const historialCargoMovimientosWrap = document.getElementById(
    "historialCargoMovimientosWrap",
  );
  const historialCargoObservacionesWrap = document.getElementById(
    "historialCargoObservacionesWrap",
  );
  const historialLocalizacionLabel = document.getElementById(
    "cargoHistorialLocalizacionLabel",
  );
  const estadoHistorialCargo = document.getElementById("estadoHistorialCargo");
  const resumenHistorialCargo = document.getElementById("resumenHistorialCargo");
  const contenidoHistorialCargo = document.getElementById("contenidoHistorialCargo");
  const estadoHistorialLocalizacion = document.getElementById("estadoHistorialLocalizacion");
  const resumenHistorialLocalizacion = document.getElementById("resumenHistorialLocalizacion");
  const contenidoHistorialLocalizacion = document.getElementById("contenidoHistorialLocalizacion");
  const estadoHistorialZona = document.getElementById("estadoHistorialZona");
  const resumenHistorialZona = document.getElementById("resumenHistorialZona");
  const contenidoHistorialZona = document.getElementById("contenidoHistorialZona");
  const estadoHistorialAnexo = document.getElementById("estadoHistorialAnexo");
  const resumenHistorialAnexo = document.getElementById("resumenHistorialAnexo");
  const contenidoHistorialAnexo = document.getElementById("contenidoHistorialAnexo");
  const estadoHistorialObservacion = document.getElementById("estadoHistorialObservacion");
  const resumenHistorialObservacion = document.getElementById("resumenHistorialObservacion");
  const contenidoHistorialObservacion = document.getElementById("contenidoHistorialObservacion");
  const pestaniasObservacionInline = Array.from(
    modal.querySelectorAll("[data-cargo-observation-mini-tab]"),
  );
  const panelesObservacionInline = Array.from(
    modal.querySelectorAll("[data-cargo-observation-mini-panel]"),
  );
  const estadoHistorialObservacionInline = document.getElementById(
    "estadoGestionObservacionHistorialInline",
  );
  const contenidoHistorialObservacionInline = document.getElementById(
    "contenidoGestionObservacionHistorialInline",
  );
  const btnGuardar = document.getElementById("btnGuardarCargo");
  const btnEliminar = document.getElementById("btnEliminarCargo");
  const modalEliminar = document.getElementById(
    "modalConfirmarEliminacionCargo",
  );
  const btnConfirmarEliminar = document.getElementById(
    "btnConfirmarEliminarCargo",
  );
  const impactoEliminacionTexto = document.getElementById("impactoEliminacionCargo");
  const ceicBusqueda = document.getElementById("cargoGestionCeicBusqueda");
  const estadoPanel = document.getElementById("cargoGestionEstadoPanel");
  const btnEstadoToggle = document.getElementById("cargoGestionEstadoToggle");
  const cambiosPendientes = document.getElementById(
    "cargoGestionCambiosPendientes",
  );
  const ofertasCampo = document.getElementById("cargoGestionOfertasCampo");
  const ofertasSelector = document.getElementById(
    "cargoGestionOfertasSelector",
  );
  const ofertasToggle = document.getElementById("cargoGestionOfertasToggle");
  const ofertasResumen = document.getElementById("cargoGestionOfertasResumen");
  const ofertasOpciones = document.getElementById(
    "cargoGestionOfertasOpciones",
  );
  const ofertasError = document.getElementById("cargoGestionOfertasError");
  const estadoZona = document.getElementById("estadoGestionZona");
  const zonaTipo = document.getElementById("cargoGestionZonaTipo");
  const zonaSelect = document.getElementById("cargoGestionZona");
  const puntosZona = document.getElementById("cargoGestionPuntosZona");
  const observacionZona = document.getElementById("cargoGestionObservacionZona");
  const estadoAnexo = document.getElementById("estadoGestionAnexo");
  const anexoPropietarioTexto = document.getElementById("cargoGestionAnexoPropietario");
  const anexoSelector = document.getElementById("cargoGestionAnexoSelector");
  const anexoToggle = document.getElementById("cargoGestionAnexoToggle");
  const anexoResumen = document.getElementById("cargoGestionAnexoResumen");
  const anexoOpciones = document.getElementById("cargoGestionAnexoOpciones");
  const anexoSeleccionadosInput = document.getElementById("cargoGestionAnexoSeleccionados");
  const anexoNuevoPanel = document.getElementById("cargoGestionAnexoNuevoPanel");
  const anexoNuevoCodigo = document.getElementById("cargoGestionAnexoNuevoCodigo");
  const btnAnexoCrear = document.getElementById("btnCargoGestionAnexoCrear");
  const btnAnexoCancelarCrear = document.getElementById("btnCargoGestionAnexoCancelarCrear");
  const camposEditables = [
    "cargoGestionEstado",
    "cargoGestionCantidad",
    "cargoGestionUnidad",
    "cargoGestionObservacion",
  ];
  const camposVisualesModificados = {
    cargoGestionCantidad: "cargoGestionCantidad",
    cargoGestionUnidad: "cargoGestionUnidad",
    cargoGestionObservacion: "cargoGestionObservacion",
  };
  let cargoActual = null;
  let eliminacionSecuencia = 0;
  let cargoIdEliminacionConfirmable = null;
  let valoresOriginales = {};
  let enviando = false;
  let ultimoTextoCeic = "";
  let triggerActivo = null;
  let ofertasDisponibles = [];
  let requiereOfertas = false;
  let ofertasCatalogoCargado = false;
  let ofertasCatalogoCargando = false;
  let ofertasSecuencia = 0;
  let advertenciaCantidadCeroVisible = false;
  let zonaActual = null;
  let zonaCatalogoSecuencia = 0;
  let zonaCatalogoCargando = false;
  let zonaCatalogoTipoCargado = "";
  let zonaEdicionIniciada = false;
  const zonaCatalogoCache = new Map();
  const zonaCatalogoPromesas = new Map();
  let anexoPropietarioActual = null;
  let anexoCatalogo = [];
  let anexoAsociaciones = [];
  let anexoSeleccionados = new Set();
  let anexoSeleccionInicial = new Set();
  let anexoSecuencia = 0;
  let anexoCargando = false;
  let anexoCreandoCodigo = false;
  let anexoCatalogoCargado = false;
  let anexoAsociacionesCargadas = false;
  let anexoCatalogoCache = null;
  let anexoCatalogoCachePromesa = null;
  let pestaniaActiva = "gestion";
  let historialActivo = "cargo";
  let filtroHistorialCargoActivo = "todos";
  let historialCargado = {
    cargo: false,
    localizacion: false,
    zona: false,
    anexo: false,
    observacion: false,
  };
  let historialCargando = {
    cargo: false,
    localizacion: false,
    zona: false,
    anexo: false,
    observacion: false,
  };
  let historialSecuencia = 0;
  let historialCargoPayload = null;
  let observacionInlineActiva = "editor";

  function buildUrl(base, cargoId) {
    return base.replace("/0/", "/" + cargoId + "/");
  }

  function buildCargoQueryUrl(base, cargoId) {
    const url = new URL(base, window.location.origin);
    url.searchParams.append("cargo_id", String(cargoId));
    return url.toString();
  }

  function zonaAsignada(zona) {
    return Boolean(
      zona &&
      zona.asignada &&
      zona.tipo &&
      zona.zona &&
      Number(zona.puntos) > 0
    );
  }

  function obtenerOpcionZonaSeleccionada() {
    return zonaSelect.options[zonaSelect.selectedIndex] || null;
  }

  function obtenerEstadoZonaFormulario() {
    const tipo = String(zonaTipo.value || "").trim().toUpperCase();
    const opcion = obtenerOpcionZonaSeleccionada();
    const zona = opcion ? String(opcion.value || "").trim() : "";
    const puntos = opcion ? Number(opcion.dataset.puntos || 0) : 0;

    return {
      tipo: tipo,
      zona: zona,
      puntos: zona && puntos > 0 ? puntos : null,
    };
  }

  function hayCambiosZonaModal() {
    if (!zonaEdicionIniciada) {
      return false;
    }

    const estadoZonaFormulario = obtenerEstadoZonaFormulario();
    const tieneZonaActual = zonaAsignada(zonaActual);

    if (!estadoZonaFormulario.zona) {
      return tieneZonaActual;
    }

    if (!estadoZonaFormulario.tipo || !estadoZonaFormulario.puntos) {
      return false;
    }

    if (!tieneZonaActual) {
      return true;
    }

    return !(
      estadoZonaFormulario.tipo ===
        String(zonaActual.tipo || "").trim().toUpperCase() &&
      estadoZonaFormulario.zona === String(zonaActual.zona || "").trim() &&
      estadoZonaFormulario.puntos === Number(zonaActual.puntos || 0)
    );
  }

  function zonaSeleccionValidaParaGuardar() {
    if (zonaCatalogoCargando) {
      return false;
    }

    const estadoZonaFormulario = obtenerEstadoZonaFormulario();

    if (estadoZonaFormulario.zona) {
      return Boolean(
        estadoZonaFormulario.tipo && Number(estadoZonaFormulario.puntos) > 0
      );
    }

    if (zonaAsignada(zonaActual)) {
      return true;
    }

    return !estadoZonaFormulario.tipo;
  }

  function construirPayloadZonaPendiente() {
    if (!hayCambiosZonaModal()) {
      return null;
    }

    const estadoZonaFormulario = obtenerEstadoZonaFormulario();
    const observacion = String(observacionZona.value || "").trim();
    if (!estadoZonaFormulario.zona) {
      return { tipo: "", zona: "", observacion: observacion };
    }

    return {
      tipo: estadoZonaFormulario.tipo,
      zona: estadoZonaFormulario.zona,
      observacion: observacion,
    };
  }

  function actualizarEstadoEdicionZona() {
    const estadoZonaFormulario = obtenerEstadoZonaFormulario();

    if (!estadoZonaFormulario.zona && zonaAsignada(zonaActual)) {
      api.showStatus(
        estadoZona,
        "warning",
        "Al guardar los cambios, se quitará la Zona Educativa y la identidad volverá a quedar pendiente."
      );
    } else if (!estadoZonaFormulario.zona && estadoZonaFormulario.tipo) {
      api.showStatus(
        estadoZona,
        "warning",
        "Seleccioná una Zona Educativa para completar el cambio."
      );
    } else if (estadoZonaFormulario.zona) {
      api.clearStatus(estadoZona);
    }

    marcarCamposModificados();
  }

  function actualizarPuntosZonaSeleccionada() {
    const estadoZonaFormulario = obtenerEstadoZonaFormulario();
    puntosZona.value = estadoZonaFormulario.puntos
      ? String(estadoZonaFormulario.puntos)
      : "";
    actualizarEstadoEdicionZona();
  }

  function resetearZonaCargo() {
    zonaCatalogoSecuencia += 1;
    zonaCatalogoCargando = false;
    zonaCatalogoTipoCargado = "";
    zonaEdicionIniciada = false;
    zonaActual = null;
    zonaTipo.value = "";
    zonaTipo.disabled = false;
    zonaSelect.innerHTML = '<option value="">Seleccioná una zona</option>';
    zonaSelect.disabled = true;
    puntosZona.value = "";
    observacionZona.value = "";
    api.clearStatus(estadoZona);
    actualizarBotonGuardarCargo();
  }

  function parametrosPropietarioAnexo(propietario) {
    const parametros = new URLSearchParams();
    parametros.set("tipo", propietario.tipo);
    parametros.set("valor", propietario.valor);
    return parametros;
  }

  function resolverPropietarioAnexoCargo(cargo) {
    const localizacion = cargo && cargo.localizacion ? cargo.localizacion : {};
    const cueanexo = String(localizacion.cueanexo || "").trim();

    if (cueanexo) {
      if (!/^\d{9}$/.test(cueanexo)) {
        return {
          error:
            "El CUEANEXO del cargo no es válido para resolver el propietario de Anexo POF.",
        };
      }
      return {
        tipo: "CUEANEXO",
        valor: cueanexo,
      };
    }

    const cuof = String(localizacion.cuof || "").trim();
    if (localizacion.tipo_identidad === "CUOF" && cuof) {
      return {
        tipo: "CUOF",
        valor: cuof,
      };
    }

    return {
      error:
        "No se pudo resolver CUEANEXO ni CUOF para administrar Código Anexo POF.",
    };
  }

  function codigosAnexoVigentes() {
    return anexoAsociaciones
      .filter(function (item) {
        return Boolean(item.activo);
      })
      .map(function (item) {
        return String(item.codigo || "").trim();
      })
      .filter(Boolean);
  }

  function obtenerCatalogoAnexoPorId(catalogoId) {
    return anexoCatalogo.find(function (item) {
      return Number(item.id) === Number(catalogoId);
    }) || null;
  }

  function obtenerAsociacionAnexoPorCatalogoId(catalogoId) {
    return anexoAsociaciones.find(function (item) {
      return Number(item.catalogo_id) === Number(catalogoId);
    }) || null;
  }

  function codigosAnexoSeleccionados() {
    const items = Array.from(anexoSeleccionados)
      .map(function (catalogoId) {
        const catalogo = obtenerCatalogoAnexoPorId(catalogoId);
        const asociacion = obtenerAsociacionAnexoPorCatalogoId(catalogoId);
        const codigo = String(
          (catalogo && catalogo.codigo) ||
          (asociacion && asociacion.codigo) ||
          "",
        ).trim();
        return codigo
          ? { id: Number(catalogoId), codigo: codigo }
          : null;
      })
      .filter(Boolean);

    items.sort(function (a, b) {
      return a.codigo.localeCompare(b.codigo, "es", {
        numeric: true,
        sensitivity: "base",
      });
    });

    return items;
  }

  function hayCambiosSeleccionAnexo() {
    if (!anexoAsociacionesCargadas) {
      return false;
    }
    if (anexoSeleccionados.size !== anexoSeleccionInicial.size) {
      return true;
    }
    return Array.from(anexoSeleccionados).some(function (catalogoId) {
      return !anexoSeleccionInicial.has(Number(catalogoId));
    });
  }

  function cerrarOpcionesAnexo() {
    anexoOpciones.classList.add("pof-hidden");
    anexoToggle.setAttribute("aria-expanded", "false");
  }

  function cerrarAltaAnexo(limpiar) {
    anexoNuevoPanel.classList.add("pof-hidden");
    if (limpiar !== false) {
      anexoNuevoCodigo.value = "";
    }
  }

  function abrirAltaAnexo() {
    if (enviando || anexoCargando || anexoCreandoCodigo) {
      return;
    }
    cerrarOpcionesAnexo();
    anexoNuevoPanel.classList.remove("pof-hidden");
    anexoNuevoCodigo.focus();
  }

  function opcionesSeleccionablesAnexo() {
    const opciones = new Map();

    anexoCatalogo.forEach(function (item) {
      if (item.activo) {
        opciones.set(Number(item.id), {
          id: Number(item.id),
          codigo: String(item.codigo || "").trim(),
          catalogo_activo: true,
        });
      }
    });

    anexoAsociaciones.forEach(function (item) {
      const catalogoId = Number(item.catalogo_id);
      if (item.activo && !opciones.has(catalogoId)) {
        opciones.set(catalogoId, {
          id: catalogoId,
          codigo: String(item.codigo || "").trim(),
          catalogo_activo: Boolean(item.catalogo_activo),
        });
      }
    });

    return Array.from(opciones.values()).sort(function (a, b) {
      return a.codigo.localeCompare(b.codigo, "es", {
        numeric: true,
        sensitivity: "base",
      });
    });
  }

  function resetearAnexoCargo() {
    anexoSecuencia += 1;
    anexoCargando = false;
    anexoCreandoCodigo = false;
    anexoPropietarioActual = null;
    anexoCatalogo = [];
    anexoAsociaciones = [];
    anexoSeleccionados = new Set();
    anexoSeleccionInicial = new Set();
    anexoCatalogoCargado = false;
    anexoAsociacionesCargadas = false;
    anexoPropietarioTexto.textContent = "Propietario administrativo";
    anexoResumen.textContent = "Seleccionar Anexos POF";
    anexoSeleccionadosInput.value = "";
    anexoSeleccionadosInput.placeholder = "Ninguno seleccionado";
    anexoOpciones.innerHTML =
      '<div class="pof-admin-offers-empty">Sin propietario cargado.</div>';
    anexoToggle.disabled = true;
    anexoNuevoCodigo.value = "";
    anexoNuevoCodigo.disabled = false;
    btnAnexoCrear.disabled = false;
    btnAnexoCancelarCrear.disabled = false;
    cerrarOpcionesAnexo();
    cerrarAltaAnexo(true);
    api.clearStatus(estadoAnexo);
  }

  function renderizarAnexoCargo() {
    const seleccionados = codigosAnexoSeleccionados();
    const opciones = opcionesSeleccionablesAnexo();

    if (anexoPropietarioActual) {
      anexoPropietarioTexto.textContent =
        anexoPropietarioActual.tipo + " " + anexoPropietarioActual.valor;
    }

    const textoSeleccionados = seleccionados
      .map(function (item) {
        return item.codigo;
      })
      .join(", ");

    anexoResumen.textContent = textoSeleccionados || "Seleccionar Anexos POF";
    anexoSeleccionadosInput.value = textoSeleccionados;
    anexoSeleccionadosInput.placeholder = !anexoAsociacionesCargadas
      ? "Estado actual no disponible"
      : seleccionados.length
      ? ""
      : "Ninguno seleccionado";

    const opcionesHtml = opciones.length
      ? opciones
          .map(function (item) {
            const seleccionado = anexoSeleccionados.has(Number(item.id));
            const retirado = !item.catalogo_activo;
            return (
              '<label class="pof-admin-offers-option' +
              (retirado ? " pof-admin-anexo-option-retired" : "") +
              '">' +
              '<input type="checkbox" data-anexo-catalogo-id="' +
              Number(item.id) +
              '"' +
              (seleccionado ? " checked" : "") +
              (!anexoAsociacionesCargadas ? " disabled" : "") +
              ">" +
              '<span><strong>' +
              escaparHtml(item.codigo) +
              "</strong>" +
              (retirado
                ? "<small>Catálogo retirado · vigente actualmente</small>"
                : "") +
              "</span></label>"
            );
          })
          .join("")
      : '<div class="pof-admin-offers-empty">No hay códigos disponibles todavía.</div>';

    anexoOpciones.innerHTML =
      opcionesHtml +
      '<button type="button" class="pof-admin-anexo-create-option" data-anexo-crear-nuevo' +
      (!anexoAsociacionesCargadas ? " disabled" : "") +
      '>' +
      '<span class="pof-action-icon pof-material-symbol material-symbols-outlined" aria-hidden="true">add</span>' +
      "<span>Crear nuevo Anexo POF</span>" +
      "</button>";

    const bloqueoBase =
      enviando ||
      anexoCargando ||
      anexoCreandoCodigo ||
      !anexoPropietarioActual;
    const selectorBloqueado = bloqueoBase || !anexoCatalogoCargado;
    const edicionBloqueada =
      selectorBloqueado || !anexoAsociacionesCargadas;

    anexoToggle.disabled = selectorBloqueado;
    anexoNuevoCodigo.disabled = edicionBloqueada;
    btnAnexoCrear.disabled = edicionBloqueada;
    btnAnexoCancelarCrear.disabled = anexoCreandoCodigo;
  }

  async function obtenerCatalogoAnexoCache() {
    if (Array.isArray(anexoCatalogoCache)) {
      return anexoCatalogoCache;
    }
    if (!anexoCatalogoCachePromesa) {
      const catalogoUrl = new URL(anexoCatalogoUrl, window.location.origin);
      catalogoUrl.searchParams.set("incluir_inactivos", "1");
      anexoCatalogoCachePromesa = api
        .requestJsonRead(catalogoUrl.toString())
        .then(function (respuesta) {
          const codigos = Array.isArray(
            respuesta.data && respuesta.data.codigos,
          )
            ? respuesta.data.codigos
            : [];
          anexoCatalogoCache = codigos;
          return codigos;
        })
        .catch(function (error) {
          anexoCatalogoCachePromesa = null;
          throw error;
        });
    }
    return anexoCatalogoCachePromesa;
  }

  async function cargarAnexoCargo(cargo, mensajeExito) {
    const propietario = resolverPropietarioAnexoCargo(cargo);
    const secuencia = ++anexoSecuencia;

    anexoCargando = true;
    anexoPropietarioActual = null;
    anexoCatalogo = [];
    anexoAsociaciones = [];
    anexoSeleccionados = new Set();
    anexoSeleccionInicial = new Set();
    anexoCatalogoCargado = false;
    anexoAsociacionesCargadas = false;
    anexoPropietarioTexto.textContent = "Cargando propietario...";
    anexoOpciones.innerHTML =
      '<div class="pof-admin-offers-empty">Cargando Anexo POF...</div>';
    cerrarOpcionesAnexo();
    cerrarAltaAnexo(true);
    renderizarAnexoCargo();

    if (propietario.error) {
      anexoCargando = false;
      anexoPropietarioTexto.textContent = "Propietario no disponible";
      renderizarAnexoCargo();
      api.showStatus(estadoAnexo, "warning", propietario.error);
      return;
    }

    anexoPropietarioActual = propietario;
    anexoPropietarioTexto.textContent =
      propietario.tipo + " " + propietario.valor;

    const parametros = parametrosPropietarioAnexo(propietario);
    const asociacionesUrl = new URL(
      anexoAsociacionesUrl,
      window.location.origin,
    );
    asociacionesUrl.search = parametros.toString();
    asociacionesUrl.searchParams.set("incluir_inactivas", "1");

    const resultados = await Promise.allSettled([
      obtenerCatalogoAnexoCache(),
      api.requestJsonRead(asociacionesUrl.toString(), { cache: "no-store" }),
    ]);

    if (
      secuencia !== anexoSecuencia ||
      !cargoActual ||
      cargoActual.id !== cargo.id
    ) {
      return;
    }

    const resultadoCatalogo = resultados[0];
    const resultadoAsociaciones = resultados[1];

    if (resultadoCatalogo.status === "fulfilled") {
      anexoCatalogo = Array.isArray(resultadoCatalogo.value)
        ? resultadoCatalogo.value
        : [];
      anexoCatalogoCargado = true;
    } else {
      anexoCatalogo = [];
      anexoCatalogoCargado = false;
      api.logError(
        "cargar catalogo anexo pof cargo gestion",
        resultadoCatalogo.reason,
      );
    }

    if (resultadoAsociaciones.status === "fulfilled") {
      const respuestaAsociaciones = resultadoAsociaciones.value;
      anexoPropietarioActual =
        respuestaAsociaciones.data &&
        respuestaAsociaciones.data.propietario
          ? respuestaAsociaciones.data.propietario
          : propietario;
      anexoAsociaciones = Array.isArray(
        respuestaAsociaciones.data &&
        respuestaAsociaciones.data.asociaciones,
      )
        ? respuestaAsociaciones.data.asociaciones
        : [];
      anexoAsociacionesCargadas = true;
      anexoSeleccionInicial = new Set(
        anexoAsociaciones
          .filter(function (item) {
            return Boolean(item.activo);
          })
          .map(function (item) {
            return Number(item.catalogo_id);
          }),
      );
      anexoSeleccionados = new Set(anexoSeleccionInicial);
    } else {
      anexoAsociaciones = [];
      anexoAsociacionesCargadas = false;
      anexoSeleccionInicial = new Set();
      anexoSeleccionados = new Set();
      api.logError(
        "cargar asociaciones anexo pof cargo gestion",
        resultadoAsociaciones.reason,
      );
    }

    anexoCargando = false;
    renderizarAnexoCargo();
    marcarCamposModificados();

    const erroresCarga = [];
    if (resultadoCatalogo.status === "rejected") {
      erroresCarga.push(
        "No se pudo cargar el catálogo Anexo POF: " +
          api.formatError(resultadoCatalogo.reason),
      );
    }
    if (resultadoAsociaciones.status === "rejected") {
      erroresCarga.push(
        "No se pudieron cargar las asociaciones de " +
          propietario.tipo +
          " " +
          propietario.valor +
          ": " +
          api.formatError(resultadoAsociaciones.reason),
      );
    }

    if (erroresCarga.length) {
      api.showStatus(
        estadoAnexo,
        "error",
        erroresCarga.join(" "),
      );
      return;
    }

    if (mensajeExito) {
      api.showStatus(estadoAnexo, "success", mensajeExito);
    } else {
      api.clearStatus(estadoAnexo);
    }
  }

  async function crearNuevoCodigoAnexo() {
    if (
      !anexoPropietarioActual ||
      enviando ||
      anexoCargando ||
      anexoCreandoCodigo
    ) {
      return;
    }

    if (!anexoCatalogoCargado || !anexoAsociacionesCargadas) {
      api.showStatus(
        estadoAnexo,
        "error",
        "No se puede crear ni modificar Anexo POF hasta cargar correctamente el catálogo y las asociaciones actuales.",
      );
      return;
    }

    const codigo = String(anexoNuevoCodigo.value || "").trim();
    if (!codigo) {
      api.showStatus(
        estadoAnexo,
        "error",
        "Ingresá un Código Anexo POF para crear.",
      );
      anexoNuevoCodigo.focus();
      return;
    }

    const existente = anexoCatalogo.find(function (item) {
      return String(item.codigo || "").trim() === codigo;
    });
    if (existente) {
      if (!existente.activo) {
        api.showStatus(
          estadoAnexo,
          "error",
          "El Código Anexo POF " +
            codigo +
            " ya existe en el catálogo pero está inactivo. Reactivalo desde Administración de Anexo POF si necesitás volver a usarlo.",
        );
        return;
      }

      anexoSeleccionados.add(Number(existente.id));
      cerrarAltaAnexo(true);
      renderizarAnexoCargo();
      marcarCamposModificados();
      api.showStatus(
        estadoAnexo,
        "info",
        "El código " +
          codigo +
          " ya existía y quedó marcado en la selección. Guardá cambios para asociarlo.",
      );
      return;
    }

    anexoCreandoCodigo = true;
    renderizarAnexoCargo();
    api.showStatus(estadoAnexo, "warning", "Creando Código Anexo POF...");

    try {
      const respuesta = await api.requestJson(anexoCatalogoCrearUrl, {
        method: "POST",
        body: { codigo: codigo },
      });
      const creado =
        respuesta.data && respuesta.data.codigo
          ? respuesta.data.codigo
          : null;

      if (!creado || !creado.id) {
        throw new Error("No se recibió el Código Anexo POF creado.");
      }

      const indiceExistente = anexoCatalogo.findIndex(function (item) {
        return Number(item.id) === Number(creado.id);
      });
      if (indiceExistente >= 0) {
        anexoCatalogo[indiceExistente] = creado;
      } else {
        anexoCatalogo.push(creado);
      }
      anexoCatalogoCache = anexoCatalogo.slice();
      anexoCatalogoCachePromesa = Promise.resolve(anexoCatalogoCache);

      anexoSeleccionados.add(Number(creado.id));
      anexoCreandoCodigo = false;
      cerrarAltaAnexo(true);
      renderizarAnexoCargo();
      marcarCamposModificados();
      api.showStatus(
        estadoAnexo,
        "success",
        "Código " +
          String(creado.codigo || codigo) +
          " creado y marcado en la selección. Guardá cambios para asociarlo.",
      );
    } catch (error) {
      anexoCreandoCodigo = false;
      renderizarAnexoCargo();
      api.showStatus(estadoAnexo, "error", api.formatError(error));
      api.logError("crear codigo anexo pof cargo gestion", error);
    }
  }

  async function obtenerCatalogoZonaCache(tipoNormalizado) {
    if (zonaCatalogoCache.has(tipoNormalizado)) {
      return zonaCatalogoCache.get(tipoNormalizado);
    }
    if (zonaCatalogoPromesas.has(tipoNormalizado)) {
      return zonaCatalogoPromesas.get(tipoNormalizado);
    }

    const url = new URL(zonaCatalogoUrl, window.location.origin);
    url.searchParams.set("tipo", tipoNormalizado);
    const promesa = api
      .requestJsonRead(url.toString())
      .then(function (data) {
        const payload = data.data || {};
        const zonas = Array.isArray(payload.zonas) ? payload.zonas : [];
        zonaCatalogoCache.set(tipoNormalizado, zonas);
        zonaCatalogoPromesas.delete(tipoNormalizado);
        return zonas;
      })
      .catch(function (error) {
        zonaCatalogoPromesas.delete(tipoNormalizado);
        throw error;
      });

    zonaCatalogoPromesas.set(tipoNormalizado, promesa);
    return promesa;
  }

  async function cargarCatalogoZona(tipo, zonaPreferida) {
    const tipoNormalizado = String(tipo || "").trim().toUpperCase();
    zonaCatalogoSecuencia += 1;
    const secuencia = zonaCatalogoSecuencia;
    zonaCatalogoCargando = true;

    zonaSelect.innerHTML = '<option value="">Cargando zonas...</option>';
    zonaSelect.disabled = true;
    puntosZona.value = "";
    actualizarBotonGuardarCargo();

    if (!tipoNormalizado) {
      zonaCatalogoCargando = false;
      zonaSelect.innerHTML = '<option value="">Seleccioná una zona</option>';
      if (zonaAsignada(zonaActual)) {
        api.showStatus(
          estadoZona,
          "warning",
          "Al guardar los cambios, se quitará la Zona Educativa y la identidad volverá a quedar pendiente."
        );
      } else {
        api.showStatus(
          estadoZona,
          "warning",
          "Seleccioná primero si la Zona Educativa es urbana o rural."
        );
      }
      marcarCamposModificados();
      return;
    }

    try {
      const zonas = await obtenerCatalogoZonaCache(tipoNormalizado);

      if (secuencia !== zonaCatalogoSecuencia) {
        return;
      }

      zonaCatalogoCargando = false;
      zonaCatalogoTipoCargado = tipoNormalizado;
      zonaSelect.innerHTML = '<option value="">Seleccioná una zona</option>';

      zonas.forEach(function (item) {
        const opcion = document.createElement("option");
        opcion.value = String(item.zona || "");
        opcion.textContent = String(item.zona || "");
        opcion.dataset.puntos = String(item.puntos || "");
        zonaSelect.appendChild(opcion);
      });

      zonaSelect.disabled = enviando || zonas.length === 0;

      const preferida = String(zonaPreferida || "").trim();
      if (
        preferida &&
        zonas.some(function (item) {
          return String(item.zona || "").trim() === preferida;
        })
      ) {
        zonaSelect.value = preferida;

        const opcionActual = obtenerOpcionZonaSeleccionada();
        const puntosCatalogo = Number(
          opcionActual ? opcionActual.dataset.puntos || 0 : 0
        );

        if (!zonaEdicionIniciada && zonaAsignada(zonaActual)) {
          puntosZona.value = String(zonaActual.puntos || "");
        } else {
          puntosZona.value = puntosCatalogo > 0 ? String(puntosCatalogo) : "";
        }

        if (
          zonaAsignada(zonaActual) &&
          puntosCatalogo !== Number(zonaActual.puntos || 0)
        ) {
          api.showStatus(
            estadoZona,
            "warning",
            "La Zona vigente conserva " +
              zonaActual.puntos +
              " puntos históricos; el catálogo actual indica " +
              puntosCatalogo +
              ". Se mantendrán los históricos mientras no modifiques la Zona."
          );
        } else {
          api.clearStatus(estadoZona);
        }
        marcarCamposModificados();
        return;
      }

      if (zonaAsignada(zonaActual) && preferida) {
        const opcionVigente = document.createElement("option");
        opcionVigente.value = preferida;
        opcionVigente.textContent = preferida + " (vigente, inactiva)";
        opcionVigente.dataset.puntos = String(zonaActual.puntos || "");
        zonaSelect.appendChild(opcionVigente);
        zonaSelect.value = preferida;
        zonaSelect.disabled = enviando;
        puntosZona.value = String(zonaActual.puntos || "");
        api.showStatus(
          estadoZona,
          "warning",
          "La Zona Educativa vigente ya no está activa en el catálogo. Elegí una zona activa para reemplazarla o «Seleccioná una zona» para quitarla."
        );
      } else if (zonas.length) {
        api.showStatus(
          estadoZona,
          "warning",
          zonaAsignada(zonaActual)
            ? "Elegí una nueva Zona Educativa o dejá «Seleccioná una zona» para quitar la vigente."
            : "Seleccioná una Zona Educativa para completar este registro."
        );
      } else if (zonaAsignada(zonaActual)) {
        api.showStatus(
          estadoZona,
          "warning",
          "No hay Zonas Educativas activas disponibles para este tipo. Podés quitar la asignación vigente."
        );
      } else {
        api.showStatus(
          estadoZona,
          "error",
          "No hay Zonas Educativas activas disponibles para este tipo."
        );
      }

      marcarCamposModificados();
    } catch (error) {
      if (secuencia !== zonaCatalogoSecuencia) {
        return;
      }
      zonaCatalogoCargando = false;
      zonaSelect.innerHTML = '<option value="">Seleccioná una zona</option>';

      if (zonaAsignada(zonaActual)) {
        const opcionVigente = document.createElement("option");
        opcionVigente.value = String(zonaActual.zona || "");
        opcionVigente.textContent = String(zonaActual.zona || "") + " (vigente)";
        opcionVigente.dataset.puntos = String(zonaActual.puntos || "");
        zonaSelect.appendChild(opcionVigente);
        zonaSelect.value = String(zonaActual.zona || "");
        zonaSelect.disabled = enviando;
        puntosZona.value = String(zonaActual.puntos || "");
      } else {
        zonaSelect.disabled = true;
        puntosZona.value = "";
      }

      api.showStatus(estadoZona, "error", api.formatError(error));
      api.logError("catalogo zona cargo gestion", error);
      marcarCamposModificados();
    }
  }

  function aplicarZonaCargo(zona) {
    zonaEdicionIniciada = false;
    zonaActual = zona || null;
    zonaCatalogoTipoCargado = "";
    zonaTipo.disabled = enviando;

    if (!zonaAsignada(zonaActual)) {
      zonaTipo.value = "";
      zonaSelect.innerHTML = '<option value="">Seleccioná una zona</option>';
      zonaSelect.disabled = true;
      puntosZona.value = "";
      api.showStatus(
        estadoZona,
        "warning",
        "Sin Zona Educativa. Elegí tipo y zona y después usá Guardar cambios."
      );
      actualizarBotonGuardarCargo();
      return;
    }

    zonaTipo.value = String(zonaActual.tipo || "").trim().toUpperCase();
    puntosZona.value = String(zonaActual.puntos || "");
    zonaSelect.innerHTML = '<option value="">Seleccioná una zona</option>';
    const opcionVigente = document.createElement("option");
    opcionVigente.value = String(zonaActual.zona || "");
    opcionVigente.textContent = String(zonaActual.zona || "");
    opcionVigente.dataset.puntos = String(zonaActual.puntos || "");
    zonaSelect.appendChild(opcionVigente);
    zonaSelect.value = String(zonaActual.zona || "");
    zonaSelect.disabled = enviando;
    api.showStatus(
      estadoZona,
      "success",
      "Zona vigente: " + zonaActual.zona + " · " + zonaActual.puntos + " puntos."
    );
    actualizarBotonGuardarCargo();

    obtenerCatalogoZonaCache(zonaTipo.value).catch(function (error) {
      api.logError("precargar catalogo zona cargo gestion", error);
    });
  }

  function setEnviando(valor) {
    enviando = valor;
    btnEliminar.disabled = valor;
    btnConfirmarEliminar.disabled = valor || !cargoIdEliminacionConfirmable;
    btnEstadoToggle.disabled = valor;
    ofertasToggle.disabled =
      valor || !requiereOfertas || ofertasCatalogoCargando;
    ofertasOpciones
      .querySelectorAll('input[type="checkbox"]')
      .forEach(function (checkbox) {
        checkbox.disabled = valor;
      });
    zonaTipo.disabled = valor;
    zonaSelect.disabled =
      valor ||
      zonaCatalogoCargando ||
      (!zonaAsignada(zonaActual) && zonaSelect.options.length <= 1);
    renderizarAnexoCargo();
    actualizarBotonGuardarCargo();
  }

  function escaparHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto == null ? "" : String(texto);
    return div.innerHTML;
  }

  function formatearFecha(fecha) {
    if (!fecha) {
      return "-";
    }
    const valor = new Date(fecha);
    if (Number.isNaN(valor.getTime())) {
      return "-";
    }
    const dia = String(valor.getDate()).padStart(2, "0");
    const mes = String(valor.getMonth() + 1).padStart(2, "0");
    const anio = valor.getFullYear();
    const horas = String(valor.getHours()).padStart(2, "0");
    const minutos = String(valor.getMinutes()).padStart(2, "0");
    return `${dia}/${mes}/${anio} ${horas}:${minutos}`;
  }

  function valorHistorial(valor) {
    if (valor === null || valor === undefined || valor === "") {
      return "—";
    }
    return String(valor);
  }

  function limpiarContenido(elemento) {
    if (elemento) {
      elemento.innerHTML = "";
    }
  }

  function agregarResumenHistorial(contenedor, etiqueta, valor, ancho) {
    const item = document.createElement("div");
    item.className = "pof-admin-history-summary-item" + (ancho ? " pof-admin-history-summary-wide" : "");
    const label = document.createElement("span");
    const contenido = document.createElement("strong");
    label.textContent = etiqueta;
    contenido.textContent = valorHistorial(valor);
    item.appendChild(label);
    item.appendChild(contenido);
    contenedor.appendChild(item);
  }

  function renderizarResumenVisualMovimiento(movimiento, contenedor) {
    const resumen = movimiento.detalle_visual || {};
    const accion = resumen.accion || movimiento.detalle || "Movimiento registrado.";
    const partes = Array.isArray(resumen.partes) ? resumen.partes : [];

    const tarjeta = document.createElement("div");
    tarjeta.className = "pof-history-summary-card pof-admin-history-summary-card";

    const accionElemento = document.createElement("div");
    accionElemento.className = "pof-history-summary-action";
    accionElemento.textContent = valorHistorial(accion);
    tarjeta.appendChild(accionElemento);

    if (partes.length) {
      const hechos = document.createElement("div");
      hechos.className = "pof-history-summary-facts";
      partes.forEach(function (parte, indice) {
        const chip = document.createElement("span");
        chip.className = "pof-history-summary-fact";
        chip.style.setProperty("--pof-history-fact-index", String(indice));
        chip.textContent = valorHistorial(parte);
        hechos.appendChild(chip);
      });
      tarjeta.appendChild(hechos);
    }

    contenedor.appendChild(tarjeta);
  }

  function renderizarResumenHistorialCargo(payload) {
    limpiarContenido(resumenHistorialCargo);
    const cargo = payload.cargo || {};
    const localizacion = payload.localizacion || {};
    agregarResumenHistorial(resumenHistorialCargo, "CEIC", cargo.ceic);
    agregarResumenHistorial(resumenHistorialCargo, "Estado actual", cargo.estado_pof);
    agregarResumenHistorial(resumenHistorialCargo, "Cantidad actual", cargo.cantidad);
    agregarResumenHistorial(
      resumenHistorialCargo,
      localizacion.tipo_identidad === "CUOF" ? "CUOF" : "CUEANEXO",
      localizacion.identidad || (
        localizacion.tipo_identidad === "CUOF"
          ? localizacion.cuof
          : localizacion.cueanexo
      ),
    );
    agregarResumenHistorial(resumenHistorialCargo, "Cargo", cargo.cargo, true);
  }

  function crearBloqueCicloHistorial(ciclo, mostrarTitulo, contenido) {
    const bloque = document.createElement("section");
    bloque.className = mostrarTitulo ? "pof-admin-history-item pof-observation-timeline-group" : "";
    if (mostrarTitulo) {
      const titulo = document.createElement("h3");
      titulo.className = "pof-observation-timeline-group-title";
      titulo.textContent = "POF " + valorHistorial(ciclo.anio);
      bloque.appendChild(titulo);
      const contexto = document.createElement("p");
      contexto.className = "pof-admin-history-meta";
      contexto.textContent = valorHistorial((ciclo.localizacion || {}).cabecera);
      bloque.appendChild(contexto);
    }
    contenido.appendChild(bloque);
    return bloque;
  }

  function renderizarEstadoInicialCiclo(ciclo, bloque, soloObservaciones) {
    const inicial = ciclo.estado_inicial || {};
    const titulo = document.createElement("p");
    titulo.className = "pof-observation-timeline-group-title";
    titulo.textContent = inicial.heredado ? "Estado inicial heredado" : "Estado inicial";
    bloque.appendChild(titulo);
    const resumen = document.createElement("div");
    resumen.className = "pof-admin-history-summary";
    agregarResumenHistorial(resumen, "Registro del ciclo", "#" + ciclo.cargo_id);
    agregarResumenHistorial(resumen, "Creado", inicial.fecha);
    (Array.isArray(inicial.campos) ? inicial.campos : []).forEach(function (campo) {
      if (!soloObservaciones || campo.campo === "observacion") {
        agregarResumenHistorial(resumen, campo.nombre, campo.valor, campo.campo === "cargo" || campo.campo === "observacion");
      }
    });
    bloque.appendChild(resumen);
    if (!Array.isArray(inicial.campos) || !inicial.campos.length) {
      const aviso = document.createElement("p");
      aviso.textContent = "No se conserva un snapshot inicial para este ciclo.";
      bloque.appendChild(aviso);
    }
  }

  function renderizarHistorialCargoPorCiclos(payload, soloObservaciones, opciones) {
    const opts = opciones || {};
    const contenido = opts.contenido || (
      soloObservaciones ? contenidoHistorialObservacion : contenidoHistorialCargo
    );
    const estado = opts.estado || (
      soloObservaciones ? estadoHistorialObservacion : estadoHistorialCargo
    );
    const resumen = soloObservaciones
      ? (
        Object.prototype.hasOwnProperty.call(opts, "resumen")
          ? opts.resumen
          : resumenHistorialObservacion
      )
      : null;

    limpiarContenido(contenido);
    api.clearStatus(estado);
    const ciclos = Array.isArray(payload.ciclos) ? payload.ciclos : [];
    if (!ciclos.length) {
      if (soloObservaciones) {
        renderizarHistorialObservacion(payload, resumen, contenido, estado);
      } else {
        renderizarMovimientosContextuales(payload, contenido, estado, false);
      }
      return;
    }
    if (soloObservaciones && resumen) {
      limpiarContenido(resumen);
      agregarResumenHistorial(resumen, "CEIC", (payload.cargo || {}).ceic);
      agregarResumenHistorial(
        resumen,
        "Observación actual",
        (payload.cargo || {}).observacion_actual,
        true,
      );
    }

    ciclos.forEach(function (ciclo) {
      const bloque = crearBloqueCicloHistorial(ciclo, ciclos.length > 1, contenido);
      if (ciclos.length > 1 || ciclo.cargo_origen_id || !ciclo.movimientos.length) {
        renderizarEstadoInicialCiclo(ciclo, bloque, soloObservaciones);
      }
      const estadoCiclo = document.createElement("div");
      estadoCiclo.className = "pof-status pof-hidden";
      const contenidoCiclo = document.createElement("div");
      bloque.appendChild(estadoCiclo);
      bloque.appendChild(contenidoCiclo);
      if (soloObservaciones) {
        // El resumen global sigue representando el cargo abierto.
        renderizarHistorialObservacion(
          ciclo.observaciones || {},
          null,
          contenidoCiclo,
          estadoCiclo,
        );
      } else {
        renderizarMovimientosContextuales(ciclo, contenidoCiclo, estadoCiclo, false);
      }
    });
    if (payload.advertencia_continuidad) {
      api.showStatus(
        estado,
        "warning",
        payload.advertencia_continuidad + " Se muestran sólo los ciclos verificables.",
      );
    }
  }

  function renderizarHistorialContextualPorCiclos(payload, contenido, estado, renderizarCiclo) {
    limpiarContenido(contenido);
    api.clearStatus(estado);
    const ciclos = Array.isArray(payload.ciclos) ? payload.ciclos : [];
    if (!ciclos.length) {
      renderizarCiclo(payload, contenido, estado);
      return;
    }

    ciclos.forEach(function (ciclo) {
      const bloque = crearBloqueCicloHistorial(ciclo, ciclos.length > 1, contenido);
      const estadoCiclo = document.createElement("div");
      estadoCiclo.className = "pof-status pof-hidden";
      const contenidoCiclo = document.createElement("div");
      bloque.appendChild(estadoCiclo);
      bloque.appendChild(contenidoCiclo);
      renderizarCiclo(ciclo, contenidoCiclo, estadoCiclo);
    });
    if (payload.advertencia_continuidad) {
      api.showStatus(estado, "warning", payload.advertencia_continuidad + " Se muestran sólo los ciclos verificables.");
    }
  }

  function renderizarResumenHistorialLocalizacion(payload) {
    limpiarContenido(resumenHistorialLocalizacion);
    const localizacion = payload.localizacion || {};
    agregarResumenHistorial(
      resumenHistorialLocalizacion,
      localizacion.tipo_identidad === "CUOF" ? "CUOF" : "CUEANEXO",
      localizacion.identidad || (
        localizacion.tipo_identidad === "CUOF"
          ? localizacion.cuof
          : localizacion.cueanexo
      ),
    );
    agregarResumenHistorial(resumenHistorialLocalizacion, "Cabecera", localizacion.cabecera, true);
  }

  function crearValorCambioHistorial(etiqueta, valor, clase) {
    const bloque = document.createElement("div");
    bloque.className = "pof-admin-history-value " + (clase || "");

    const titulo = document.createElement("span");
    titulo.className = "pof-admin-history-value-label";
    titulo.textContent = etiqueta;

    const contenido = document.createElement("strong");
    contenido.className = "pof-admin-history-value-text";
    contenido.textContent = valorHistorial(valor);

    bloque.appendChild(titulo);
    bloque.appendChild(contenido);
    return bloque;
  }

  function renderizarDetalleMovimientoInline(movimiento, contenedor) {
    const diff = Array.isArray(movimiento.diff) ? movimiento.diff : [];
    if (!diff.length && !movimiento.observacion) {
      const vacio = document.createElement("div");
      vacio.className = "pof-admin-history-detail-empty";
      vacio.textContent = "El movimiento no registra diferencias adicionales.";
      contenedor.appendChild(vacio);
      return;
    }

    diff.forEach(function (cambio) {
      const fila = document.createElement("div");
      fila.className = "pof-admin-history-diff-row";
      const campo = document.createElement("strong");
      campo.textContent = valorHistorial(cambio.campo || cambio.clave);

      const valores = document.createElement("div");
      valores.className = "pof-admin-history-diff-values";
      const anterior = valorHistorial(cambio.anterior);
      const nuevo = valorHistorial(cambio.nuevo);

      if ((cambio.tipo === "agregado" || anterior === "—") && nuevo !== "—") {
        valores.appendChild(
          crearValorCambioHistorial("Valor inicial", nuevo, "pof-admin-history-value-after"),
        );
      } else if ((cambio.tipo === "eliminado" || nuevo === "—") && anterior !== "—") {
        valores.appendChild(
          crearValorCambioHistorial("Valor anterior", anterior, "pof-admin-history-value-before"),
        );
      } else {
        valores.appendChild(
          crearValorCambioHistorial("Antes", anterior, "pof-admin-history-value-before"),
        );
        valores.appendChild(
          crearValorCambioHistorial("Después", nuevo, "pof-admin-history-value-after"),
        );
      }

      fila.appendChild(campo);
      fila.appendChild(valores);
      contenedor.appendChild(fila);
    });

    if (movimiento.observacion) {
      const observacion = document.createElement("div");
      observacion.className = "pof-admin-history-observation";
      const titulo = document.createElement("strong");
      const texto = document.createElement("span");
      titulo.textContent = "Observación";
      texto.textContent = movimiento.observacion;
      observacion.appendChild(titulo);
      observacion.appendChild(texto);
      contenedor.appendChild(observacion);
    }
  }

  function renderizarMovimientosContextuales(payload, contenido, estadoPanelHistorial, incluirCargo) {
    limpiarContenido(contenido);
    api.clearStatus(estadoPanelHistorial);
    const movimientos = Array.isArray(payload.movimientos) ? payload.movimientos : [];
    if (!movimientos.length) {
      api.showStatus(
        estadoPanelHistorial,
        "info",
        incluirCargo
          ? "No se registraron movimientos de cargos para esta localización."
          : "Este cargo todavía no registra movimientos de historial.",
      );
      return;
    }

    const lista = document.createElement("div");
    lista.className = "pof-admin-history-list";

    movimientos.forEach(function (movimiento, indiceMovimiento) {
      const item = document.createElement("article");
      item.className = "pof-admin-history-item pof-admin-history-item-animated";
      item.style.setProperty("--pof-admin-history-item-index", String(indiceMovimiento));

      const cabecera = document.createElement("div");
      cabecera.className = "pof-admin-history-item-head";
      const tipo = document.createElement("span");
      tipo.className = "pof-admin-history-type pof-admin-history-type-" + String(movimiento.tipo_movimiento_clase || "movimiento");
      tipo.textContent = valorHistorial(movimiento.tipo_movimiento_display);
      const fecha = document.createElement("strong");
      fecha.textContent = valorHistorial(movimiento.fecha);
      cabecera.appendChild(tipo);
      cabecera.appendChild(fecha);
      item.appendChild(cabecera);

      if (incluirCargo) {
        const cargoMovimiento = movimiento.cargo || {};
        const referencia = document.createElement("div");
        referencia.className = "pof-admin-history-cargo-ref";
        referencia.textContent =
          "CEIC " + valorHistorial(cargoMovimiento.ceic) + " · " + valorHistorial(cargoMovimiento.cargo);
        item.appendChild(referencia);
      }

      const meta = document.createElement("div");
      meta.className = "pof-admin-history-meta";
      const usuario = movimiento.usuario || {};
      meta.textContent = "Usuario: " + valorHistorial(usuario.nombre);
      item.appendChild(meta);

      const detalle = document.createElement("div");
      detalle.className = "pof-admin-history-description";
      renderizarResumenVisualMovimiento(movimiento, detalle);
      item.appendChild(detalle);

      const acciones = document.createElement("div");
      acciones.className = "pof-admin-history-actions";
      const botonDetalle = document.createElement("button");
      botonDetalle.type = "button";
      botonDetalle.className = "pof-btn pof-btn-light pof-admin-history-detail-toggle";
      botonDetalle.textContent = "Ver detalle";
      const detalleCompleto = document.createElement("div");
      detalleCompleto.className = "pof-admin-history-detail pof-hidden";
      renderizarDetalleMovimientoInline(movimiento, detalleCompleto);
      botonDetalle.addEventListener("click", function () {
        const abrir = detalleCompleto.classList.contains("pof-hidden");
        detalleCompleto.classList.toggle("pof-hidden", !abrir);
        botonDetalle.textContent = abrir ? "Ocultar detalle" : "Ver detalle";
      });
      acciones.appendChild(botonDetalle);
      item.appendChild(acciones);
      item.appendChild(detalleCompleto);
      lista.appendChild(item);
    });

    contenido.appendChild(lista);
  }

  function crearValorCambioZona(etiqueta, valor, clase) {
    const bloque = document.createElement("div");
    bloque.className = "pof-admin-zone-history-value " + clase;

    const titulo = document.createElement("span");
    titulo.className = "pof-admin-zone-history-value-label";
    titulo.textContent = etiqueta;

    const contenido = document.createElement("strong");
    contenido.className = "pof-admin-zone-history-value-text";
    contenido.textContent = valorHistorial(valor);

    bloque.appendChild(titulo);
    bloque.appendChild(contenido);
    return bloque;
  }

  function renderizarCambiosZona(evento, contenedor) {
    const cambios = Array.isArray(evento.cambios) ? evento.cambios : [];
    if (!cambios.length) {
      const vacio = document.createElement("div");
      vacio.className = "pof-admin-history-detail-empty";
      vacio.textContent = "Sin diferencias adicionales.";
      contenedor.appendChild(vacio);
      return;
    }

    cambios.forEach(function (cambio) {
      const fila = document.createElement("div");
      fila.className = "pof-admin-zone-history-change";

      const campo = document.createElement("strong");
      campo.className = "pof-admin-zone-history-field";
      campo.textContent = valorHistorial(
        cambio.etiqueta || cambio.campo || "Cambio",
      );

      const valores = document.createElement("div");
      valores.className = "pof-admin-zone-history-values";
      valores.appendChild(
        crearValorCambioZona("Antes", cambio.anterior, "pof-admin-zone-history-value-before"),
      );
      valores.appendChild(
        crearValorCambioZona("Después", cambio.nuevo, "pof-admin-zone-history-value-after"),
      );

      fila.appendChild(campo);
      fila.appendChild(valores);
      contenedor.appendChild(fila);
    });
  }

  function descripcionZona(asignacion) {
    const zona = asignacion || {};
    if (!zona.zona) {
      return "Sin zona";
    }
    return zona.zona + (zona.puntos ? " · " + zona.puntos + " puntos" : "");
  }

  function renderizarResumenHistorialZona(payload) {
    limpiarContenido(resumenHistorialZona);

    const identidad = payload.identidad || {};
    const vigente = payload.vigente || {};
    agregarResumenHistorial(
      resumenHistorialZona,
      identidad.tipo_clave === "CUOF" ? "CUOF" : "CUEANEXO",
      identidad.clave,
    );
    agregarResumenHistorial(resumenHistorialZona, "Año", identidad.anio);
    agregarResumenHistorial(resumenHistorialZona, "Zona vigente", descripcionZona(vigente), true);
  }

  function renderizarHistorialZonaPorCiclos(payload) {
    renderizarResumenHistorialZona(payload);
    renderizarHistorialContextualPorCiclos(
      payload, contenidoHistorialZona, estadoHistorialZona, renderizarHistorialZona,
    );
  }

  function renderizarHistorialZona(
    payload,
    contenido = contenidoHistorialZona,
    estado = estadoHistorialZona,
  ) {
    limpiarContenido(contenido);
    api.clearStatus(estado);
    const eventos = Array.isArray(payload.eventos) ? payload.eventos : [];
    if (!eventos.length) {
      api.showStatus(
        estado,
        "info",
        "No se registraron cambios de Zona Educativa para esta localización.",
      );
      return;
    }

    const lista = document.createElement("div");
    lista.className = "pof-admin-history-list";
    eventos.forEach(function (evento, indiceEvento) {
      const item = document.createElement("article");
      item.className = "pof-admin-history-item pof-admin-history-item-animated";
      item.style.setProperty("--pof-admin-history-item-index", String(indiceEvento));
      const cabecera = document.createElement("div");
      cabecera.className = "pof-admin-history-item-head";
      const tipo = document.createElement("span");
      tipo.className = "pof-admin-history-type pof-admin-history-type-zona";
      tipo.textContent = "Zona Educativa";
      const fecha = document.createElement("strong");
      fecha.textContent = formatearFecha(evento.fecha);
      cabecera.appendChild(tipo);
      cabecera.appendChild(fecha);
      item.appendChild(cabecera);

      const meta = document.createElement("div");
      meta.className = "pof-admin-history-meta";
      meta.textContent = "Usuario: " + valorHistorial((evento.usuario || {}).nombre);
      item.appendChild(meta);

      const accion = document.createElement("div");
      accion.className = "pof-history-summary-action pof-admin-zone-history-action";
      accion.textContent = "Se actualizó la Zona Educativa.";
      item.appendChild(accion);

      const transicion = document.createElement("div");
      transicion.className = "pof-admin-zone-history-transition";
      transicion.appendChild(
        crearValorCambioZona(
          "Antes",
          descripcionZona(evento.anterior),
          "pof-admin-zone-history-value-before",
        ),
      );
      transicion.appendChild(
        crearValorCambioZona(
          "Después",
          descripcionZona(evento.nuevo),
          "pof-admin-zone-history-value-after",
        ),
      );
      item.appendChild(transicion);

      const cambios = document.createElement("div");
      cambios.className = "pof-admin-history-detail pof-admin-zone-history-detail";
      renderizarCambiosZona(evento, cambios);
      item.appendChild(cambios);

      const observacion = String(evento.observacion || "").trim();
      if (observacion) {
        const nota = document.createElement("div");
        nota.className = "pof-admin-history-detail";
        nota.textContent = "Observación: " + observacion;
        item.appendChild(nota);
      }

      lista.appendChild(item);
    });
    contenido.appendChild(lista);
  }

  function usuarioAnexoVisible(usuario) {
    if (!usuario) {
      return "—";
    }
    if (typeof usuario === "string") {
      return usuario || "—";
    }
    return String(usuario.texto || usuario.nombre || "—");
  }

  function renderizarHistorialAnexo(payload) {
    limpiarContenido(resumenHistorialAnexo);
    limpiarContenido(contenidoHistorialAnexo);
    api.clearStatus(estadoHistorialAnexo);

    const propietario =
      payload.propietario || anexoPropietarioActual || {};
    const vigentes = codigosAnexoVigentes();

    agregarResumenHistorial(
      resumenHistorialAnexo,
      "Propietario",
      propietario.tipo && propietario.valor
        ? propietario.tipo + " " + propietario.valor
        : "—",
    );
    agregarResumenHistorial(
      resumenHistorialAnexo,
      "Código(s) vigente(s)",
      vigentes.length ? vigentes.join(", ") : "Sin códigos vigentes",
      true,
    );

    const historial = Array.isArray(payload.historial)
      ? payload.historial
      : [];

    if (!historial.length) {
      api.showStatus(
        estadoHistorialAnexo,
        "info",
        "No se registraron movimientos de Anexo POF para este propietario.",
      );
      return;
    }

    const lista = document.createElement("div");
    lista.className = "pof-admin-history-list";

    historial.forEach(function (evento, indiceEvento) {
      const item = document.createElement("article");
      item.className =
        "pof-admin-history-item pof-admin-history-item-animated";
      item.style.setProperty(
        "--pof-admin-history-item-index",
        String(indiceEvento),
      );

      const cabecera = document.createElement("div");
      cabecera.className = "pof-admin-history-item-head";

      const tipo = document.createElement("span");
      tipo.className = "pof-admin-history-type";
      tipo.textContent = "Anexo POF";

      const fecha = document.createElement("strong");
      fecha.textContent = formatearFecha(evento.fecha);

      cabecera.appendChild(tipo);
      cabecera.appendChild(fecha);
      item.appendChild(cabecera);

      const meta = document.createElement("div");
      meta.className = "pof-admin-history-meta";
      meta.textContent =
        "Usuario: " + usuarioAnexoVisible(evento.usuario);
      item.appendChild(meta);

      const accion = document.createElement("div");
      accion.className = "pof-history-summary-action";
      accion.textContent =
        "Código " +
        valorHistorial(evento.codigo) +
        " · " +
        valorHistorial(evento.accion_texto || evento.accion);
      item.appendChild(accion);

      lista.appendChild(item);
    });

    contenidoHistorialAnexo.appendChild(lista);
  }

  function crearBloqueObservacionTimeline(etiqueta, valor, clase) {
    const bloque = document.createElement("div");
    bloque.className = "pof-observation-timeline-value " + (clase || "");

    const label = document.createElement("span");
    label.className = "pof-observation-timeline-value-label";
    label.textContent = etiqueta;

    const texto = document.createElement("div");
    texto.className = "pof-observation-timeline-value-text";
    texto.textContent = valorHistorial(valor);

    bloque.appendChild(label);
    bloque.appendChild(texto);
    return bloque;
  }

  function crearEventoObservacionTimeline(evento, indice, abiertoPorDefecto) {
    const entrada = document.createElement("div");
    entrada.className = "pof-observation-timeline-entry";
    entrada.style.setProperty("--pof-observation-event-index", String(indice));

    const nodo = document.createElement("span");
    nodo.className = "pof-observation-timeline-node";
    nodo.setAttribute("aria-hidden", "true");
    entrada.appendChild(nodo);

    const tarjeta = document.createElement("article");
    tarjeta.className = "pof-observation-timeline-card";

    const cabecera = document.createElement("div");
    cabecera.className = "pof-observation-timeline-head";

    const meta = document.createElement("div");
    meta.className = "pof-observation-timeline-meta";

    const fecha = document.createElement("span");
    fecha.className = "pof-observation-timeline-date";
    fecha.textContent = valorHistorial(evento.fecha);

    const usuario = document.createElement("span");
    usuario.className = "pof-observation-timeline-user";
    usuario.textContent = valorHistorial(evento.usuario);

    meta.appendChild(fecha);
    meta.appendChild(usuario);

    const badge = document.createElement("span");
    badge.className =
      "pof-observation-timeline-badge " +
      (evento.tipo_evento === "inicial"
        ? "pof-observation-timeline-badge-initial"
        : "pof-observation-timeline-badge-change");
    badge.textContent =
      evento.label ||
      (evento.tipo_evento === "inicial"
        ? "Observación inicial"
        : "Observación modificada");

    cabecera.appendChild(meta);
    cabecera.appendChild(badge);
    tarjeta.appendChild(cabecera);

    if (evento.tipo_evento === "inicial") {
      tarjeta.appendChild(
        crearBloqueObservacionTimeline(
          "Valor inicial",
          evento.valor_inicial || evento.resumen,
          "pof-observation-timeline-value-initial",
        ),
      );
    } else {
      const resumen = document.createElement("div");
      resumen.className = "pof-observation-timeline-current";
      resumen.textContent = valorHistorial(
        evento.resumen || evento.observacion_nueva,
      );
      tarjeta.appendChild(resumen);

      const acciones = document.createElement("div");
      acciones.className = "pof-observation-timeline-actions";
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "pof-observation-timeline-toggle";
      toggle.setAttribute("aria-expanded", abiertoPorDefecto ? "true" : "false");
      toggle.textContent = abiertoPorDefecto ? "Ocultar cambio" : "Ver cambio";
      acciones.appendChild(toggle);
      tarjeta.appendChild(acciones);

      const detalle = document.createElement("div");
      detalle.className = "pof-observation-timeline-change";
      if (!abiertoPorDefecto) {
        detalle.classList.add("pof-hidden");
      }
      detalle.appendChild(
        crearBloqueObservacionTimeline(
          "Antes",
          evento.observacion_anterior,
          "pof-observation-timeline-value-before",
        ),
      );
      detalle.appendChild(
        crearBloqueObservacionTimeline(
          "Después",
          evento.observacion_nueva,
          "pof-observation-timeline-value-after",
        ),
      );
      tarjeta.appendChild(detalle);

      toggle.addEventListener("click", function () {
        const abrir = detalle.classList.contains("pof-hidden");
        detalle.classList.toggle("pof-hidden", !abrir);
        toggle.setAttribute("aria-expanded", abrir ? "true" : "false");
        toggle.textContent = abrir ? "Ocultar cambio" : "Ver cambio";
      });
    }

    entrada.appendChild(tarjeta);
    return entrada;
  }

  function renderizarHistorialObservacion(
    payload,
    resumen = resumenHistorialObservacion,
    contenido = contenidoHistorialObservacion,
    estado = estadoHistorialObservacion,
  ) {
    limpiarContenido(resumen);
    limpiarContenido(contenido);
    api.clearStatus(estado);

    const cargo = payload.cargo || {};
    if (resumen) {
      agregarResumenHistorial(resumen, "CEIC", cargo.ceic);
      agregarResumenHistorial(
        resumen,
        "Observación actual",
        cargo.observacion_actual,
        true,
      );
    }

    const cargos = Array.isArray(payload.cargos) ? payload.cargos : [];
    const cargosConEventos = cargos.filter(function (item) {
      return Array.isArray(item.movimientos) && item.movimientos.length > 0;
    });

    if (!cargosConEventos.length) {
      api.showStatus(
        estado,
        "info",
        "No hay historial de observación registrado para este cargo.",
      );
      return;
    }

    cargosConEventos.forEach(function (item) {
      const grupo = document.createElement("section");
      grupo.className = "pof-observation-timeline-group";

      if (cargos.length > 1) {
        const titulo = document.createElement("h3");
        titulo.className = "pof-observation-timeline-group-title";
        titulo.textContent =
          "Registro físico #" + valorHistorial(item.id) +
          " · CEIC " + valorHistorial(item.ceic);
        grupo.appendChild(titulo);
      }

      const timeline = document.createElement("div");
      timeline.className = "pof-observation-timeline";
      const eventos = item.movimientos;

      eventos.forEach(function (evento, indice) {
        timeline.appendChild(
          crearEventoObservacionTimeline(
            evento,
            indice,
            false,
          ),
        );
      });

      grupo.appendChild(timeline);
      contenido.appendChild(grupo);
    });
  }

  function renderizarHistorialObservacionInline(payload) {
    if (!contenidoHistorialObservacionInline || !estadoHistorialObservacionInline) {
      return;
    }
    renderizarHistorialCargoPorCiclos(payload, true, {
      resumen: null,
      contenido: contenidoHistorialObservacionInline,
      estado: estadoHistorialObservacionInline,
    });
  }

  async function activarObservacionInline(nombre) {
    const destino = nombre === "historial" ? "historial" : "editor";
    observacionInlineActiva = destino;

    pestaniasObservacionInline.forEach(function (boton) {
      const activa = boton.dataset.cargoObservationMiniTab === destino;
      boton.classList.toggle("pof-admin-observation-mini-tab-active", activa);
      boton.setAttribute("aria-selected", activa ? "true" : "false");
    });

    panelesObservacionInline.forEach(function (panel) {
      panel.classList.toggle(
        "pof-hidden",
        panel.dataset.cargoObservationMiniPanel !== destino,
      );
    });

    if (destino !== "historial" || !cargoActual) {
      return;
    }

    if (historialCargoPayload && historialCargado.cargo) {
      renderizarHistorialObservacionInline(historialCargoPayload);
      return;
    }

    api.showStatus(
      estadoHistorialObservacionInline,
      "warning",
      "Cargando historial de observación...",
    );
    await cargarHistorialPestania("cargo");
  }

  function activarFiltroHistorialCargo(modo) {
    const filtro = modo === "observaciones" ? "observaciones" : "todos";
    filtroHistorialCargoActivo = filtro;

    filtrosHistorialCargo.forEach(function (boton) {
      const activo = boton.dataset.cargoHistoryFilter === filtro;
      boton.classList.toggle("pof-admin-history-filter-active", activo);
      boton.setAttribute("aria-pressed", activo ? "true" : "false");
    });

    historialCargoMovimientosWrap.classList.toggle(
      "pof-hidden",
      filtro === "observaciones",
    );
    historialCargoObservacionesWrap.classList.toggle(
      "pof-hidden",
      filtro !== "observaciones",
    );

    if (
      filtro === "observaciones" &&
      pestaniaActiva === "historiales" &&
      historialActivo === "cargo"
    ) {
      cargarHistorialPestania("observacion");
    }
  }

  function activarHistorial(nombre) {
    if (!cargoActual) {
      return;
    }

    const destino = ["cargo", "localizacion", "zona", "anexo"].includes(nombre)
      ? nombre
      : "cargo";
    historialActivo = destino;

    pestaniasHistorial.forEach(function (boton) {
      const activa = boton.dataset.cargoHistoryTab === destino;
      boton.classList.toggle("pof-admin-history-tab-active", activa);
      boton.setAttribute("aria-selected", activa ? "true" : "false");
    });

    panelesHistorial.forEach(function (panel) {
      panel.classList.toggle(
        "pof-hidden",
        panel.dataset.cargoHistoryPanel !== destino,
      );
    });

    cargarHistorialPestania(destino);
    if (destino === "cargo" && filtroHistorialCargoActivo === "observaciones") {
      cargarHistorialPestania("observacion");
    }
  }

  function reiniciarHistoriales() {
    historialSecuencia += 1;
    historialCargado = {
      cargo: false,
      localizacion: false,
      zona: false,
      anexo: false,
      observacion: false,
    };
    historialCargando = {
      cargo: false,
      localizacion: false,
      zona: false,
      anexo: false,
      observacion: false,
    };
    historialCargoPayload = null;
    observacionInlineActiva = "editor";
    [
      estadoHistorialCargo,
      estadoHistorialLocalizacion,
      estadoHistorialZona,
      estadoHistorialAnexo,
      estadoHistorialObservacion,
      estadoHistorialObservacionInline,
    ].forEach(function (elemento) {
      api.clearStatus(elemento);
    });
    [
      resumenHistorialCargo,
      contenidoHistorialCargo,
      resumenHistorialLocalizacion,
      contenidoHistorialLocalizacion,
      resumenHistorialZona,
      contenidoHistorialZona,
      resumenHistorialAnexo,
      contenidoHistorialAnexo,
      resumenHistorialObservacion,
      contenidoHistorialObservacion,
      contenidoHistorialObservacionInline,
    ].forEach(limpiarContenido);

    pestaniasObservacionInline.forEach(function (boton) {
      const activa = boton.dataset.cargoObservationMiniTab === "editor";
      boton.classList.toggle("pof-admin-observation-mini-tab-active", activa);
      boton.setAttribute("aria-selected", activa ? "true" : "false");
    });
    panelesObservacionInline.forEach(function (panel) {
      panel.classList.toggle(
        "pof-hidden",
        panel.dataset.cargoObservationMiniPanel !== "editor",
      );
    });

    historialActivo = "cargo";
    pestaniasHistorial.forEach(function (boton) {
      const activa = boton.dataset.cargoHistoryTab === "cargo";
      boton.classList.toggle("pof-admin-history-tab-active", activa);
      boton.setAttribute("aria-selected", activa ? "true" : "false");
    });
    panelesHistorial.forEach(function (panel) {
      panel.classList.toggle(
        "pof-hidden",
        panel.dataset.cargoHistoryPanel !== "cargo",
      );
    });
    activarFiltroHistorialCargo("todos");
  }

  function historialContextoVigente(cargoId, secuencia) {
    return Boolean(
      cargoActual &&
      cargoActual.id === cargoId &&
      historialSecuencia === secuencia
    );
  }

  async function precargarHistorialesEnSegundoPlano(
    cargoIdContexto,
    secuenciaContexto,
  ) {
    const ordenPrecarga = ["cargo", "localizacion", "zona", "anexo"];

    for (const nombre of ordenPrecarga) {
      if (!historialContextoVigente(cargoIdContexto, secuenciaContexto)) {
        return;
      }
      await cargarHistorialPestania(nombre);
    }
  }

  function iniciarPrecargaHistorialesEnSegundoPlano() {
    if (!cargoActual) {
      return;
    }

    const cargoIdContexto = cargoActual.id;
    const secuenciaContexto = historialSecuencia;

    window.setTimeout(function () {
      if (!historialContextoVigente(cargoIdContexto, secuenciaContexto)) {
        return;
      }
      precargarHistorialesEnSegundoPlano(
        cargoIdContexto,
        secuenciaContexto,
      ).catch(function (error) {
        if (historialContextoVigente(cargoIdContexto, secuenciaContexto)) {
          api.logError("precargar historiales cargo gestion", error);
        }
      });
    }, 0);
  }

  async function cargarHistorialPestania(nombre) {
    if (!cargoActual || historialCargado[nombre] || historialCargando[nombre]) {
      return;
    }

    if (nombre === "observacion") {
      if (historialCargado.cargo) {
        historialCargado.observacion = true;
        return;
      }
      api.showStatus(
        estadoHistorialObservacion,
        "warning",
        "Cargando historial...",
      );
      await cargarHistorialPestania("cargo");
      return;
    }

    const cargoIdContexto = cargoActual.id;
    const secuenciaContexto = historialSecuencia;
    const localizacionId = cargoActual.localizacion && cargoActual.localizacion.id;
    let url = "";
    let estadoPanelHistorial = null;
    if (nombre === "cargo") {
      url = buildUrl(historialCargoUrlBase, cargoActual.id);
      estadoPanelHistorial = estadoHistorialCargo;
    } else if (nombre === "localizacion" && localizacionId) {
      url = buildCargoQueryUrl(buildUrl(historialLocalizacionUrlBase, localizacionId), cargoIdContexto);
      estadoPanelHistorial = estadoHistorialLocalizacion;
    } else if (nombre === "zona" && localizacionId) {
      url = buildCargoQueryUrl(buildUrl(historialZonaUrlBase, localizacionId), cargoIdContexto);
      estadoPanelHistorial = estadoHistorialZona;
    } else if (nombre === "anexo") {
      estadoPanelHistorial = estadoHistorialAnexo;
      if (!anexoPropietarioActual) {
        historialCargado.anexo = true;
        api.showStatus(
          estadoHistorialAnexo,
          "warning",
          "No hay un propietario Anexo POF válido para este cargo.",
        );
        return;
      }
      const parametros = parametrosPropietarioAnexo(anexoPropietarioActual);
      const historialUrl = new URL(anexoHistorialUrl, window.location.origin);
      historialUrl.search = parametros.toString();
      url = historialUrl.toString();
    }

    if (!url || !estadoPanelHistorial) {
      return;
    }

    historialCargando[nombre] = true;
    api.showStatus(estadoPanelHistorial, "warning", "Cargando historial...");
    try {
      const respuesta = await api.requestJsonRead(url, { cache: "no-store" });
      if (
        secuenciaContexto !== historialSecuencia ||
        !cargoActual ||
        cargoActual.id !== cargoIdContexto
      ) {
        return;
      }
      const payload = respuesta.data || {};
      if (nombre === "cargo") {
        historialCargoPayload = payload;
        renderizarResumenHistorialCargo(payload);
        renderizarHistorialCargoPorCiclos(payload, false);
        renderizarHistorialCargoPorCiclos(payload, true);
        renderizarHistorialObservacionInline(payload);
        historialCargado.observacion = true;
      } else if (nombre === "localizacion") {
        renderizarResumenHistorialLocalizacion(payload);
        renderizarHistorialContextualPorCiclos(
          payload, contenidoHistorialLocalizacion, estadoHistorialLocalizacion,
          function (ciclo, contenido, estado) {
            renderizarMovimientosContextuales(ciclo, contenido, estado, true);
          },
        );
      } else if (nombre === "zona") {
        renderizarHistorialZonaPorCiclos(payload);
      } else if (nombre === "anexo") {
        renderizarHistorialAnexo(payload);
      }
      historialCargado[nombre] = true;
    } catch (error) {
      if (secuenciaContexto === historialSecuencia) {
        const mensajeError = api.formatError(error);
        api.showStatus(estadoPanelHistorial, "error", mensajeError);
        if (nombre === "cargo") {
          api.showStatus(estadoHistorialObservacion, "error", mensajeError);
          api.showStatus(estadoHistorialObservacionInline, "error", mensajeError);
        }
        api.logError("cargar historial " + nombre, error);
      }
    } finally {
      if (secuenciaContexto === historialSecuencia) {
        historialCargando[nombre] = false;
      }
    }
  }

  function activarPestania(nombre) {
    if (!cargoActual && nombre !== "gestion") {
      return;
    }

    const destino = nombre === "historiales" ? "historiales" : "gestion";
    pestaniaActiva = destino;

    pestaniasPrincipales.forEach(function (boton) {
      const activa = boton.dataset.cargoMainTab === destino;
      boton.classList.toggle("pof-admin-cargo-tab-active", activa);
      boton.setAttribute("aria-selected", activa ? "true" : "false");
    });

    panelesPrincipales.forEach(function (panel) {
      panel.classList.toggle(
        "pof-hidden",
        panel.dataset.cargoMainPanel !== destino,
      );
    });

    if (destino === "historiales") {
      activarHistorial(historialActivo);
    }
  }

  function textoEstadoVisual(estado) {
    return estado || "-";
  }

  function actualizarEstadoVisual() {
    const estadoActual = document.getElementById("cargoGestionEstado").value;
    const resumenEstado = document.getElementById("cargoGestionResumenEstado");
    resumenEstado.textContent = textoEstadoVisual(estadoActual);
    resumenEstado.classList.toggle(
      "pof-admin-state-affected",
      estadoActual === "AFECTADO",
    );
    resumenEstado.classList.toggle(
      "pof-admin-state-low",
      estadoActual === "DESAFECTADO",
    );
    estadoPanel.classList.toggle(
      "pof-admin-state-panel-affected",
      estadoActual === "AFECTADO",
    );
    estadoPanel.classList.toggle(
      "pof-admin-state-panel-low",
      estadoActual === "DESAFECTADO",
    );
    btnEstadoToggle.textContent =
      estadoActual === "DESAFECTADO" ? "AFECTAR" : "DESAFECTAR";
    btnEstadoToggle.classList.toggle(
      "pof-admin-state-toggle-affected",
      estadoActual === "DESAFECTADO",
    );
    btnEstadoToggle.classList.toggle(
      "pof-admin-state-toggle-low",
      estadoActual === "AFECTADO",
    );
  }

  function alternarEstadoPendiente() {
    const estadoCampo = document.getElementById("cargoGestionEstado");
    const vaAAfectar = estadoCampo.value === "DESAFECTADO";
    const cantidad = Number(
      document.getElementById("cargoGestionCantidad").value,
    );
    if (vaAAfectar && (!Number.isInteger(cantidad) || cantidad <= 0)) {
      api.showStatus(
        estado,
        "error",
        "Cantidad: Para afectar el cargo, la cantidad debe ser superior a 0.",
      );
      return;
    }

    estadoCampo.value =
      vaAAfectar ? "AFECTADO" : "DESAFECTADO";
    api.clearStatus(estado);
    actualizarEstadoVisual();
    marcarCamposModificados();
  }

  function normalizarTextoCargoModal(valor) {
    return String(valor == null ? "" : valor).trim();
  }

  function normalizarNumeroEnteroCargoModal(valor) {
    const texto = normalizarTextoCargoModal(valor);
    if (!texto) {
      return "";
    }
    if (/^[+-]?\d+(\.0+)?$/.test(texto)) {
      return String(parseInt(texto, 10));
    }
    return texto;
  }

  function normalizarDecimalCargoModal(valor) {
    const texto = normalizarTextoCargoModal(valor).replace(",", ".");
    if (!texto) {
      return "";
    }
    const numero = Number(texto);
    if (!Number.isFinite(numero)) {
      return texto;
    }
    return numero.toFixed(2);
  }

  function obtenerCampoOferta(oferta, campos) {
    for (const campo of campos) {
      const valor = oferta && oferta[campo];
      if (valor !== undefined && valor !== null && String(valor).trim()) {
        return String(valor).trim();
      }
    }
    return "";
  }

  function obtenerNombreOferta(oferta) {
    return obtenerCampoOferta(oferta, ["oferta_real", "oferta"]);
  }

  function normalizarEstadoOfertaGestion(oferta) {
    const valor = obtenerCampoOferta(oferta, [
      "est_oferta",
      "estado_oferta_padron",
      "estado_oferta",
      "oferta_estado",
    ]);
    const normalizado = String(valor || "")
      .trim()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toUpperCase();

    if (
      normalizado === "A" ||
      normalizado.includes("ACTIVA") ||
      normalizado.includes("ACTIVO") ||
      normalizado.includes("VIGENTE")
    ) {
      return {
        codigo: "ACTIVA",
        texto: "ACTIVA",
        clase: "pof-offer-status-active",
      };
    }

    if (normalizado === "B" || normalizado.includes("BAJA")) {
      return {
        codigo: "BAJA",
        texto: "BAJA",
        clase: "pof-offer-status-low",
      };
    }

    return {
      codigo: "SIN_DATO",
      texto: "SIN DATO",
      clase: "pof-offer-status-unknown",
    };
  }

  function claveOfertaCargo(oferta) {
    return [
      obtenerCampoOferta(oferta, ["id_oferta_local", "id"]),
      obtenerCampoOferta(oferta, ["id_localizacion"]),
      obtenerCampoOferta(oferta, ["padron_cueanexo", "cueanexo"]),
      obtenerCampoOferta(oferta, ["cuof_loc", "cuof"]),
      obtenerNombreOferta(oferta),
    ].join("|");
  }

  function obtenerOfertasSeleccionadas() {
    return Array.from(
      ofertasOpciones.querySelectorAll('input[type="checkbox"]:checked'),
    )
      .map(function (checkbox) {
        return ofertasDisponibles[Number(checkbox.dataset.ofertaIndex)];
      })
      .filter(Boolean);
  }

  function normalizarOfertasCargoModal(ofertas) {
    if (!Array.isArray(ofertas)) {
      return "";
    }
    return ofertas.map(claveOfertaCargo).sort().join("||");
  }

  function cerrarOpcionesOfertas() {
    ofertasOpciones.classList.add("pof-hidden");
    ofertasToggle.setAttribute("aria-expanded", "false");
  }

  function actualizarResumenOfertas() {
    const seleccionadas = obtenerOfertasSeleccionadas();
    const nombres = seleccionadas
      .map(obtenerNombreOferta)
      .filter(Boolean);
    const sinSeleccion = requiereOfertas && !seleccionadas.length;

    ofertasResumen.textContent = nombres.length
      ? nombres.join(", ")
      : "Seleccioná al menos una oferta";
    ofertasSelector.classList.toggle(
      "pof-admin-offers-invalid",
      sinSeleccion,
    );
    ofertasError.textContent = sinSeleccion
      ? "Debe mantener al menos una oferta seleccionada."
      : "";
    ofertasError.classList.toggle("pof-hidden", !sinSeleccion);
  }

  function renderizarOfertasCargo(cargo) {
    requiereOfertas = Boolean(cargo.requiere_ofertas);
    ofertasCatalogoCargado = Boolean(cargo.ofertas_catalogo_cargado);
    ofertasCatalogoCargando = false;
    ofertasDisponibles = Array.isArray(cargo.ofertas_disponibles)
      ? cargo.ofertas_disponibles
      : [];
    ofertasCampo.classList.toggle("pof-hidden", !requiereOfertas);
    cerrarOpcionesOfertas();

    if (!requiereOfertas) {
      ofertasOpciones.innerHTML = "";
      actualizarResumenOfertas();
      return;
    }

    if (!ofertasDisponibles.length) {
      ofertasOpciones.innerHTML =
        '<div class="pof-admin-offers-empty">No hay ofertas disponibles para este CUEANEXO.</div>';
      actualizarResumenOfertas();
      return;
    }

    function renderizarOpcionOferta(oferta, index) {
        const nombre = obtenerNombreOferta(oferta) || "Oferta sin identificar";
        const cuof = obtenerCampoOferta(oferta, ["cuof_loc", "cuof"]);
        const estadoOferta = normalizarEstadoOfertaGestion(oferta);
        return `
          <label class="pof-admin-offers-option">
            <input type="checkbox"
                   data-oferta-index="${index}"
                   ${oferta.seleccionada ? "checked" : ""}>
            <div class="pof-admin-offers-option-content">
              <div class="pof-admin-offers-option-title-row">
                <strong>${escaparHtml(nombre)}</strong>
                <span class="pof-offer-status-badge ${estadoOferta.clase}">
                  ${estadoOferta.texto}
                </span>
              </div>
              ${cuof ? `<small>CUOF: ${escaparHtml(cuof)}</small>` : ""}
            </div>
          </label>
        `;
    }

    const ofertasIndexadas = ofertasDisponibles.map(function (oferta, index) {
      return { oferta, index };
    });
    const clasificaPorReunida = ofertasDisponibles.some(function (oferta) {
      return Object.prototype.hasOwnProperty.call(oferta, "oferta_sugerida");
    });

    if (clasificaPorReunida) {
      const sugeridas = ofertasIndexadas.filter(function (item) {
        return item.oferta.oferta_sugerida === true;
      });
      const otras = ofertasIndexadas.filter(function (item) {
        return item.oferta.oferta_sugerida !== true;
      });
      const renderizarGrupo = function (titulo, items, mensajeVacio) {
        const opciones = items.length
          ? items
              .map(function (item) {
                return renderizarOpcionOferta(item.oferta, item.index);
              })
              .join("")
          : `<div class="pof-admin-offers-empty">${escaparHtml(mensajeVacio)}</div>`;
        return `
          <div class="pof-admin-offers-empty"><strong>${escaparHtml(titulo)}</strong></div>
          ${opciones}
        `;
      };

      ofertasOpciones.innerHTML =
        renderizarGrupo(
          "Ofertas sugeridas",
          sugeridas,
          "No hay ofertas sugeridas para el nivel de la POF.",
        ) + renderizarGrupo("Otras ofertas", otras, "No hay otras ofertas.");
    } else {
      ofertasOpciones.innerHTML = ofertasIndexadas
        .map(function (item) {
          return renderizarOpcionOferta(item.oferta, item.index);
        })
        .join("");
    }
    actualizarResumenOfertas();
  }

  async function cargarCatalogoOfertasCargo() {
    if (
      !cargoActual ||
      !requiereOfertas ||
      ofertasCatalogoCargado ||
      ofertasCatalogoCargando
    ) {
      return ofertasCatalogoCargado;
    }

    const cargoId = Number(cargoActual.id);
    const secuencia = ++ofertasSecuencia;
    ofertasCatalogoCargando = true;
    ofertasToggle.disabled = true;
    ofertasOpciones.innerHTML =
      '<div class="pof-admin-offers-empty">Cargando ofertas de padrón...</div>';

    try {
      const respuesta = await api.requestJsonRead(
        buildUrl(ofertasCatalogoUrlBase, cargoId),
        { cache: "no-store" },
      );
      if (
        secuencia !== ofertasSecuencia ||
        !cargoActual ||
        Number(cargoActual.id) !== cargoId
      ) {
        return false;
      }

      const payload = respuesta.data || {};
      cargoActual.oferta = payload.oferta || cargoActual.oferta || "";
      cargoActual.ofertas_seleccionadas = Array.isArray(
        payload.ofertas_seleccionadas,
      )
        ? payload.ofertas_seleccionadas
        : [];
      cargoActual.ofertas_disponibles = Array.isArray(
        payload.ofertas_disponibles,
      )
        ? payload.ofertas_disponibles
        : [];
      cargoActual.requiere_ofertas = Boolean(payload.requiere_ofertas);
      cargoActual.ofertas_catalogo_cargado = true;
      renderizarOfertasCargo(cargoActual);
      valoresOriginales.ofertas_seleccionadas = normalizarOfertasCargoModal(
        obtenerOfertasSeleccionadas(),
      );
      marcarCamposModificados();
      return true;
    } catch (error) {
      if (
        secuencia === ofertasSecuencia &&
        cargoActual &&
        Number(cargoActual.id) === cargoId
      ) {
        ofertasCatalogoCargando = false;
        ofertasCatalogoCargado = false;
        ofertasOpciones.innerHTML =
          '<div class="pof-admin-offers-empty">No se pudieron cargar las ofertas. Volvé a intentarlo.</div>';
        api.logError("cargar catalogo ofertas cargo gestion", error);
      }
      return false;
    } finally {
      if (
        secuencia === ofertasSecuencia &&
        cargoActual &&
        Number(cargoActual.id) === cargoId
      ) {
        ofertasCatalogoCargando = false;
        ofertasToggle.disabled = enviando || !requiereOfertas;
        actualizarBotonGuardarCargo();
      }
    }
  }

  function normalizarEstadoCargoModal(estado) {
    return {
      cantidad: normalizarNumeroEnteroCargoModal(estado.cantidad),
      unidad_cantidad: normalizarTextoCargoModal(
        estado.unidad_cantidad,
      ).toUpperCase(),
      estado_pof: normalizarTextoCargoModal(estado.estado_pof).toUpperCase(),
      observacion: normalizarTextoCargoModal(estado.observacion),
      ofertas_seleccionadas: normalizarOfertasCargoModal(
        estado.ofertas_seleccionadas,
      ),
    };
  }

  function obtenerEstadoCargoModal() {
    return normalizarEstadoCargoModal({
      cantidad: document.getElementById("cargoGestionCantidad").value,
      unidad_cantidad: document.getElementById("cargoGestionUnidad").value,
      estado_pof: document.getElementById("cargoGestionEstado").value,
      observacion: document.getElementById("cargoGestionObservacion").value,
      ofertas_seleccionadas: obtenerOfertasSeleccionadas(),
    });
  }

  function hayCambiosCargoModal() {
    const estadoActual = obtenerEstadoCargoModal();
    return Object.keys(estadoActual).some(function (campo) {
      return estadoActual[campo] !== (valoresOriginales[campo] || "");
    });
  }

  function hayCambiosGestionModal() {
    return (
      hayCambiosCargoModal() ||
      hayCambiosZonaModal() ||
      hayCambiosSeleccionAnexo()
    );
  }

  function setBotonDeshabilitadoPof(boton, deshabilitado) {
    boton.disabled = deshabilitado;
    boton.setAttribute("aria-disabled", deshabilitado ? "true" : "false");
    boton.classList.toggle("pof-btn-disabled", deshabilitado);
  }

  function actualizarBotonGuardarCargo() {
    const cargoModificado = hayCambiosCargoModal();
    const hayCambios =
      cargoModificado ||
      hayCambiosZonaModal() ||
      hayCambiosSeleccionAnexo();
    const ofertasValidas =
      !cargoModificado ||
      !requiereOfertas ||
      obtenerOfertasSeleccionadas().length > 0;
    const zonaValida = zonaSeleccionValidaParaGuardar();

    setBotonDeshabilitadoPof(
      btnGuardar,
      enviando ||
        !cargoActual ||
        !hayCambios ||
        !ofertasValidas ||
        !zonaValida ||
        ofertasCatalogoCargando ||
        zonaCatalogoCargando ||
        anexoCreandoCodigo,
    );
  }

  function guardarValoresOriginales() {
    valoresOriginales = obtenerEstadoCargoModal();
  }

  function marcarCamposModificados() {
    const estadoActual = obtenerEstadoCargoModal();
    const camposEstado = {
      cargoGestionEstado: "estado_pof",
      cargoGestionCantidad: "cantidad",
      cargoGestionUnidad: "unidad_cantidad",
      cargoGestionObservacion: "observacion",
    };
    Object.keys(camposEstado).forEach(function (id) {
      const clave = camposEstado[id];
      const modificado =
        estadoActual[clave] !== (valoresOriginales[clave] || "");
      const idVisual = camposVisualesModificados[id];
      if (idVisual) {
        document
          .getElementById(idVisual)
          .classList.toggle("pof-admin-field-modified", modificado);
      }
    });
    ofertasSelector.classList.toggle(
      "pof-admin-field-modified",
      estadoActual.ofertas_seleccionadas !==
        (valoresOriginales.ofertas_seleccionadas || ""),
    );

    const zonaModificada = hayCambiosZonaModal();
    zonaTipo.classList.toggle("pof-admin-field-modified", zonaModificada);
    zonaSelect.classList.toggle("pof-admin-field-modified", zonaModificada);

    const anexoModificado = hayCambiosSeleccionAnexo();
    anexoSelector.classList.toggle(
      "pof-admin-field-modified",
      anexoModificado,
    );
    anexoSeleccionadosInput.classList.toggle(
      "pof-admin-field-modified",
      anexoModificado,
    );

    actualizarResumenOfertas();
    const hayCambios = hayCambiosGestionModal();
    cambiosPendientes.classList.toggle("pof-hidden", !hayCambios);
    actualizarBotonGuardarCargo();
  }

  function actualizarTotal() {
    const cantidad = parseInt(
      document.getElementById("cargoGestionCantidad").value || 0,
      10,
    );
    const puntos = Number(
      document.getElementById("cargoGestionPuntos").value || 0,
    );
    document.getElementById("cargoGestionTotal").value = (
      cantidad * puntos
    ).toFixed(2);
  }

  function actualizarAdvertenciaCantidadCero() {
    const cantidad = document.getElementById("cargoGestionCantidad").value;
    if (/^0+$/.test(cantidad)) {
      api.showStatus(
        estado,
        "warning",
        "Advertencia: la cantidad es 0. Al guardar los cambios, el cargo quedará automáticamente DESAFECTADO.",
      );
      advertenciaCantidadCeroVisible = true;
      return;
    }
    if (advertenciaCantidadCeroVisible) {
      api.clearStatus(estado);
      advertenciaCantidadCeroVisible = false;
    }
  }

  async function aplicarCargo(cargo) {
    ofertasSecuencia += 1;
    cargoActual = cargo;
    document.getElementById("cargoGestionId").value = cargo.id;
    document.getElementById("cargoGestionCeic").value = cargo.ceic || "";
    ceicBusqueda.value = cargo.ceic || "";
    ultimoTextoCeic = ceicBusqueda.value.trim();
    document.getElementById("cargoGestionEstado").value =
      cargo.estado_pof || "AFECTADO";
    document.getElementById("cargoGestionTotal").value = cargo.total || "0.00";
    document.getElementById("cargoGestionCargo").value = cargo.cargo || "";
    document.getElementById("cargoGestionCantidad").value =
      cargo.cantidad || "";
    document.getElementById("cargoGestionUnidad").value =
      cargo.unidad_cantidad || "CARGO";
    document.getElementById("cargoGestionPuntos").value =
      cargo.puntos_asignados || "";
    document.getElementById("cargoGestionObservacion").value =
      cargo.observacion || "";
    document.getElementById("cargoGestionSubtituloCabecera").textContent =
      cargo.cabecera || "-";
    document.getElementById("cargoGestionSubtituloActualizado").textContent =
      "\u00daltima modificaci\u00f3n: " + formatearFecha(cargo.actualizado_en);

    const localizacion = cargo.localizacion || {};
    if (historialLocalizacionLabel) {
      historialLocalizacionLabel.textContent =
        localizacion.tipo_identidad === "CUOF"
          ? "Cargos del CUOF"
          : "Cargos del CUEANEXO";
    }
    document.getElementById("cargoGestionResumenCabecera").textContent =
      cargo.cabecera || "-";
    document.getElementById("cargoGestionResumenCueanexo").textContent =
      localizacion.cueanexo || "-";
    document.getElementById("cargoGestionResumenCuof").textContent =
      localizacion.cuof || "-";
    document.getElementById("cargoGestionResumenEstablecimiento").textContent =
      localizacion.establecimiento || "-";
    aplicarZonaCargo(cargo.zona_educativa || null);
    renderizarOfertasCargo(cargo);
    actualizarEstadoVisual();
    guardarValoresOriginales();
    marcarCamposModificados();

    cargarAnexoCargo(cargo).catch(function (error) {
      api.logError("cargar anexo pof cargo gestion en segundo plano", error);
    });
    iniciarPrecargaHistorialesEnSegundoPlano();
  }

  function abrirModal() {
    modal.classList.remove("pof-hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("pof-modal-open");
  }

  function cerrarModal() {
    cerrarModalEliminar();
    const triggerAnterior = triggerActivo;

    modal.classList.add("pof-hidden");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("pof-modal-open");

    ofertasSecuencia += 1;
    cargoActual = null;
    valoresOriginales = {};
    triggerActivo = null;
    ofertasDisponibles = [];
    requiereOfertas = false;
    ofertasCatalogoCargado = false;
    ofertasCatalogoCargando = false;
    ofertasCampo.classList.add("pof-hidden");
    ofertasOpciones.innerHTML = "";
    cerrarOpcionesOfertas();

    setEnviando(false);
    resetearZonaCargo();
    resetearAnexoCargo();
    api.clearStatus(estado);
    reiniciarHistoriales();
    activarPestania("gestion");
    advertenciaCantidadCeroVisible = false;

    if (triggerAnterior && document.contains(triggerAnterior)) {
      triggerAnterior.focus({ preventScroll: true });
    }
  }

  async function abrirModalEliminar() {
    if (!cargoActual || enviando) {
      return;
    }
    const cargoId = String(cargoActual.id);
    const secuencia = ++eliminacionSecuencia;
    cargoIdEliminacionConfirmable = null;
    btnConfirmarEliminar.disabled = true;
    impactoEliminacionTexto.textContent = "Consultando el impacto real de la eliminación...";
    modalEliminar.classList.remove("pof-hidden");
    modalEliminar.setAttribute("aria-hidden", "false");
    modalEliminar.querySelector("[data-eliminar-cancelar]").focus();

    try {
      const url = new URL(buildUrl(detalleUrlBase, cargoId), window.location.origin);
      url.searchParams.set("impacto_eliminacion", "1");
      const respuesta = await api.requestJsonRead(url.toString(), { cache: "no-store" });
      if (
        secuencia !== eliminacionSecuencia || !cargoActual ||
        String(cargoActual.id) !== cargoId
      ) {
        return;
      }
      const impacto = (respuesta.data || {}).impacto_eliminacion;
      if (
        !impacto || String(impacto.cargo_id) !== cargoId ||
        !Number.isInteger(impacto.cantidad_movimientos) || impacto.cantidad_movimientos < 0 ||
        typeof impacto.puede_eliminar !== "boolean" ||
        typeof impacto.mensaje !== "string" || !impacto.mensaje
      ) {
        throw new Error("No se pudo verificar el impacto de la eliminación.");
      }
      impactoEliminacionTexto.textContent = impacto.mensaje;
      if (impacto.puede_eliminar) {
        cargoIdEliminacionConfirmable = cargoId;
        btnConfirmarEliminar.disabled = enviando;
        if (!enviando) {
          btnConfirmarEliminar.focus();
        }
      }
    } catch (error) {
      if (secuencia === eliminacionSecuencia && cargoActual && String(cargoActual.id) === cargoId) {
        impactoEliminacionTexto.textContent = api.formatError(error);
        api.logError("consultar impacto eliminación cargo", error);
      }
    }
  }

  function cerrarModalEliminar() {
    eliminacionSecuencia += 1;
    cargoIdEliminacionConfirmable = null;
    btnConfirmarEliminar.disabled = true;
    modalEliminar.classList.add("pof-hidden");
    modalEliminar.setAttribute("aria-hidden", "true");
  }

  async function cargarCargo(cargoId) {
    cerrarModalEliminar();
    reiniciarHistoriales();
    activarPestania("gestion");
    abrirModal();
    api.clearStatus(estado);
    setEnviando(true);
    api.showStatus(estado, "warning", "Cargando detalle del cargo...");

    try {
      const data = await api.requestJson(buildUrl(detalleUrlBase, cargoId), {
        cache: "no-store",
      });
      await aplicarCargo(data.data.cargo);
      api.clearStatus(estado);
      actualizarAdvertenciaCantidadCero();
    } catch (error) {
      api.showStatus(estado, "error", api.formatError(error));
      api.logError("cargar cargo gestion", error);
    } finally {
      setEnviando(false);
    }
  }

  /**
   * Ejecuta una modificación o eliminación del cargo usando el CRUD compartido.
   *
   * - En Administración conserva el refresco normal de la pantalla.
   * - En Detalle emite un evento para conservar el Anexo/CUOF abierto.
   * - No duplica validaciones ni endpoints.
   */
  async function ejecutarAccionCargo(url, payload, accion) {
    setEnviando(true);
    api.clearStatus(estado);

    try {
      const data = await api.requestJson(url, {
        method: "POST",
        body: payload,
      });

      const respuesta = data.data || {};

      // Toda mutación puede cambiar Cargo, Zona o Anexo POF. Invalidamos los
      // historiales ya cargados y cualquier respuesta tardía antes de aplicar
      // el estado fresco devuelto por el servidor.
      reiniciarHistoriales();

      if (respuesta.cargo) {
        await aplicarCargo(respuesta.cargo);
      }

      const detalleEvento = {
        accion: accion,
        cargoId: cargoActual ? cargoActual.id : null,
        trigger: triggerActivo,
        respuesta: respuesta,
      };

      api.showStatus(
        estado,
        "success",
        data.mensaje || "Operación realizada correctamente.",
      );

      window.setTimeout(function () {
        if (successMode === "event") {
          cerrarModalEliminar();

          const evento = new CustomEvent("pof:cargo-gestion-actualizado", {
            detail: detalleEvento,
          });

          cerrarModal();
          document.dispatchEvent(evento);
          return;
        }

        window.location.reload();
      }, 900);
    } catch (error) {
      api.showStatus(estado, "error", api.formatError(error));
      api.logError("accion cargo gestion", error);
      setEnviando(false);
    }
  }

  document.addEventListener("click", function (event) {
    const boton = event.target.closest("[data-cargo-gestion]");

    if (!boton || enviando) {
      return;
    }

    const cargoId = String(boton.dataset.cargoId || "").trim();

    if (!/^[1-9]\d*$/.test(cargoId)) {
      return;
    }

    triggerActivo = boton;
    cargarCargo(cargoId);
  });

  pestaniasPrincipales.forEach(function (boton) {
    boton.addEventListener("click", function () {
      if (enviando) {
        return;
      }
      activarPestania(boton.dataset.cargoMainTab || "gestion");
    });
  });

  pestaniasHistorial.forEach(function (boton) {
    boton.addEventListener("click", function () {
      if (enviando) {
        return;
      }
      activarHistorial(boton.dataset.cargoHistoryTab || "cargo");
    });
  });

  filtrosHistorialCargo.forEach(function (boton) {
    boton.addEventListener("click", function () {
      if (enviando) {
        return;
      }
      activarFiltroHistorialCargo(
        boton.dataset.cargoHistoryFilter || "todos",
      );
    });
  });

  pestaniasObservacionInline.forEach(function (boton) {
    boton.addEventListener("click", function () {
      if (enviando) {
        return;
      }
      void activarObservacionInline(
        boton.dataset.cargoObservationMiniTab || "editor",
      );
    });
  });

  document.querySelectorAll("[data-cargo-cerrar]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      if (!enviando) {
        cerrarModal();
      }
    });
  });

  modal.addEventListener("click", function (event) {
    if (event.target === modal && !enviando) {
      cerrarModal();
    }
  });

  camposEditables.forEach(function (id) {
    const campo = document.getElementById(id);
    campo.addEventListener("input", function () {
      if (id === "cargoGestionCantidad") {
        actualizarTotal();
        actualizarAdvertenciaCantidadCero();
      }
      if (id === "cargoGestionEstado") {
        actualizarEstadoVisual();
      }
      marcarCamposModificados();
    });
    campo.addEventListener("change", function () {
      if (id === "cargoGestionEstado") {
        actualizarEstadoVisual();
      }
      marcarCamposModificados();
    });
  });

  ofertasToggle.addEventListener("click", async function () {
    if (enviando || !requiereOfertas || ofertasCatalogoCargando) {
      return;
    }

    const abrir = ofertasOpciones.classList.contains("pof-hidden");
    if (abrir && !ofertasCatalogoCargado) {
      const cargado = await cargarCatalogoOfertasCargo();
      if (!cargado) {
        ofertasOpciones.classList.remove("pof-hidden");
        ofertasToggle.setAttribute("aria-expanded", "true");
        return;
      }
    }

    ofertasOpciones.classList.toggle("pof-hidden", !abrir);
    ofertasToggle.setAttribute("aria-expanded", abrir ? "true" : "false");
  });

  ofertasOpciones.addEventListener("change", function (event) {
    if (!event.target.matches('input[type="checkbox"]')) {
      return;
    }
    marcarCamposModificados();
  });

  document.addEventListener("click", function (event) {
    if (!ofertasSelector.contains(event.target)) {
      cerrarOpcionesOfertas();
    }
    if (!anexoSelector.contains(event.target)) {
      cerrarOpcionesAnexo();
    }
  });

  btnEstadoToggle.addEventListener("click", alternarEstadoPendiente);

  zonaTipo.addEventListener("change", function () {
    if (enviando) {
      return;
    }
    zonaEdicionIniciada = true;
    zonaCatalogoTipoCargado = "";
    cargarCatalogoZona(this.value, "");
  });

  function asegurarCatalogoZonaActual() {
    if (
      enviando ||
      zonaCatalogoCargando ||
      !zonaAsignada(zonaActual)
    ) {
      return;
    }
    const tipo = String(zonaTipo.value || "").trim().toUpperCase();
    if (!tipo || zonaCatalogoTipoCargado === tipo) {
      return;
    }
    cargarCatalogoZona(tipo, String(zonaActual.zona || ""));
  }

  zonaSelect.addEventListener("focus", asegurarCatalogoZonaActual);
  zonaSelect.addEventListener("pointerdown", asegurarCatalogoZonaActual);

  zonaSelect.addEventListener("change", function () {
    zonaEdicionIniciada = true;
    actualizarPuntosZonaSeleccionada();
  });

  anexoToggle.addEventListener("click", function () {
    if (enviando || anexoCargando || anexoCreandoCodigo || !anexoPropietarioActual) {
      return;
    }
    const abrir = anexoOpciones.classList.contains("pof-hidden");
    anexoOpciones.classList.toggle("pof-hidden", !abrir);
    anexoToggle.setAttribute("aria-expanded", abrir ? "true" : "false");
  });

  anexoOpciones.addEventListener("change", function (event) {
    const checkbox = event.target.closest("input[data-anexo-catalogo-id]");
    if (!checkbox || enviando || anexoCargando || anexoCreandoCodigo) {
      return;
    }

    const catalogoId = Number(checkbox.dataset.anexoCatalogoId || 0);
    if (!catalogoId) {
      return;
    }

    if (checkbox.checked) {
      anexoSeleccionados.add(catalogoId);
    } else {
      anexoSeleccionados.delete(catalogoId);
    }
    renderizarAnexoCargo();
    marcarCamposModificados();
  });

  anexoOpciones.addEventListener("click", function (event) {
    const botonCrear = event.target.closest("[data-anexo-crear-nuevo]");
    if (!botonCrear) {
      return;
    }
    event.preventDefault();
    abrirAltaAnexo();
  });

  btnAnexoCrear.addEventListener("click", crearNuevoCodigoAnexo);

  btnAnexoCancelarCrear.addEventListener("click", function () {
    cerrarAltaAnexo(true);
  });

  anexoNuevoCodigo.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      crearNuevoCodigoAnexo();
    } else if (event.key === "Escape") {
      event.preventDefault();
      cerrarAltaAnexo(true);
    }
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (
      !cargoActual ||
      enviando ||
      zonaCatalogoCargando ||
      anexoCreandoCodigo ||
      !hayCambiosGestionModal()
    ) {
      return;
    }

    if (!zonaSeleccionValidaParaGuardar()) {
      api.showStatus(
        estadoZona,
        "error",
        "Zona Educativa: completá una zona válida o dejá tipo y zona vacíos."
      );
      actualizarBotonGuardarCargo();
      return;
    }

    const cargoModificado = hayCambiosCargoModal();
    const zonaModificada = hayCambiosZonaModal();
    const anexoModificado = hayCambiosSeleccionAnexo();
    const payload = {};

    if (cargoModificado) {
      const ofertasSeleccionadas = obtenerOfertasSeleccionadas();
      if (requiereOfertas && !ofertasSeleccionadas.length) {
        actualizarResumenOfertas();
        api.showStatus(
          estado,
          "error",
          "Ofertas: Debe mantener al menos una oferta seleccionada.",
        );
        return;
      }

      const cantidad = document.getElementById("cargoGestionCantidad").value;
      if (!/^\d+$/.test(cantidad)) {
        api.showStatus(
          estado,
          "error",
          "Cantidad: La cantidad debe ser un número entero.",
        );
        return;
      }

      let estadoPof = document.getElementById("cargoGestionEstado").value;
      if (!["AFECTADO", "DESAFECTADO"].includes(estadoPof)) {
        api.showStatus(
          estado,
          "error",
          "Estado: El estado indicado no es válido.",
        );
        return;
      }
      if (Number(cantidad) === 0 && estadoPof !== "DESAFECTADO") {
        estadoPof = "DESAFECTADO";
        document.getElementById("cargoGestionEstado").value = estadoPof;
        actualizarEstadoVisual();
      }

      payload.cantidad = cantidad;
      payload.unidad_cantidad =
        document.getElementById("cargoGestionUnidad").value;
      payload.estado_pof = estadoPof;
      payload.observacion =
        document.getElementById("cargoGestionObservacion").value;

      if (requiereOfertas) {
        payload.ofertas_seleccionadas = ofertasSeleccionadas.map(
          function (oferta) {
            return {
              id_localizacion: obtenerCampoOferta(oferta, ["id_localizacion"]),
              id_oferta_local: obtenerCampoOferta(oferta, [
                "id_oferta_local",
                "id",
              ]),
              padron_cueanexo: obtenerCampoOferta(oferta, [
                "padron_cueanexo",
                "cueanexo",
              ]),
              cuof_loc: obtenerCampoOferta(oferta, ["cuof_loc", "cuof"]),
            };
          },
        );
      }
    }

    if (zonaModificada) {
      payload.zona_educativa = construirPayloadZonaPendiente();
    }

    if (anexoModificado) {
      payload.anexo_pof = {
        catalogo_ids: Array.from(anexoSeleccionados).sort(function (a, b) {
          return Number(a) - Number(b);
        }),
      };
    }

    ejecutarAccionCargo(
      buildUrl(modificarUrlBase, cargoActual.id),
      payload,
      "modificar",
    );
  });

  btnEliminar.addEventListener("click", function () {
    if (cargoActual && !enviando) {
      abrirModalEliminar();
    }
  });

  btnConfirmarEliminar.addEventListener("click", function () {
    if (
      cargoActual && !enviando && !btnConfirmarEliminar.disabled &&
      cargoIdEliminacionConfirmable === String(cargoActual.id)
    ) {
      cerrarModalEliminar();
      ejecutarAccionCargo(
        buildUrl(eliminarUrlBase, cargoActual.id),
        {},
        "eliminar",
      );
    }
  });

  document
    .querySelectorAll("[data-eliminar-cancelar]")
    .forEach(function (boton) {
      boton.addEventListener("click", cerrarModalEliminar);
    });

  modalEliminar.addEventListener("click", function (event) {
    if (event.target === modalEliminar && !enviando) {
      cerrarModalEliminar();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (
      event.key === "Escape" &&
      !modalEliminar.classList.contains("pof-hidden") &&
      !enviando
    ) {
      cerrarModalEliminar();
    }
  });
})();
