
$(function () {
    var table = $('#data').DataTable({
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
            dataSrc: function (json) {
                // Verificar los datos recibidos en la consola
                console.log(json);
                return json;
            }
        },
        columns: [
            {"data": "cueanexo"},
            {"data": "nom_est"},
            {"data": "lengua"},
            {"data": "varones"},
            {"data": "mujeres"},
            {"data": "region_loc"},
            {"data": "localidad"},
            {"data": "localidad"}  // Esto es para las acciones (editar/eliminar)
        ],
        columnDefs: [
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="../list_superv_cue/' + row.cueanexo + '/" class="btn btn-success btn-xs btn-flat"><i class="fas fa-search"></i></a> '; 
                    
                    return buttons;
                }
            },
        ],
        footerCallback: function (row, data, start, end, display) {
            var api = this.api();

            // Función para sumar una columna
            var intVal = function (i) {
                return typeof i === 'string' ?
                    i.replace(/[\$,]/g, '') * 1 :
                    typeof i === 'number' ? i : 0;
            };

            // Sumar las columnas de varones y mujeres
            var totalVarones = api
                .column(3, { search: 'applied' })
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);

            var totalMujeres = api
                .column(4, { search: 'applied' })
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);

            // Verificar los totales calculados en la consola
            console.log('Total Varones:', totalVarones);
            console.log('Total Mujeres:', totalMujeres);

            // Asegurarse de que los totales se actualicen solo después de que los datos estén cargados
            setTimeout(function() {
                // Actualizar los totales directamente en el footer
                $('#totalVarones').html(totalVarones);
                $('#totalMujeres').html(totalMujeres);
            }, 100); // Esperar un pequeño retraso para asegurarse de que la tabla esté completamente renderizada
        }
    });
});

