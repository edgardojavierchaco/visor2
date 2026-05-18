var asigna = {
    items : {
        supervisor: '',
        total: 0,
        detescuelas: []
    },
    add: function(item) {
        this.items.detescuelas.push(item);
        this.list();
    },
    calculate_invoice: function() {
        var cuenta = 0;
        $.each(this.items.detescuelas, function(pos, dict) {
            cuenta += 1;
        });
        this.items.total = cuenta;
        $('input[name="total"]').val(this.items.total);
    },
    list: function () {
        this.calculate_invoice();

        $('#tblEscuelas').DataTable({
            responsive: true,
            autoWidth: false,
            destroy: true,
            data: this.items.detescuelas,
            columns: [
                {"data": "id"},
                {"data": "cueanexo"},
                {"data": "nom_est"},
                {"data": "oferta"},
                {"data": "region"}
            ],
            columnDefs: [
                {
                    targets: [0],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<a href="#" rel="remove" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    }
                }
            ],
            initComplete: function (settings, json) {
                // Puedes agregar funciones adicionales después de que la tabla se haya renderizado aquí
            }
        });
    },
};

$(function () {
    $('.select2').select2({
        theme: "bootstrap4",
        language: 'es'
    });

    // Eliminar todos los items
    $('.btnRemoveAll').on('click', function () {
        if (asigna.items.detescuelas.length === 0) return false;
        alert_action('Notificación', '¿Estas seguro de eliminar todos los items de tu detalle?', function () {
            asigna.items.detescuelas = [];
            asigna.list();
        });
    });

    // Eliminar
    $('#tblEscuelas tbody')
        .on('click', 'a[rel="remove"]', function() {
            var tr = $('#tblEscuelas').DataTable().cell($(this).closest('td, li')).index();
            alert_action('Notificación', '¿Estas seguro de eliminar el item de tu detalle?', function () {
            asigna.items.detescuelas.splice(tr.row, 1);
            asigna.list();
        });            
    });

    // Evento Limpiar
    $('.btnClearSearch').on('click',function(){
        $('input[name="search"]').val('').focus();
    })

    // Evento Submit
    $('form').on('submit', function(e){
        e.preventDefault();

        if(asigna.items.detescuelas.length === 0){
            message_error('Debe al menos tener un item en su detalle');
            return false;
        }
        asigna.items.supervisor = $('select[name="supervisor"]').val();
        var parameters= new FormData();
        parameters.append('action', $('input[name="action"]').val());
        parameters.append('asignado',JSON.stringify(asigna.items));
        submit_with_ajax(window.location.pathname, 'Notificación','¿Estás seguro de realizar la siguiente acción?',parameters,function () {
            location.href = '/sup/asign/';
        });
    })

    // Buscar escuelas
    $('input[name="search"]').autocomplete({
        source: function (request, response) {
            $.ajax({
                url: window.location.pathname,
                type: 'POST',
                data: {
                    'action': 'search_schools',
                    'term': request.term
                },
                dataType: 'json',
            }).done(function (data) {
                response(data);
            }).fail(function (jqXHR, textStatus, errorThrown) {
                console.error(textStatus + ': ' + errorThrown);
            });
        },
        delay: 500,
        minLength: 1,
        select: function (event, ui) {
            event.preventDefault();
            ui.item.total = 0;
            // Agrega la escuela seleccionada al detalle con la oferta
            ui.item.total = 0;
            asigna.add({
                id: ui.item.id,
                cueanexo: ui.item.cueanexo,
                nom_est: ui.item.nom_est,
                oferta: ui.item.oferta, 
                region: ui.item.region
            });
            $(this).val('');
        }
    });
    asigna.list();
});
