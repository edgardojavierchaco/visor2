$(function () {
        // Inicialización de DataTable
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
                    return json.docentes;
                }
            },
            columns: [
                {"data": "cueanexo"},            
                {"data": "apellidos"},
                {"data": "nombres"},
                {"data": "n_doc"},
                {"data": "cuil"},
                {"data": "denom_cargo"},
                {"data": "sit_rev"},
                {"data": "f_desde"},
                {"data": "f_hasta"},
                {"data": "cuof"},
                {"data": "cuof_anexo"},
                {"data": "id"}
            ],
            columnDefs: [
                {
                    targets: [-1],  // Aplica sobre la última columna (índice 11)
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        var buttons = '<a href="../ver_doc/' + row.cuil + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-search"></i></a> ';
                       
                        return buttons;
                    }
                }
            ],
                    
            footerCallback: function (row, data, start, end, display) {
                var api = this.api();
                var pageInfo = api.page.info();
                var totalRecords = pageInfo.recordsDisplay;
                $(api.column(0).footer()).html('Total registros: ' + totalRecords);
            }
        });
    });