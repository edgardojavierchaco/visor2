var tblAsignacion;
$(function () {
    tblAsignacion = $('#data').DataTable({
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
            {"data": "replegales"},
            {"data": "total"},
            {"data": "id"},
        ],
        columnDefs: [
            {
                targets: [-1],
                className: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="../delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a> ';
                    buttons += '<a href="../update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a rel="details" class="btn btn-success btn-xs btn-flat"><i class="fas fa-search"></i></a>';
                    return buttons;
                }
            },
        ],
        initComplete: function (settings, json) {
            // Opcional: código adicional
        }
    });

    // Evento para el botón de detalles
    $('#data tbody').on('click', 'a[rel="details"]', function () {
        var tr = tblAsignacion.cell($(this).closest('td, li')).index();
        var data = tblAsignacion.row(tr.row).data();
        console.log(data);  

        $('#tblDet').DataTable({
            responsive: true,
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: window.location.pathname,
                type: 'POST',
                data: {
                    'action': 'search_details_asign',  // Cambiado a search_details_asign
                    'id': data.id
                },
                dataSrc: ""
            },
            columns: [
                {"data": "escuela.cueanexo"},
                {"data": "escuela.nom_est"},
                {"data": "escuela.region"},                
            ],
            initComplete: function (settings, json) {
                // Opcional: código adicional al completar la inicialización
            }
        });
        
        $('#myModelDet').modal('show');
    });
});
