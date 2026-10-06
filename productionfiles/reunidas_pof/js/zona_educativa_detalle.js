(function () {
    "use strict";

    const api = window.pofApi || null;
    const changeModal = document.querySelector("[data-pof-zone-change-modal]");
    const historyModal = document.querySelector("[data-pof-zone-history-modal]");

    if (!api || !changeModal || !historyModal) {
        return;
    }

    const changeLabel = changeModal.querySelector("[data-pof-zone-change-label]");
    const changeCurrent = changeModal.querySelector("[data-pof-zone-change-current]");
    const changeStatus = changeModal.querySelector("[data-pof-zone-change-status]");
    const changeType = changeModal.querySelector("[data-pof-zone-change-type]");
    const changeZone = changeModal.querySelector("[data-pof-zone-change-zone]");
    const changePoints = changeModal.querySelector("[data-pof-zone-change-points]");
    const changeObservation = changeModal.querySelector("[data-pof-zone-change-observation]");
    const changeRemove = changeModal.querySelector("[data-pof-zone-change-remove]");
    const changeSave = changeModal.querySelector("[data-pof-zone-change-save]");

    const historyLabel = historyModal.querySelector("[data-pof-zone-history-label]");
    const historySummary = historyModal.querySelector("[data-pof-zone-history-summary]");
    const historyStatus = historyModal.querySelector("[data-pof-zone-history-status]");
    const historyContent = historyModal.querySelector("[data-pof-zone-history-content]");

    let activeLocalizacionId = null;
    let currentAssignment = null;
    let catalogRequestSequence = 0;

    function clearElement(element) {
        while (element && element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

    function visibleValue(value) {
        if (value === null || value === undefined || value === "") {
            return "—";
        }
        return String(value);
    }

    function formatDate(value) {
        if (!value) {
            return "—";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return String(value);
        }
        return new Intl.DateTimeFormat("es-AR", {
            dateStyle: "short",
            timeStyle: "short",
        }).format(date);
    }

    function urlWithId(baseUrl, localizacionId) {
        return String(baseUrl || "").replace("/0/", "/" + String(localizacionId) + "/");
    }

    function createSummaryItem(label, value) {
        const item = document.createElement("div");
        item.className = "pof-detail-item";
        const key = document.createElement("span");
        const strong = document.createElement("strong");
        key.textContent = label;
        strong.textContent = visibleValue(value);
        item.appendChild(key);
        item.appendChild(strong);
        return item;
    }

    function renderCurrentSummary(container, state) {
        clearElement(container);
        const assignment = state && state.asignada ? state : {};
        container.appendChild(createSummaryItem("Tipo", assignment.tipo || ""));
        container.appendChild(createSummaryItem("Zona Educativa", assignment.zona || ""));
        container.appendChild(createSummaryItem("Puntos Zona", assignment.puntos));
        container.classList.remove("pof-hidden");
    }

    function renderHistorySummary(payload) {
        clearElement(historySummary);
        const vigente = payload && payload.vigente ? payload.vigente : {};
        const localizacion = payload && payload.localizacion ? payload.localizacion : {};
        historySummary.appendChild(createSummaryItem("CUEANEXO", localizacion.cueanexo || ""));
        historySummary.appendChild(createSummaryItem("CUOF", localizacion.cuof || ""));
        historySummary.appendChild(createSummaryItem("Zona vigente", vigente.zona || ""));
        historySummary.appendChild(createSummaryItem("Puntos vigentes", vigente.puntos));
        historySummary.classList.remove("pof-hidden");
    }

    function resetZoneSelector() {
        changeZone.innerHTML = "";
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Seleccioná una zona";
        changeZone.appendChild(option);
        changeZone.disabled = true;
        changePoints.value = "";
        changeSave.disabled = true;
    }

    function updateSelectedZone() {
        const option = changeZone.options[changeZone.selectedIndex];
        const points = option ? Number(option.dataset.puntos || 0) : 0;
        changePoints.value = points > 0 ? String(points) : "";
        changeSave.disabled = !(
            activeLocalizacionId
            && changeType.value
            && option
            && option.value
            && points > 0
        );
    }

    function openModal(modal) {
        modal.classList.remove("pof-hidden");
        modal.setAttribute("aria-hidden", "false");
    }

    function closeModal(modal) {
        modal.classList.add("pof-hidden");
        modal.setAttribute("aria-hidden", "true");
    }

    async function loadCatalog(type, preferredZone) {
        const normalizedType = String(type || "").trim().toUpperCase();
        resetZoneSelector();

        if (!normalizedType) {
            api.showStatus(changeStatus, "info", "Seleccioná primero el tipo de Zona Educativa.");
            return;
        }

        const sequence = ++catalogRequestSequence;
        changeZone.innerHTML = "";
        const loadingOption = document.createElement("option");
        loadingOption.value = "";
        loadingOption.textContent = "Cargando zonas...";
        changeZone.appendChild(loadingOption);
        api.showStatus(changeStatus, "info", "Cargando catálogo de Zona Educativa...");

        try {
            const url = new URL(changeModal.dataset.catalogoUrl || "", window.location.origin);
            url.searchParams.set("tipo", normalizedType);
            const response = await api.requestJsonRead(url.toString());

            if (sequence !== catalogRequestSequence || changeType.value !== normalizedType) {
                return;
            }

            const payload = response.data || {};
            const zones = Array.isArray(payload.zonas) ? payload.zonas : [];

            changeZone.innerHTML = "";
            const emptyOption = document.createElement("option");
            emptyOption.value = "";
            emptyOption.textContent = "Seleccioná una zona";
            changeZone.appendChild(emptyOption);

            zones.forEach(function (item) {
                const option = document.createElement("option");
                option.value = String(item.zona || "");
                option.textContent = String(item.zona || "");
                option.dataset.puntos = String(item.puntos || "");
                changeZone.appendChild(option);
            });

            changeZone.disabled = zones.length === 0;

            const preferred = String(preferredZone || "").trim();
            if (preferred && zones.some(function (item) {
                return String(item.zona || "").trim() === preferred;
            })) {
                changeZone.value = preferred;
                updateSelectedZone();
                const catalogPoints = Number(
                    changeZone.options[changeZone.selectedIndex].dataset.puntos || 0
                );
                if (
                    currentAssignment
                    && Number(currentAssignment.puntos || 0) > 0
                    && catalogPoints !== Number(currentAssignment.puntos)
                ) {
                    api.showStatus(
                        changeStatus,
                        "info",
                        "El catálogo activo tiene puntos distintos a los congelados actualmente. Guardar la misma zona adoptará los puntos vigentes del catálogo."
                    );
                } else {
                    api.clearStatus(changeStatus);
                }
                return;
            }

            if (preferred && currentAssignment && currentAssignment.asignada) {
                api.showStatus(
                    changeStatus,
                    "info",
                    "La Zona Educativa vigente no está disponible en el catálogo activo. Seleccioná una zona activa para cambiarla."
                );
            } else if (zones.length) {
                api.showStatus(changeStatus, "info", "Seleccioná la nueva Zona Educativa.");
            } else {
                api.showStatus(changeStatus, "error", "No hay zonas activas disponibles para este tipo.");
            }
        } catch (error) {
            if (sequence !== catalogRequestSequence) {
                return;
            }
            resetZoneSelector();
            api.showStatus(changeStatus, "error", api.formatError(error));
        }
    }

    async function openChange(trigger) {
        const localizacionId = String(trigger.dataset.localizacionId || "").trim();
        if (!/^\d+$/.test(localizacionId)) {
            return;
        }

        activeLocalizacionId = Number(localizacionId);
        currentAssignment = null;
        catalogRequestSequence += 1;
        changeLabel.textContent = trigger.dataset.zoneLabel || ("Localización #" + localizacionId);
        changeType.value = "";
        changeObservation.value = "";
        changeRemove.classList.add("pof-hidden");
        changeRemove.disabled = true;
        resetZoneSelector();
        clearElement(changeCurrent);
        changeCurrent.classList.add("pof-hidden");
        api.showStatus(changeStatus, "info", "Consultando Zona Educativa vigente...");
        openModal(changeModal);

        try {
            const url = new URL(changeModal.dataset.vigenteUrl || "", window.location.origin);
            url.searchParams.set("localizacion_id", localizacionId);
            const response = await api.requestJsonRead(url.toString());
            const state = response.data || {};
            currentAssignment = state;
            renderCurrentSummary(changeCurrent, state);
            changeRemove.classList.toggle("pof-hidden", !state.asignada);
            changeRemove.disabled = !state.asignada;

            if (state.asignada && state.tipo) {
                changeType.value = String(state.tipo).toUpperCase();
                await loadCatalog(changeType.value, state.zona || "");
            } else {
                api.showStatus(
                    changeStatus,
                    "info",
                    "La identidad todavía no tiene Zona Educativa. Seleccioná tipo y zona."
                );
            }
        } catch (error) {
            api.showStatus(changeStatus, "error", api.formatError(error));
            changeType.disabled = true;
            resetZoneSelector();
        }
    }

    async function persistChange(type, zone, successMessage) {
        if (!activeLocalizacionId) {
            return;
        }

        const observation = String(changeObservation.value || "").trim();

        changeSave.disabled = true;
        changeRemove.disabled = true;
        changeType.disabled = true;
        changeZone.disabled = true;
        changeObservation.disabled = true;
        api.showStatus(changeStatus, "info", "Guardando cambio de Zona Educativa...");

        try {
            const url = urlWithId(
                changeModal.dataset.cambioUrlBase,
                activeLocalizacionId
            );
            await api.requestJson(url, {
                method: "POST",
                body: {
                    tipo: type,
                    zona: zone,
                    observacion: observation,
                },
            });
            api.showStatus(
                changeStatus,
                "ok",
                successMessage
            );
            window.location.reload();
        } catch (error) {
            if (error && error.tipo === "sin_cambios") {
                api.showStatus(
                    changeStatus,
                    "info",
                    error.mensaje || "La Zona Educativa seleccionada ya es la vigente."
                );
            } else {
                api.showStatus(changeStatus, "error", api.formatError(error));
            }
            changeType.disabled = false;
            changeZone.disabled = !changeType.value || changeZone.options.length <= 1;
            changeObservation.disabled = false;
            changeRemove.disabled = !(currentAssignment && currentAssignment.asignada);
            updateSelectedZone();
        }
    }

    async function saveChange() {
        if (!activeLocalizacionId || changeSave.disabled) {
            return;
        }

        const type = String(changeType.value || "").trim().toUpperCase();
        const zone = String(changeZone.value || "").trim();
        if (!type || !zone) {
            return;
        }

        await persistChange(
            type,
            zone,
            "Zona Educativa actualizada correctamente. Recargando el detalle..."
        );
    }

    async function removeChange() {
        if (
            !activeLocalizacionId
            || changeRemove.disabled
            || !(currentAssignment && currentAssignment.asignada)
        ) {
            return;
        }

        await persistChange(
            "",
            "",
            "Zona Educativa quitada correctamente. Recargando el detalle..."
        );
    }

    function createCell(value) {
        const cell = document.createElement("td");
        cell.textContent = visibleValue(value);
        return cell;
    }

    function createHeader(value) {
        const header = document.createElement("th");
        header.textContent = value;
        return header;
    }

    function describeChanges(event) {
        const changes = Array.isArray(event.cambios) ? event.cambios : [];
        if (!changes.length) {
            return "—";
        }
        return changes.map(function (change) {
            return String(change.etiqueta || change.campo || "Cambio")
                + ": "
                + visibleValue(change.anterior)
                + " → "
                + visibleValue(change.nuevo);
        }).join(" · ");
    }

    function renderHistoryEvents(events, container) {
        const items = Array.isArray(events) ? events : [];
        if (!items.length) {
            return false;
        }

        const wrap = document.createElement("div");
        wrap.className = "pof-table-wrap";
        const table = document.createElement("table");
        table.className = "pof-grid-table pof-quantity-history-table";

        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");
        ["Fecha", "Usuario", "Anterior", "Nueva", "Cambios", "Observación"].forEach(function (title) {
            headerRow.appendChild(createHeader(title));
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        items.forEach(function (event) {
            const row = document.createElement("tr");
            const previous = event.anterior || {};
            const next = event.nuevo || {};
            const user = event.usuario || {};

            row.appendChild(createCell(formatDate(event.fecha)));
            row.appendChild(createCell(user.nombre || ""));
            row.appendChild(createCell(
                (previous.zona ? previous.zona : "Sin zona")
                + (previous.puntos ? " · " + previous.puntos + " puntos" : "")
            ));
            row.appendChild(createCell(
                (next.zona ? next.zona : "Sin zona")
                + (next.puntos ? " · " + next.puntos + " puntos" : "")
            ));
            row.appendChild(createCell(describeChanges(event)));
            row.appendChild(createCell(event.observacion || ""));
            tbody.appendChild(row);
        });

        table.appendChild(tbody);
        wrap.appendChild(table);
        container.appendChild(wrap);
        return true;
    }

    function renderHistory(payload) {
        renderHistorySummary(payload);
        clearElement(historyContent);
        api.clearStatus(historyStatus);

        const cycles = Array.isArray(payload.ciclos) ? payload.ciclos : [];
        if (cycles.length) {
            let hasEvents = false;

            cycles.forEach(function (cycle) {
                const section = document.createElement("section");
                if (cycles.length > 1) {
                    section.className = "pof-admin-history-item pof-observation-timeline-group";

                    const title = document.createElement("h3");
                    title.className = "pof-observation-timeline-group-title";
                    title.textContent = "POF " + visibleValue(cycle.anio);
                    section.appendChild(title);

                    const context = document.createElement("p");
                    context.className = "pof-admin-history-meta";
                    context.textContent = visibleValue(
                        cycle.localizacion && cycle.localizacion.cabecera
                    );
                    section.appendChild(context);
                }

                if (!renderHistoryEvents(cycle.eventos, section)) {
                    const empty = document.createElement("p");
                    empty.className = "pof-help";
                    empty.textContent = "Sin cambios explícitos de Zona Educativa en este ciclo.";
                    section.appendChild(empty);
                } else {
                    hasEvents = true;
                }

                historyContent.appendChild(section);
            });

            if (payload.advertencia_continuidad) {
                api.showStatus(
                    historyStatus,
                    "warning",
                    payload.advertencia_continuidad + " Se muestran sólo los ciclos verificables."
                );
            } else if (!hasEvents) {
                api.showStatus(
                    historyStatus,
                    "info",
                    "No se registraron cambios de Zona Educativa para los ciclos enlazados."
                );
            }
            return;
        }

        if (!renderHistoryEvents(payload.eventos, historyContent)) {
            api.showStatus(
                historyStatus,
                "info",
                "No se registraron cambios de Zona Educativa para esta localización."
            );
        }
    }

    async function openHistory(trigger) {
        const localizacionId = String(trigger.dataset.localizacionId || "").trim();
        if (!/^\d+$/.test(localizacionId)) {
            return;
        }

        historyLabel.textContent = trigger.dataset.zoneLabel || ("Localización #" + localizacionId);
        clearElement(historySummary);
        historySummary.classList.add("pof-hidden");
        clearElement(historyContent);
        api.showStatus(historyStatus, "info", "Cargando historial de Zona Educativa...");
        openModal(historyModal);

        try {
            const cargoId = String(trigger.dataset.cargoId || "").trim();
            const url = new URL(
                urlWithId(
                    historyModal.dataset.historialUrlBase,
                    Number(localizacionId)
                ),
                window.location.origin
            );
            if (/^\d+$/.test(cargoId)) {
                url.searchParams.set("cargo_id", cargoId);
            }
            const response = await api.requestJsonRead(
                url.toString(),
                { cache: "no-store" }
            );
            renderHistory(response.data || {});
        } catch (error) {
            api.showStatus(historyStatus, "error", api.formatError(error));
        }
    }

    changeType.addEventListener("change", function () {
        if (!activeLocalizacionId) {
            return;
        }
        loadCatalog(this.value, "");
    });

    changeZone.addEventListener("change", updateSelectedZone);
    changeRemove.addEventListener("click", removeChange);
    changeSave.addEventListener("click", saveChange);

    document.addEventListener("click", function (event) {
        const changeTrigger = event.target.closest("[data-pof-zone-change]");
        if (changeTrigger) {
            openChange(changeTrigger);
            return;
        }

        const historyTrigger = event.target.closest("[data-pof-zone-history]");
        if (historyTrigger) {
            openHistory(historyTrigger);
        }
    });

    changeModal.querySelectorAll("[data-pof-zone-change-close]").forEach(function (button) {
        button.addEventListener("click", function () {
            activeLocalizacionId = null;
            catalogRequestSequence += 1;
            changeType.disabled = false;
            closeModal(changeModal);
        });
    });

    historyModal.querySelectorAll("[data-pof-zone-history-close]").forEach(function (button) {
        button.addEventListener("click", function () {
            closeModal(historyModal);
        });
    });

    changeModal.addEventListener("click", function (event) {
        if (event.target === changeModal) {
            activeLocalizacionId = null;
            catalogRequestSequence += 1;
            changeType.disabled = false;
            closeModal(changeModal);
        }
    });

    historyModal.addEventListener("click", function (event) {
        if (event.target === historyModal) {
            closeModal(historyModal);
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }
        if (!changeModal.classList.contains("pof-hidden")) {
            activeLocalizacionId = null;
            catalogRequestSequence += 1;
            changeType.disabled = false;
            closeModal(changeModal);
        }
        if (!historyModal.classList.contains("pof-hidden")) {
            closeModal(historyModal);
        }
    });
})();
