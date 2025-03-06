$(function () {
    // Destruir DataTable si ya está inicializada
    if ($.fn.DataTable.isDataTable('#data')) {
        $('#data').DataTable().clear().destroy();  // Destruye y limpia la tabla antes de reinicializar
    }

    // Inicializar DataTable
    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'GET',
            dataType: "json",
            dataSrc: ""  // Elimina la necesidad de un wrapper "data"
        },
        columns: [
            {"data": "cueanexo"},
            {"data": "mes"},
            {"data": "anios"},
            {"data": "servicio"},
            {"data": "cantidad"},
            {
                "data": "acciones",
                "render": function (data, type, row) {
                    return `                        
                        <a href="../anexas/delete/${data}/" class="btn btn-danger btn-xs btn-flat">
                            <i class="fas fa-trash-alt"></i>
                        </a>
                    `;
                }
            }
        ],
        footerCallback: function (row, data, start, end, display) {
            var api = this.api();
            var intVal = function (i) {
                return typeof i === 'string' ? i.replace(/[\$,]/g, '') * 1 : (typeof i === 'number' ? i : 0);
            };

            var totalCantidad = api
                .column(4, { search: 'applied' })
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);

            $(api.column(4).footer()).html(totalCantidad);
        }
    });
});
