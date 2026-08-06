(function () {
    "use strict";

    function getCsrfToken() {
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (let i = 0; i < cookies.length; i += 1) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === "csrftoken=") {
                return decodeURIComponent(cookie.substring(10));
            }
        }
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        return input ? input.value : "";
    }

    function esObjetoPlano(valor) {
        return valor && typeof valor === "object" && !(valor instanceof FormData) && !(valor instanceof Blob);
    }

    function tipoPorStatus(status, data) {
        if (data && data.tipo) {
            return data.tipo;
        }
        if (status === 401) {
            return "sesion";
        }
        if (status === 400) {
            return "validacion";
        }
        if (status === 403) {
            if (data && /permis/i.test(data.mensaje || "")) {
                return "permiso";
            }
            return "sesion";
        }
        if (status === 404) {
            return "no_encontrado";
        }
        if (status >= 500) {
            return "interno";
        }
        return "respuesta_invalida";
    }

    function mensajePorStatus(status, tipo) {
        if (tipo === "sin_cambios") {
            return "No hay cambios para guardar.";
        }
        if (tipo === "permiso") {
            return "Esta acci\u00f3n no est\u00e1 disponible para tu usuario.";
        }
        if (tipo === "sesion") {
            return "La sesi\u00f3n expir\u00f3 o la solicitud no es v\u00e1lida. Recarg\u00e1 la p\u00e1gina.";
        }
        if (status === 400) {
            return "La solicitud tiene datos inv\u00e1lidos.";
        }
        if (status === 403) {
            return "La sesi\u00f3n expir\u00f3 o la solicitud no es v\u00e1lida. Recarg\u00e1 la p\u00e1gina.";
        }
        if (status === 404) {
            return "No se encontr\u00f3 el registro solicitado.";
        }
        if (status >= 500) {
            return "Ocurri\u00f3 un error interno. Informe al administrador.";
        }
        return "No se pudo completar la acci\u00f3n.";
    }

    function crearError(status, tipo, mensaje, errores, data, body) {
        return {
            status: status || 0,
            tipo: tipo || "interno",
            mensaje: mensaje || mensajePorStatus(status || 0, tipo),
            errores: errores || {},
            data: data || null,
            body: body || ""
        };
    }

    function logError(context, error) {
        if (!window.console || !window.console.error) {
            return;
        }
        window.console.error("[POF API]", {
            contexto: context || "",
            url: error && error.url,
            metodo: error && error.metodo,
            status: error && error.status,
            tipo: error && error.tipo,
            mensaje: error && error.mensaje,
            errores: error && error.errores,
            body: error && error.body,
            data: error && error.data
        });
    }

    async function requestJson(url, options) {
        const opciones = options || {};
        const metodo = (opciones.method || "GET").toUpperCase();
        const headers = new Headers(opciones.headers || {});
        let body = opciones.body;

        headers.set("X-Requested-With", "XMLHttpRequest");

        if (["POST", "PUT", "PATCH", "DELETE"].includes(metodo)) {
            headers.set("X-CSRFToken", getCsrfToken());
        }

        if (esObjetoPlano(body)) {
            headers.set("Content-Type", "application/json");
            body = JSON.stringify(body);
        }

        let response;
        let texto = "";
        try {
            response = await fetch(url, {
                ...opciones,
                method: metodo,
                headers: headers,
                body: body,
                mode: "same-origin"
            });
            texto = await response.text();
        } catch (errorRed) {
            const error = crearError(
                0,
                "interno",
                "No se pudo conectar con el servidor. Verific\u00e1 la conexi\u00f3n e intent\u00e1 nuevamente.",
                {},
                null,
                ""
            );
            error.url = url;
            error.metodo = metodo;
            error.original = errorRed;
            logError("requestJson", error);
            throw error;
        }

        let data = null;
        if (texto) {
            try {
                data = JSON.parse(texto);
            } catch (errorParseo) {
                const tipoRespuesta = [401, 403].includes(response.status)
                    ? tipoPorStatus(response.status, null)
                    : "respuesta_invalida";
                const error = crearError(
                    response.status,
                    tipoRespuesta,
                    tipoRespuesta === "respuesta_invalida"
                        ? "Respuesta inesperada del servidor. Revisar consola/terminal."
                        : mensajePorStatus(response.status, tipoRespuesta),
                    {},
                    null,
                    texto
                );
                error.url = url;
                error.metodo = metodo;
                error.original = errorParseo;
                logError("requestJson", error);
                throw error;
            }
        }

        if (!texto) {
            if (response.ok) {
                return {ok: true, tipo: "ok", mensaje: "", data: {}};
            }
            const error = crearError(
                response.status,
                tipoPorStatus(response.status, data),
                mensajePorStatus(response.status, tipoPorStatus(response.status, data)),
                {},
                data,
                texto
            );
            error.url = url;
            error.metodo = metodo;
            logError("requestJson", error);
            throw error;
        }

        if (!response.ok || !data || data.ok === false) {
            const tipo = tipoPorStatus(response.status, data);
            let mensaje = data && data.mensaje ? data.mensaje : mensajePorStatus(response.status, tipo);
            if ([401, 403].includes(response.status) && (!data || !data.tipo)) {
                mensaje = mensajePorStatus(response.status, tipo);
            }
            const error = crearError(
                response.status,
                tipo,
                mensaje,
                data && data.errores ? data.errores : {},
                data,
                texto
            );
            error.url = url;
            error.metodo = metodo;
            logError("requestJson", error);
            throw error;
        }

        return data;
    }

    function etiquetaCampo(campo) {
        const etiquetas = {
            ceic: "CEIC",
            cantidad: "Cantidad",
            estado_pof: "Estado",
            cargo_id: "Cargo",
            unidad_cantidad: "Unidad",
            payload: "Solicitud",
            __all__: ""
        };
        return etiquetas[campo] !== undefined ? etiquetas[campo] : campo;
    }

    function aMensajes(valor) {
        if (valor == null) {
            return [];
        }
        if (Array.isArray(valor)) {
            return valor.map(function (item) {
                return String(item);
            });
        }
        if (typeof valor === "object") {
            const partes = [];
            Object.keys(valor).forEach(function (clave) {
                aMensajes(valor[clave]).forEach(function (mensaje) {
                    const etiqueta = etiquetaCampo(clave);
                    partes.push(etiqueta ? etiqueta + ": " + mensaje : mensaje);
                });
            });
            return partes;
        }
        return [String(valor)];
    }

    function formatError(errorOrData) {
        const data = errorOrData && errorOrData.data ? errorOrData.data : errorOrData;
        const errores = errorOrData && errorOrData.errores ? errorOrData.errores : data && data.errores;
        const partes = [];

        if (errores && typeof errores === "object") {
            Object.keys(errores).forEach(function (campo) {
                aMensajes(errores[campo]).forEach(function (mensaje) {
                    const etiqueta = etiquetaCampo(campo);
                    partes.push(etiqueta ? etiqueta + ": " + mensaje : mensaje);
                });
            });
        }

        if (partes.length) {
            return partes.join(" ");
        }

        if (data && data.mensaje) {
            return data.mensaje;
        }

        if (errorOrData && errorOrData.mensaje) {
            return errorOrData.mensaje;
        }

        return "No se pudo completar la acci\u00f3n.";
    }

    function resolverTarget(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "string") {
            return document.querySelector(target);
        }
        return target;
    }

    function showStatus(target, type, message) {
        const elemento = resolverTarget(target);
        if (!elemento) {
            return;
        }
        const tipo = type || "info";
        const mapaPof = {
            success: "ok",
            ok: "ok",
            error: "error",
            warning: "warn",
            warn: "warn",
            info: "info"
        };
        const mapaBootstrap = {
            success: "alert-success",
            ok: "alert-success",
            error: "alert-danger",
            warning: "alert-warning",
            warn: "alert-warning",
            info: "alert-info"
        };
        elemento.className = [
            "pof-status",
            "pof-api-status",
            mapaPof[tipo] || "info",
            "pof-api-status-" + tipo,
            "alert",
            mapaBootstrap[tipo] || "alert-info"
        ].join(" ");
        elemento.textContent = message || "";
    }

    function clearStatus(target) {
        const elemento = resolverTarget(target);
        if (!elemento) {
            return;
        }
        elemento.className = "pof-status pof-api-status";
        elemento.textContent = "";
    }

    function limpiarSoloDigitos(valor) {
    return String(valor || "").replace(/\D+/g, "");
    }

    function bindDigitsOnly(root) {
        const scope = root || document;
        const campos = Array.from(scope.querySelectorAll("[data-pof-digits-only]"));

        campos.forEach(function (campo) {
            if (campo.dataset.pofDigitsOnlyBound === "true") {
                return;
            }

            campo.dataset.pofDigitsOnlyBound = "true";

            campo.addEventListener("beforeinput", function (event) {
                if (!event.data) {
                    return;
                }

                if (/\D/.test(event.data)) {
                    event.preventDefault();
                }
            });

            campo.addEventListener("input", function () {
                const valorOriginal = campo.value;
                const valorLimpio = limpiarSoloDigitos(valorOriginal);

                if (valorOriginal === valorLimpio) {
                    return;
                }

                const posicion = campo.selectionStart || valorLimpio.length;
                campo.value = valorLimpio;

                try {
                    const nuevaPosicion = Math.min(posicion, valorLimpio.length);
                    campo.setSelectionRange(nuevaPosicion, nuevaPosicion);
                } catch (error) {
                    // Algunos inputs/navegadores no permiten reposicionar selección.
                }
            });
        });
    }

    function campoFiltroTieneValor(campo) {
        if (!campo) {
            return false;
        }

        if (campo.type === "checkbox" || campo.type === "radio") {
            return campo.checked;
        }

        return String(campo.value || "").trim() !== "";
    }

    function actualizarAuraFiltro(campo) {
        const contenedor = campo ? campo.closest(".pof-filter-field") : null;
        if (!contenedor) {
            return;
        }

        contenedor.classList.toggle("pof-filter-field-active", campoFiltroTieneValor(campo));
    }

    function bindFilterActiveState(root) {
        const scope = root || document;
        const campos = Array.from(scope.querySelectorAll(
            ".pof-filter-field input, .pof-filter-field select, .pof-filter-field textarea"
        ));

        campos.forEach(function (campo) {
            if (campo.dataset.pofFilterActiveBound === "true") {
                return;
            }

            campo.dataset.pofFilterActiveBound = "true";
            actualizarAuraFiltro(campo);

            campo.addEventListener("input", function () {
                actualizarAuraFiltro(campo);
            });

            campo.addEventListener("change", function () {
                actualizarAuraFiltro(campo);
            });
        });
    }

    /**
     * Vincula la única modal de eliminación de cabeceras POF presente en una pantalla.
     *
     * - Toma tipo, etiqueta, advertencia y URL POST desde el disparador data-pof-delete-open.
     * - Cierra sin enviar por cancelar, X, Escape o clic directo en el backdrop.
     * - Evita doble submit y conserva la protección CSRF incluida en el formulario Django.
     */
    /**
 * Vincula la única modal de eliminación de cabeceras POF presente en una pantalla.
 *
 * - Toma tipo, etiqueta, advertencia y URL POST desde el disparador data-pof-delete-open.
 * - Envía la eliminación por la API compartida y espera la respuesta real del backend.
 * - Muestra éxito o error dentro de la misma modal.
 * - Recarga la página solo después de una eliminación confirmada por el servidor.
 * - Evita doble submit y conserva la protección CSRF del módulo.
 */
    function bindDeleteHeaderModal() {
        const modal = document.getElementById("modalEliminarCabecera");
        if (!modal || modal.dataset.pofDeleteBound === "true") {
            return;
        }

        const form = modal.querySelector("[data-pof-delete-form]");
        const title = modal.querySelector("[data-pof-delete-title]");
        const label = modal.querySelector("[data-pof-delete-label]");
        const warning = modal.querySelector("[data-pof-delete-warning]");
        const status = modal.querySelector("[data-pof-delete-status]");
        const confirmButton = modal.querySelector("[data-pof-delete-confirm]");

        let triggerActivo = null;

        if (
            !form ||
            !title ||
            !label ||
            !warning ||
            !status ||
            !confirmButton
        ) {
            return;
        }

        const contenidoConfirmacionOriginal = confirmButton.innerHTML;

        modal.dataset.pofDeleteBound = "true";

        /**
         * Devuelve la modal a su estado inicial y elimina datos temporales
         * pertenecientes a la última cabecera seleccionada.
         */
        function resetearModal() {
            form.removeAttribute("action");
            form.dataset.pofDeleteSubmitting = "false";

            modal.removeAttribute("data-pof-delete-tipo");

            confirmButton.disabled = false;
            confirmButton.removeAttribute("aria-disabled");
            confirmButton.innerHTML = contenidoConfirmacionOriginal;

            clearStatus(status);
        }

        /**
         * Cierra la modal solo cuando no existe una eliminación en curso.
         *
         * Evita que la persona usuaria cierre la modal mientras el backend
         * todavía está resolviendo una operación destructiva.
         */
        function cerrarModal() {
            if (form.dataset.pofDeleteSubmitting === "true") {
                return;
            }

            modal.classList.add("pof-hidden");
            modal.setAttribute("aria-hidden", "true");

            resetearModal();

            if (triggerActivo) {
                triggerActivo.focus();
            }

            triggerActivo = null;
        }

        document
            .querySelectorAll("[data-pof-delete-open]")
            .forEach(function (trigger) {
                trigger.addEventListener("click", function () {
                    triggerActivo = trigger;

                    title.textContent =
                        trigger.dataset.pofDeleteTitle ||
                        "Eliminar cabecera";

                    label.textContent =
                        trigger.dataset.pofDeleteLabel ||
                        "";

                    warning.textContent =
                        trigger.dataset.pofDeleteWarning ||
                        "";

                    form.action =
                        trigger.dataset.pofDeleteUrl ||
                        "";

                    modal.dataset.pofDeleteTipo =
                        trigger.dataset.pofDeleteTipo ||
                        "";

                    form.dataset.pofDeleteSubmitting = "false";

                    confirmButton.disabled = false;
                    confirmButton.removeAttribute("aria-disabled");
                    confirmButton.innerHTML = contenidoConfirmacionOriginal;

                    clearStatus(status);

                    modal.classList.remove("pof-hidden");
                    modal.setAttribute("aria-hidden", "false");

                    confirmButton.focus();
                });
            });

        modal
            .querySelectorAll("[data-pof-delete-close]")
            .forEach(function (button) {
                button.addEventListener("click", cerrarModal);
            });

        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                cerrarModal();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (
                event.key === "Escape" &&
                !modal.classList.contains("pof-hidden")
            ) {
                cerrarModal();
            }
        });

        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            const url = form.getAttribute("action");

            if (
                !url ||
                form.dataset.pofDeleteSubmitting === "true"
            ) {
                return;
            }

            form.dataset.pofDeleteSubmitting = "true";

            confirmButton.disabled = true;
            confirmButton.setAttribute("aria-disabled", "true");
            confirmButton.textContent = "⏳ Eliminando...";

            clearStatus(status);

            try {
                const data = await requestJson(url, {
                    method: "POST"
                });

                showStatus(
                    status,
                    "success",
                    data.mensaje ||
                        "La cabecera fue eliminada correctamente."
                );

                window.setTimeout(function () {
                    window.location.reload();
                }, 900);
            } catch (error) {
                form.dataset.pofDeleteSubmitting = "false";

                confirmButton.disabled = false;
                confirmButton.removeAttribute("aria-disabled");
                confirmButton.innerHTML = contenidoConfirmacionOriginal;

                showStatus(
                    status,
                    "error",
                    formatError(error)
                );
            }
        });
    }


    document.addEventListener("DOMContentLoaded", function () {
        bindDigitsOnly(document);
        bindFilterActiveState(document);
        bindDeleteHeaderModal();
    });


    window.pofApi = {
        getCsrfToken: getCsrfToken,
        requestJson: requestJson,
        formatError: formatError,
        showStatus: showStatus,
        clearStatus: clearStatus,
        logError: logError,
        limpiarSoloDigitos: limpiarSoloDigitos,
        bindDigitsOnly: bindDigitsOnly,
        actualizarAuraFiltro: actualizarAuraFiltro,
        bindFilterActiveState: bindFilterActiveState,
        bindDeleteHeaderModal: bindDeleteHeaderModal
    };
})();
