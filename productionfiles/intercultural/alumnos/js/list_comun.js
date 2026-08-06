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
            {"data": "nivel"},
            {"data": "curso"},
            {"data": "seccion"},
            {"data": "lengua"},
            {"data": "varones"},
            {"data": "mujeres"},
            {"data": "id"}  // Esto es para las acciones (editar/eliminar)
        ],
        columnDefs: [
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="../update_comun/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="../delete_comun/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    return buttons;
                }
            },
        ],
        footerCallback: function (row, data, start, end, display) {
            var api = this.api();

            // Función para sumar una columna
            var intVal = function (i) {
                return typeof i === 'string' ?
                    i.replace(/[\$,]/g, '') * 1 :
                    typeof i === 'number' ? i : 0;
            };

            // Sumar las columnas de varones y mujeres
            var totalVarones = api
                .column(5, { search: 'applied' })
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);

            var totalMujeres = api
                .column(6, { search: 'applied' })
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);

            // Insertar los totales en el footer
            $(api.column(5).footer()).html(totalVarones);
            $(api.column(6).footer()).html(totalMujeres);
        }
    });
});

