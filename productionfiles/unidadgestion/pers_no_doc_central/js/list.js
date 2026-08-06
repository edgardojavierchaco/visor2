$(function () {
    $('#data').DataTable({
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
            {"data": "id"},
            {"data": "t_dni"},
            {"data": "dni"},
            {"data": "cuil"},
            {"data": "apellido"},
            {"data": "nombres"},
            {"data": "f_nac"},
            {"data": "sexo"},
            {"data": "categoria"},            
            {"data": "sit_nom"},
            {"data": "f_designacion"},
            {"data": "nom_funcion"},
            {"data": "f_desde"},
            {"data": "f_hasta"},
            {"data": "carga_horaria_sem"},
            {"data": "cuof"},
            {"data": "cuof_anexo"},
            {"data": "region"},
            {"data": "region"},
        ],
        columnDefs: [
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="../update_admin/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="../delete_admin/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    return buttons;
                }
            },
        ],
        initComplete: function (settings, json) {

        }
    });
});
