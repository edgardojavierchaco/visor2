console.log("✅ Script ejecutado correctamente");
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Busca la cookie con el nombre "csrftoken"
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
console.log(getCookie('csrftoken'));

$(function () {
    console.log("✅ DataTable inicializado");

    $('#data').DataTable({        
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            headers: { "X-CSRFToken": getCookie('csrftoken') },
            data: {
                'action': 'searchdata'
            },
            dataSrc: "",
            error: function (xhr, status, error) {
                console.error("❌ Error en AJAX:", status, error);
                console.error("❌ Respuesta del servidor:", xhr.responseText);
            }
        },
        columns: [
            {"data": "id"},
            {"data": "dni"},
            {"data": "apellido"},
            {"data": "nombres"},
            {"data": "email"},
            {"data": "telefono"},
            {"data": "region"},
            {"data": "region"},
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
            console.log("Datos recibidos:",json)
        }
    });
});
