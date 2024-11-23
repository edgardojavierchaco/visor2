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
            {"data": "cue"},
            {"data": "anexo"},
            {"data": "cueanexo"},
            {"data": "cuof"},
            {"data": "cuof_anexo"},
            {"data": "cui"},
            {"data": "nivel"},
            {"data": "modalidad"},
            {"data": "sector"},
            {"data": "ambito"},
            {"data": "zona"},
            {"data": "categoria"},
            {"data": "jornada"},
            {"data": "region"},
            {"data": "nom_est"},
            {"data": "ubicacion"},
            {"data": "nro"},
            {"data": "departamento"},
            {"data": "localidad"},
            {"data": "localidad"},
        ],
        columnDefs: [
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="../update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="../delete/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    return buttons;
                }
            },
        ],
        initComplete: function (settings, json) {

        }
    });
});
