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

console.log(getCookie('csrftoken'));

$(function () {
    console.log("✅ DataTable inicializado");

    $.ajax({
        url: window.location.pathname,
        type: 'POST',
        headers: { "X-CSRFToken": getCookie('csrftoken') },
        data: { 'action': 'searchdata' },
        success: function(response) {
            console.log("✅ Datos recibidos:", response);

            const categorias = response.categorias;

            $('#data').DataTable().clear().destroy();

            $('#data').DataTable({
                responsive: true,
                autoWidth: false,
                destroy: true,
                deferRender: true,
                data: response.data,
                columns: [
                    { data: "alumno.dni", title: "DNI" },
                    { data: "alumno.apellidos", title: "Apellidos" },
                    { data: "alumno.nombres", title: "Nombres" },

                    ...categorias.map(cat => ({
                        data: function (row) {
                            return row.totales_por_categoria[cat] || "0.00";
                        },
                        title: cat
                    })),

                    {
                        data: function (row) {
                            return row.total_sin_categoria || "0.00";
                        },
                        title: "Otros"
                    },

                    {
                        data: function (row) {
                            let total = 0;
                            categorias.forEach(cat => {
                                total += parseFloat(row.totales_por_categoria[cat] || 0);
                            });
                            total += parseFloat(row.total_sin_categoria || 0);
                            return total.toFixed(2);
                        },
                        title: "Total"
                    }
                ]
            });
        },
        error: function (xhr, status, error) {
            console.error("❌ Error en AJAX:", status, error);
            console.error("❌ Respuesta del servidor:", xhr.responseText);
        }
    });
});

