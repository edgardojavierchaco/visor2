// =========================
// 🔥 MOSTRAR ERRORES BONITO
// =========================
function message_error(obj) {
    let html = '';

    if (typeof obj === 'object') {

        html = '<ul style="text-align:left;">';

        $.each(obj, function (key, value) {

            // 🔥 Si es array (errores de Django)
            if (Array.isArray(value)) {

                value.forEach(function (error) {
                    html += `<li><b>${key}</b>: ${error}</li>`;
                });

            } else if (typeof value === 'object') {

                // 🔥 nested errors (muy importante)
                $.each(value, function (k, v) {
                    html += `<li><b>${k}</b>: ${v}</li>`;
                });

            } else {

                html += `<li>${value}</li>`;
            }
        });

        html += '</ul>';

    } else {
        html = `<p>${obj}</p>`;
    }

    Swal.fire({
        title: 'Error',
        html: html,
        icon: 'error'
    });
}


// =========================
// 🚀 AJAX GENÉRICO
// =========================
function submit_with_ajax(url, title, content, parameters, callback) {

    $.confirm({
        theme: 'material',
        title: title,
        icon: 'fa fa-info',
        content: content,
        columnClass: 'small',
        typeAnimated: true,

        buttons: {

            confirm: {
                text: "Sí",
                btnClass: 'btn-primary',

                action: function () {

                    $.ajax({
                        url: url,
                        type: 'POST',
                        data: parameters,
                        dataType: 'json',
                        processData: false,
                        contentType: false,

                        // 🔥 CSRF AUTOMÁTICO (CLAVE)
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }

                    }).done(function (data) {

                        console.log("RESPONSE:", data);

                        // =========================
                        // ✅ CASO OK
                        // =========================
                        if (!data.error) {
                            callback();
                            return;
                        }

                        // =========================
                        // ❌ ERRORES DJANGO
                        // =========================
                        if (data.errors) {
                            message_error(data.errors);
                            return;
                        }

                        // =========================
                        // ❌ ERROR SIMPLE
                        // =========================
                        message_error(data.message || "Ocurrió un error");

                    }).fail(function (jqXHR) {

                        console.error("AJAX ERROR:", jqXHR.responseText);

                        Swal.fire({
                            icon: 'error',
                            title: 'Error AJAX',
                            text: 'Ver consola (F12)'
                        });

                    });
                }
            },

            cancel: {
                text: "No",
                btnClass: 'btn-red'
            }
        }
    });
}


// =========================
// 🔐 OBTENER CSRF COOKIE
// =========================
function getCookie(name) {

    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {

        const cookies = document.cookie.split(';');

        for (let i = 0; i < cookies.length; i++) {

            let cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }

    return cookieValue;
}


// =========================
// ⚠️ CONFIRM SIMPLE
// =========================
function alert_action(title, content, callback) {

    Swal.fire({
        title: title,
        html: content,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sí',
        cancelButtonText: 'No'

    }).then((result) => {
        if (result.isConfirmed) {
            callback();
        }
    });
}