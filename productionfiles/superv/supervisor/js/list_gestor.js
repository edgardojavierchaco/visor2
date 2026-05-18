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
            {"data": "dni"},
            {"data": "apellido"},
            {"data": "nombres"},
            {"data": "email"},
            {"data": "telefono"},
            {"data": "region"},
            
        ],
        
        initComplete: function (settings, json) {
            console.log("Datos recibidos:",json)
        }
    });
});
