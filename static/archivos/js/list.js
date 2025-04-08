$(function () {
    $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            data: { 'action': 'searchdata' },
            dataSrc: ""
        },
        columns: [
            { "data": "id" },
            { "data": "cueanexo" },
            { "data": "asunto" },
            { "data": "nivel" },
            { "data": "t_norma" },
            { "data": "nro_normativa" },
            { "data": "anio" },
            { "data": "descripcion" },
            { "data": "descripcion" }
        ],
        columnDefs: [{
            targets: [-1],
            class: 'text-center',
            orderable: false,
            render: function (data, type, row) {
                var buttons = '<a href="../editar/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                buttons += '<a href="../eliminar/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                buttons += '<button type="button" class="btn btn-info btn-xs btn-flat view-pdf" data-id="' + row.id + '"><i class="fas fa-file-pdf"></i></button>'; 
                return buttons;
            }
        }],
        initComplete: function (settings, json) {
            // Código a ejecutar cuando la tabla se haya inicializado
        }
    });

    // Evento para ver PDF
    $('#data tbody').on('click', 'button.view-pdf', function () {
        //let cueanexo = $(this).data('cueanexo');
        //let asunto = $(this).data('asunto');
        let id=$(this).data('id');

        $.post("/cargar/buscar/", { action: 'buscar_pdf_por_id', id:id }, function (response) {
            if (response.ruta_pdf) {
                window.open(response.ruta_pdf, '_blank');
            } else {
                alert(response.error || "Error al buscar el PDF.");
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            console.log("Error en la petición:", textStatus, errorThrown);
            alert("Error en la petición.");
        });
    });
});
