$(function () {

    const tableId = '#data';

    if ($.fn.DataTable.isDataTable(tableId)) {
        $(tableId).DataTable().clear().destroy();
    }

    $(tableId).DataTable({
        responsive: true,
        autoWidth: false,
        ajax: {
            url: window.location.pathname,
            type: "GET",
            dataSrc: "data"
        },
        columns: [
            { data: "cueanexo" },
            { data: "mes" },
            { data: "anio" },
            { data: "destino" },
            { data: "descripcion" },
            {
                data: "id",
                orderable: false,
                render: function (data) {
                    return `
                        <a href="../regfondos/delete/${data}/"
                           class="btn btn-danger btn-xs btn-flat">
                            <i class="fas fa-trash-alt"></i>
                        </a>
                    `;
                }
            }
        ]
    });

});