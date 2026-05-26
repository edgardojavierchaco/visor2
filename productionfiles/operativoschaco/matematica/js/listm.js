console.log("✅ Script ejecutado correctamente");

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(function () {
    console.log("✅ DataTable inicializado");

    $.ajax({
        url: window.location.pathname,
        type: 'POST',
        headers: { "X-CSRFToken": getCookie('csrftoken') },
        data: { 'action': 'searchdata' },
        success: function(response) {
            $('#data').DataTable().clear().destroy();

            $('#data').DataTable({
                responsive: true,
                autoWidth: false,
                destroy: true,
                deferRender: true,
                data: response.data,
                columns: [
                    { data: "alumno.dni" },
                    { data: "alumno.apellidos" },
                    { data: "alumno.nombres" },
                    {
                        data: "subtotales.Aritmética",
                        render: data => parseFloat(data || 0).toFixed(2)
                    },
                    {
                        data: "subtotales.Geometría",
                        render: data => parseFloat(data || 0).toFixed(2)
                    },
                    {
                        data: "subtotales.Estadística",
                        render: data => parseFloat(data || 0).toFixed(2)
                    },
                    {
                        data: "total_general",
                        render: data => parseFloat(data || 0).toFixed(2)
                    }
                ]
            });
        },
        error: function(xhr, status, error) {
            console.error("❌ Error en AJAX:", status, error);
            console.error("❌ Respuesta del servidor:", xhr.responseText);
        }
    });
});
