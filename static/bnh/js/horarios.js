let actividadActual = null;



// ===============================
// ABRIR MODAL
// ===============================

function abrirHorarios(id){


    actividadActual = id;


    const modal =
    new bootstrap.Modal(
        document.getElementById(
            "horarioModal"
        )
    );


    modal.show();



    cargarHorarios();



}




// ===============================
// CERRAR
// ===============================

function cerrarHorarios(){


    const modal =
    bootstrap.Modal
    .getInstance(
        document.getElementById(
            "horarioModal"
        )
    );


    if(modal){

        modal.hide();

    }


}





// ===============================
// CARGAR HORARIOS
// ===============================

async function cargarHorarios(){



    const res = await fetch(

        `/bnh/horario/${actividadActual}/`

    );



    const html =
    await res.text();



    document.getElementById(
        "horariosList"
    ).innerHTML = html;



}





// ===============================
// GUARDAR
// ===============================

async function guardarHorario(){



const form =
document.getElementById(
    "horarioForm"
);



const data =
new FormData(form);





const res =
await fetch(

`/bnh/horario/${actividadActual}/agregar/`,

{

method:"POST",

body:data,

headers:{

"X-Requested-With":
"XMLHttpRequest"

}

}

);




const json =
await res.json();





if(!json.ok){


Swal.fire(

"Error",

json.mensaje || 
"Horario inválido",

"error"

);


return;


}





Swal.fire({

icon:"success",

title:"Horario agregado",

timer:1000,

showConfirmButton:false

});





form.reset();



cargarHorarios();



}






// ===============================
// ELIMINAR
// ===============================


async function eliminarHorario(id){



const confirmar =
await Swal.fire({

title:"Eliminar horario?",

icon:"warning",

showCancelButton:true


});




if(!confirmar.isConfirmed)

return;






const res =
await fetch(

`/bnh/horario/${id}/eliminar/`,

{

method:"GET",

headers:{

"X-Requested-With":
"XMLHttpRequest"

}

}

);




const json =
await res.json();




if(json.ok){


cargarHorarios();


}



}