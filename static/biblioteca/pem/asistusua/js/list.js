$(document).ready(function () {

    console.log("🔥 JS funcionando");

    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,

        ajax: {
            url: window.location.pathname,
            type: 'POST',
            data: { action: 'searchdata' },
            dataSrc: ""
        },

        columns: [
            { data: "cueanexo" },
            { data: "mes" },
            { data: "anio" },
            { data: "nivel" },
            { data: "usuario" },
            { data: "varones" },
            { data: "total" },
            { data: "id" }
        ],

        columnDefs: [{
            targets: -1,
            class: 'text-center',
            orderable: false,
            render: function (data, type, row) {
                return `
                    <a href="../update/${row.id}/" class="btn btn-warning btn-xs">
                        <i class="fas fa-edit"></i>
                    </a>
                    <a href="../delete/${row.id}/" class="btn btn-danger btn-xs">
                        <i class="fas fa-trash"></i>
                    </a>
                `;
            }
        }],

        drawCallback: function () {

            console.log("✅ sumando datos");

            let sumaVarones = 0;
            let sumaTotales = 0;

            this.api().rows({ search: 'applied' }).every(function () {
                let d = this.data();

                console.log("fila:", d); // 🔥 DEBUG REAL

                sumaVarones += Number(d.varones) || 0;
                sumaTotales += Number(d.total) || 0;
            });

            $('#varones').html(sumaVarones);
            $('#totales').html(sumaTotales);
        }
    });

});