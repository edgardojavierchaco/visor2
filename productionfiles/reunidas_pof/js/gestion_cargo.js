(function () {
  "use strict";

  const api = window.pofApi || null;
  const modal = document.querySelector("[data-cargo-gestion-modal]");

  if (!api || !modal) {
    return;
  }

  const detalleUrlBase = modal.dataset.detalleUrlBase || "";
  const modificarUrlBase = modal.dataset.modificarUrlBase || "";
  const eliminarUrlBase = modal.dataset.eliminarUrlBase || "";
  const successMode = modal.dataset.successMode || "reload";

  if (!detalleUrlBase || !modificarUrlBase || !eliminarUrlBase) {
    return;
  }

  const form = document.getElementById("formGestionCargo");
  const estado = document.getElementById("estadoGestionCargo");
  const btnGuardar = document.getElementById("btnGuardarCargo");
  const btnEliminar = document.getElementById("btnEliminarCargo");
  const modalEliminar = document.getElementById(
    "modalConfirmarEliminacionCargo",
  );
  const btnConfirmarEliminar = document.getElementById(
    "btnConfirmarEliminarCargo",
  );
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
  let valoresOriginales = {};
  let enviando = false;
  let ultimoTextoCeic = "";
  let triggerActivo = null;
  let ofertasDisponibles = [];
  let requiereOfertas = false;
  let advertenciaCantidadCeroVisible = false;

  function buildUrl(base, cargoId) {
    return base.replace("/0/", "/" + cargoId + "/");
  }

  function setEnviando(valor) {
    enviando = valor;
    btnEliminar.disabled = valor;
    btnConfirmarEliminar.disabled = valor;
    btnEstadoToggle.disabled = valor;
    ofertasToggle.disabled = valor || !requiereOfertas;
    ofertasOpciones
      .querySelectorAll('input[type="checkbox"]')
      .forEach(function (checkbox) {
        checkbox.disabled = valor;
      });
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
        return `
          <label class="pof-admin-offers-option">
            <input type="checkbox"
                   data-oferta-index="${index}"
                   ${oferta.seleccionada ? "checked" : ""}>
            <span>
              <strong>${escaparHtml(nombre)}</strong>
              ${cuof ? `<small>CUOF: ${escaparHtml(cuof)}</small>` : ""}
            </span>
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
          "No hay ofertas sugeridas para el nivel de la Reunida.",
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

  function setBotonDeshabilitadoPof(boton, deshabilitado) {
    boton.disabled = deshabilitado;
    boton.setAttribute("aria-disabled", deshabilitado ? "true" : "false");
    boton.classList.toggle("pof-btn-disabled", deshabilitado);
  }

  function actualizarBotonGuardarCargo() {
    const hayCambios = hayCambiosCargoModal();
    const ofertasValidas =
      !requiereOfertas || obtenerOfertasSeleccionadas().length > 0;
    setBotonDeshabilitadoPof(
      btnGuardar,
      enviando || !cargoActual || !hayCambios || !ofertasValidas,
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
    actualizarResumenOfertas();
    const hayCambios = hayCambiosCargoModal();
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

  function aplicarCargo(cargo) {
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
    document.getElementById("cargoGestionResumenCabecera").textContent =
      cargo.cabecera || "-";
    document.getElementById("cargoGestionResumenCueanexo").textContent =
      localizacion.cueanexo || "-";
    document.getElementById("cargoGestionResumenCuof").textContent =
      localizacion.cuof || "-";
    document.getElementById("cargoGestionResumenEstablecimiento").textContent =
      localizacion.establecimiento || "-";
    renderizarOfertasCargo(cargo);
    actualizarEstadoVisual();
    guardarValoresOriginales();
    marcarCamposModificados();
  }

  function abrirModal() {
    modal.classList.remove("pof-hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("pof-modal-open");
  }

  function cerrarModal() {
    const triggerAnterior = triggerActivo;

    modal.classList.add("pof-hidden");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("pof-modal-open");

    cargoActual = null;
    valoresOriginales = {};
    triggerActivo = null;
    ofertasDisponibles = [];
    requiereOfertas = false;
    ofertasCampo.classList.add("pof-hidden");
    ofertasOpciones.innerHTML = "";
    cerrarOpcionesOfertas();

    setEnviando(false);
    api.clearStatus(estado);
    advertenciaCantidadCeroVisible = false;

    if (triggerAnterior && document.contains(triggerAnterior)) {
      triggerAnterior.focus({ preventScroll: true });
    }
  }

  function abrirModalEliminar() {
    modalEliminar.classList.remove("pof-hidden");
    modalEliminar.setAttribute("aria-hidden", "false");
    btnConfirmarEliminar.focus();
  }

  function cerrarModalEliminar() {
    modalEliminar.classList.add("pof-hidden");
    modalEliminar.setAttribute("aria-hidden", "true");
  }

  async function cargarCargo(cargoId) {
    abrirModal();
    api.clearStatus(estado);
    setEnviando(true);
    api.showStatus(estado, "warning", "Cargando detalle del cargo...");

    try {
      const data = await api.requestJson(buildUrl(detalleUrlBase, cargoId));
      aplicarCargo(data.data.cargo);
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

      if (respuesta.cargo) {
        aplicarCargo(respuesta.cargo);
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

  document.querySelectorAll("[data-cargo-cerrar]").forEach(function (boton) {
    boton.addEventListener("click", cerrarModal);
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

  ofertasToggle.addEventListener("click", function () {
    if (enviando || !requiereOfertas) {
      return;
    }
    const abrir = ofertasOpciones.classList.contains("pof-hidden");
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
  });

  btnEstadoToggle.addEventListener("click", alternarEstadoPendiente);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!cargoActual || enviando || !hayCambiosCargoModal()) {
      return;
    }

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

    const payload = {
      cantidad: cantidad,
      unidad_cantidad: document.getElementById("cargoGestionUnidad").value,
      estado_pof: estadoPof,
      observacion: document.getElementById("cargoGestionObservacion").value,
    };
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
    if (cargoActual && !enviando) {
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
