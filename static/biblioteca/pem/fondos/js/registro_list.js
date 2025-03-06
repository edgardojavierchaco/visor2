$(function () {
    // Destruir DataTable si ya está inicializada
    if ($.fn.DataTable.isDataTable('#data')) {
        $('#data').DataTable().clear().destroy();  // Destruye y limpia la tabla antes de reinicializar
    }

    // Inicializar DataTable
    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'GET',
            dataType: "json",
            dataSrc: ""  // Elimina la necesidad de un wrapper "data"
        },
        columns: [
            {"data": "cueanexo"},
            {"data": "mes"},
            {"data": "anio"},
            {"data": "destino"},
            {"data": "descripcion"},
            {
                "data": "acciones",  // Este campo contiene el id del registro
                "render": function (data, type, row) {
                    return `                        
                        <a href="../regfondos/delete/${data}/" class="btn btn-danger btn-xs btn-flat">
                            <i class="fas fa-trash-alt"></i>
                        </a>
                    `;
                }
            }
        ]
    });
});
