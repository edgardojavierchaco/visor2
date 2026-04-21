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
            
            {"data": "cueanexo"},
            {"data": "nom_est"},
            {"data": "oferta"},
            {"data": "region"},              
            {"data": "region"},       
        ],
        columnDefs: [
            
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="superv/escuelas/update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat disabled"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="superv/escuelas/delete/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat disabled"><i class="fas fa-trash-alt"></i></a>';
                    return buttons;
                }
            },
        ],
        initComplete: function (settings, json) {

        }
    });
});
