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

  function buildUrl(base, cargoId) {
    return base.replace("/0/", "/" + cargoId + "/");
  }

  function setEnviando(valor) {
    enviando = valor;
    btnEliminar.disabled = valor;
    btnConfirmarEliminar.disabled = valor;
    btnEstadoToggle.disabled = valor;
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
    estadoCampo.value =
      estadoCampo.value === "DESAFECTADO" ? "AFECTADO" : "DESAFECTADO";
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

  function normalizarEstadoCargoModal(estado) {
    return {
      cantidad: normalizarNumeroEnteroCargoModal(estado.cantidad),
      unidad_cantidad: normalizarTextoCargoModal(
        estado.unidad_cantidad,
      ).toUpperCase(),
      estado_pof: normalizarTextoCargoModal(estado.estado_pof).toUpperCase(),
      observacion: normalizarTextoCargoModal(estado.observacion),
    };
  }

  function obtenerEstadoCargoModal() {
    return normalizarEstadoCargoModal({
      cantidad: document.getElementById("cargoGestionCantidad").value,
      unidad_cantidad: document.getElementById("cargoGestionUnidad").value,
      estado_pof: document.getElementById("cargoGestionEstado").value,
      observacion: document.getElementById("cargoGestionObservacion").value,
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
    setBotonDeshabilitadoPof(
      btnGuardar,
      enviando || !cargoActual || !hayCambios,
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

    setEnviando(false);
    api.clearStatus(estado);

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

  btnEstadoToggle.addEventListener("click", alternarEstadoPendiente);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!cargoActual || enviando || !hayCambiosCargoModal()) {
      return;
    }

    const cantidad = document.getElementById("cargoGestionCantidad").value;
    if (!/^[1-9]\d*$/.test(cantidad)) {
      api.showStatus(
        estado,
        "error",
        "Cantidad: La cantidad debe ser un número entero.",
      );
      return;
    }

    const estadoPof = document.getElementById("cargoGestionEstado").value;
    if (!["AFECTADO", "DESAFECTADO"].includes(estadoPof)) {
      api.showStatus(
        estado,
        "error",
        "Estado: El estado indicado no es válido.",
      );
      return;
    }

    ejecutarAccionCargo(
      buildUrl(modificarUrlBase, cargoActual.id),
      {
        cantidad: cantidad,
        unidad_cantidad: document.getElementById("cargoGestionUnidad").value,
        estado_pof: estadoPof,
        observacion: document.getElementById("cargoGestionObservacion").value,
      },
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
