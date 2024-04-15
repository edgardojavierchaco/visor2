function alert_jqueryvalidacion(){
    $.confirm({
        theme: 'modern',
        title: '',
        icon: 'fa-solid fa-circle-info text-danger',
        content: "Ingrese un Cueanexo válido (9 dígitos, los dos primeros deben ser '22')",
        columnClass: 'medium',
        typeAnimated: true,
        cancelButtonClass: 'btn-primary',
        draggable: true,
        dragWindowBorder: false,
        buttons: {            
            danger: {
                text: 'OK',
                btnClass: 'btn-green',
                action: function () {
                    
                }
            },
        }
    })
}

function avisoregion(){
    $.confirm({
        theme: 'modern',
        title: '',
        icon: 'fas fa-exclamation-triangle text-warning',
        content: 'Si selecciona una Región Educativa no seleccione Localidad y/o Departamento',
        columnClass: 'medium',
        typeAnimated: true,
        cancelButtonClass: 'btn-primary',
        draggable: true,
        dragWindowBorder: false,
        buttons: {            
            danger: {
                text: 'OK',
                btnClass: 'btn-green',
                action: function () {
                    
                }
            },
        }
    })
}

function mensaje_error(obj){
    var html='';
    if(typeof(obj)==='object'){
        html='<ul style="text-align: center;">';
        $.each(obj,function(key,value){
            html+='<li>'+key+': '+value+'</li>';
        });
        html+='</ul>';
    }
    else{
        html='<p>'+obj+'</p>';
    }   
    
    Swal.fire({
        title:'Error!',
        html: html,
        icon: 'error'
    });
}