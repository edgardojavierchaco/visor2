// =========================
// 🔐 OBTENER CSRF DESDE INPUT
// =========================
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// =========================
// DATATABLE
// =========================
$(function () {
    const csrftoken = getCSRFToken();

    console.log("CSRF TOKEN:", csrftoken); // ahora sí va a tener valor

    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            headers: {
                "X-CSRFToken": csrftoken
            },
            data: {
                'action': 'searchdata'
            },
            dataSrc: function (json) {

                console.log("DATA:", json);

                if (json.error) {
                    Swal.fire("Error", json.message, "error");
                    return [];
                }

                return json;
            },

            error: function (xhr) {

                console.error("STATUS:", xhr.status);
                console.error("RESPONSE:", xhr.responseText);

                Swal.fire({
                    icon: "error",
                    title: "Error AJAX",
                    text: "Ver consola (F12)"
                });
            }
        },
        columns: [            
            {"data": "cueanexo"},
            {"data": "mes"},
            {"data": "anio"},
            {"data": "destino"},
            {"data": "descripcion"},
            {"data": "cantidad"},
            {"data": "id"}  // Columna extra para los botones
        ],
        columnDefs: [
            {
                targets: [-1],  // Aplica sobre la última columna (índice 7)
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="../update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="../delete/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    return buttons;
                }
            }
        ],
        footerCallback: function (row, data, start, end, display) {
            var api = this.api();

            // Función para convertir a número
            var intVal = function (i) {
                return typeof i === 'string' ?
                    i.replace(/[\$,]/g, '') * 1 :
                    typeof i === 'number' ? i : 0;
            };
            
            // Sumar la columna "cantidad" (índice 5)
            var totales = api
                .column(5, { search: 'applied' })
                .data()
                .reduce(function(a, b) { 
                    return intVal(a) + intVal(b); 
                }, 0);
            
            // Insertar los totales en el footer (columnas 5)            
            $(api.column(5).footer()).html(totales);            
        }
    });
});