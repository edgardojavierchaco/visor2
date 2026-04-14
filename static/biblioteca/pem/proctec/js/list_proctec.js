$(function () {
    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            data: {
                'action': 'searchdata'
            },
            dataSrc: ""
        },
        columns: [            
            {"data": "cueanexo"},
            {"data": "mes"},
            {"data": "anio"},
            {"data": "material"},
            {"data": "procesos"},            
            {"data": "total"},
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

            // Sumar la columna "varones" (índice 5)
            var totales = api
                .column(5, { search: 'applied' })
                .data()
                .reduce(function(a, b) { 
                    return intVal(a) + intVal(b); 
                }, 0);            
            
            // Insertar los totales en el footer (columnas)  
            $(api.column(5).footer()).html(totales);
                       
        }
    });
});