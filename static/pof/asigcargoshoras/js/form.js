var tblCargosHoras;
var vents = {
    items: {
        'unidad': '',
        'cant_cargos': 0,
        'cant_horas': 0,
        detcargoshoras: []
    },
    add: function (item) {  
        this.items.detcargoshoras.push(item);
        this.list();
    },
    calculate_invoice: function(){
        var subtotalcar = 0;
        var subtotalhs = 0;
        $.each(this.items.detcargoshoras, function (pos, dict){
            dict.subtcar = dict.cargos;
            dict.subths = dict.horas;
            subtotalcar+=dict.subtcar;
            subtotalhs+=dict.subths;
        });
        console.log(subtotalcar);
        console.log(subtotalhs);
        this.items.cant_cargos=subtotalcar;
        this.items.cant_horas=subtotalhs;
        $('input[name="cant_cargos"]').val(this.items.cant_cargos);
        $('input[name="cant_horas"]').val(this.items.cant_horas);
    },
    list: function () {
        this.calculate_invoice();
        tblCargosHoras = $('#tblCargosHoras').DataTable({
            responsive: true,
            autoWidth: false,
            destroy: true,
            data: this.items.detcargoshoras,
            columns: [
                {"data": "id"},
                {"data": "denom_cargoshoras"},
                {"data": "cargos"},
                {"data": "horas"},
                {"data": "puntos"},
                
            ],
            columnDefs: [
                {
                    targets: [0],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<a rel="remove" class="btn btn-danger btn-xs btn-flat" style="color: white;"><i class="fas fa-trash-alt"></i></a>';
                    }
                },                
                {
                    targets: [-3],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<input type="text" name="cargos" class="form-control form-control-sm input-sm" autocomplete="off" value="' + row.cargos + '">';
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<input type="text" name="horas" class="form-control form-control-sm input-sm" autocomplete="off" value="' + row.horas + '">';
                    }
                },
                
            ],
            rowCallback(row,data,displayNum,displayIndex,dataIndex){

            },
            initComplete: function (settings, json) {

            }
        });
    },
};


$(function () { 
    $('.select2').select2({
        theme: "bootstrap4",
        language: "es"
    });

    //Buscar cargos/horas
    $('input[name="search"]').autocomplete({
        source: function (request, response) {
            $.ajax({
                url: window.location.pathname,
                type: 'POST',
                data: {
                    'action': 'search_cargoshoras',
                    'term': request.term
                },
                dataType: 'json',
            }).done(function (data) {
                response(data);
            }).fail(function (jqXHR, textStatus, errorThrown) {
                //alert(textStatus + ': ' + errorThrown);
            }).always(function (data) {

            });
        },
        delay: 500,
        minLength: 1,
        select: function (event, ui) {
            event.preventDefault();
            console.clear();
            ui.item.cargos=1;
            ui.item.horas=1;
            ui.item.subtcar=0;
            ui.item.subths=0;            
            console.log(vents.items);
            vents.add(ui.item);            
            $(this).val('');
        }
    });

    // eliminar todo
    $('.btnRemoveAll').on('click', function(){
        if(vents.items.detcargoshoras.length===0) return false;
        alert_action('Notificación', '¿Estás seguro de eliminar todos los items de tu detalle?', function(){
            vents.items.detcargoshoras = [];
            vents.list();
        });        
    });

    //evento cantidades
    $('#tblCargosHoras tbody')
        .on('click', 'a[rel="remove"]', function(){
            var tr = tblCargosHoras.cell($(this).closest('td, li')).index(); 
            alert_action('Notificación', '¿Estás seguro de eliminar este item de tu detalle?', function(){
            vents.items.detcargoshoras.splice(tr.row,1);
            vents.list();
            });             
            
        })
        .on('change keyup', 'input[name="cargos"]', function(){
        console.clear();
        var cargo=parseInt($(this).val());
        var tr = tblCargosHoras.cell($(this).closest('td, li')).index();       
        //var data = tblCargosHoras.row(tr.row).node(); 
        vents.items.detcargoshoras[tr.row].cargos = cargo;
        vents.items.detcargoshoras[tr.row].subtcar = cargo;        
        vents.calculate_invoice();
        $('td:eq(5)',tblCargosHoras.row(tr.row).node()).html('$' + vents.items.detcargoshoras[tr.row].subtcar);        
        })
        .on('change keyup', 'input[name="horas"]', function(){
        console.clear();
        var hora=parseInt($(this).val());
        var tr = tblCargosHoras.cell($(this).closest('td, li')).index();       
        //var data = tblCargosHoras.row(tr.row).node(); 
        vents.items.detcargoshoras[tr.row].horas = hora;
        vents.items.detcargoshoras[tr.row].subths = hora;        
        vents.calculate_invoice();
        $('td:eq(6)',tblCargosHoras.row(tr.row).node()).html('$' + vents.items.detcargoshoras[tr.row].subtcar);        
    });

 });