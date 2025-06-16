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
            {"data": "cuil"},
            {"data": "t_doc"},
            {"data": "n_doc"},
            {"data": "apellidos"},
            {"data": "nombres"},
            {"data": "f_nac"},
            {"data": "cargo"},
            {"data": "situacion_revista"},
            {"data": "f_ingreso"},
            {"data": "f_hasta"},
            {"data": "turno"},
            {"data": "cuof"},
            {"data": "cuof_anexo"},
            {"data": "mes"},
            {"data": "anio"},
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
        
    });
});