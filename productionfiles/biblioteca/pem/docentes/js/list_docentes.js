$(function () {
    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: window.location.pathname,  // Usamos la URL actual
            type: 'POST',
            data: {
                'action': 'searchdata'  // Enviamos la acción para que el servidor lo procese
            },
            dataSrc: function (json) {
                console.log('datosrecibidos:', json);
                // Asumiendo que los datos vienen bajo la clave 'docentes'
                return json.docentes;  // Accedemos a 'docentes' desde la respuesta
            }
        },
        columns: [
            {"data": "apellidos"},
            {"data": "nombres"},
            {"data": "n_doc"},
            {"data": "cuil"},
            {"data": "denom_cargo"},
            {"data": "sit_rev"},
            {"data": "f_desde"},
            {"data": "f_hasta"},
            
        ],
        footerCallback: function (row, data, start, end, display) {
            var api = this.api();
            var pageInfo = api.page.info();
            var totalRecords = pageInfo.recordsDisplay;
            $(api.column(0).footer()).html('Total registros: ' + totalRecords);
        }
    });
});
