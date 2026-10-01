let personaActualId = null;
let typingTimer = null;
let cuilValido = false;
let dniCuilValido = true;
let edadValida = true;


// =========================
// INIT
// =========================

initPersona();


function initPersona() {


    const cuil = document.querySelector("#id_cuil");


    if (cuil) {

        cuil.addEventListener(
            "input",
            onCuilInput
        );

    }

    const dni =
        document.querySelector("#id_dni");


    if(dni){

        dni.addEventListener(
            "input",
            validarDniConCuil
        );

    }

    const nacimiento =
        document.querySelector("#id_f_nacimiento");


    if(nacimiento){

        nacimiento.addEventListener(
            "change",
            validarEdad
        );

    }


    // Provincia con Select2
    $("#id_provincia").on(
        "change",
        function(){

            console.log(
                "Provincia:",
                this.value
            );


            cargarLocalidades({
                target:{
                    value:this.value
                }
            });

        }
    );

}



// =========================
// VALIDAR CUIL
// =========================

function validarCUIL(cuil) {


    cuil = cuil.replace(/\D/g,"");


    if(cuil.length !== 11)
        return false;



    const mult = [
        5,4,3,2,7,
        6,5,4,3,2
    ];


    let suma = 0;



    for(let i=0;i<10;i++){

        suma += 
        parseInt(cuil[i]) *
        mult[i];

    }



    let mod = suma % 11;


    let dig = 11 - mod;



    if(dig === 11)
        dig = 0;


    if(dig === 10)
        dig = 9;



    return dig === parseInt(cuil[10]);

}




// =========================
// INPUT CUIL
// =========================


function onCuilInput(e){


    clearTimeout(typingTimer);



    const valor = e.target.value.trim();


    personaActualId = null;

    cuilValido = false;



    setValue(
        "persona_id",
        ""
    );



    if(valor.length === 0){

        setStatus(
            "",
            ""
        );


        bloquearFormulario(true);

        return;

    }




    if(valor.length < 11){

        setStatus(
            "Escribiendo...",
            "gray"
        );


        bloquearFormulario(true);


        return;

    }





    if(!validarCUIL(valor)){


        setStatus(
            "CUIL inválido",
            "red"
        );


        bloquearFormulario(true);


        return;

    }




    setStatus(
        "Validando...",
        "orange"
    );



    typingTimer = setTimeout(()=>{


        buscarPersona(valor);



    },500);



}




// =========================
// BUSCAR PERSONA
// =========================


async function buscarPersona(cuil){



try{


    const res = await fetch(
        `/bnh/buscar-persona/?cuil=${cuil}`
    );



    const data = await res.json();




    if(!data.existe){


        setStatus(
            "✔ Nuevo CUIL",
            "green"
        );



        limpiarFormulario();



        cuilValido = true;


        bloquearFormulario(false);



        return;


    }





    personaActualId = data.id;


    cuilValido = true;




    setStatus(
        "✔ Persona encontrada",
        "green"
    );



    cargarDatos(data);



    bloquearFormulario(false);





}
catch(error){


    setStatus(
        "Error conexión",
        "red"
    );


    bloquearFormulario(true);


}



}






// =========================
// CARGAR DATOS PERSONA
// =========================


function cargarDatos(data){



setValue(
    "persona_id",
    data.id
);


setValue(
    "id_dni",
    data.dni
);


setValue(
    "id_apellido",
    data.apellido
);


setValue(
    "id_nombre",
    data.nombre
);


setValue(
    "id_sexo",
    data.sexo
);




setValue(
    "id_provincia",
    data.provincia
);



// cargar localidades después

if(data.provincia){


    cargarLocalidades({

        target:{
            value:data.provincia
        }

    });



    setTimeout(()=>{


        setValue(
            "id_localidad",
            data.localidad
        );


        $("#id_localidad")
        .trigger("change.select2");



    },300);



}



setValue(
    "id_codigo_area",
    data.codigo_area
);



setValue(
    "id_telefono",
    data.telefono
);





const whatsapp =
document.querySelector("#id_whatsapp");



if(whatsapp){

    whatsapp.checked =
    data.whatsapp;

}




setTimeout(()=>{


    if(window.jQuery && $.fn.select2){

        $(".select2")
        .trigger("change.select2");

    }



},100);



}






// =========================
// LOCALIDADES
// =========================
async function cargarLocalidades(e){


    const provincia = e.target.value;


    console.log(
        "Cargando localidades provincia:",
        provincia
    );



    const select =
        document.getElementById(
            "id_localidad"
        );



    if(!select)
        return;



    select.innerHTML =
    "<option value=''>Seleccione</option>";



    if(!provincia)
        return;




    try{


        const url =
        `/bnh/filtrar-localidades/?provincia=${provincia}`;



        console.log(
            "URL:",
            url
        );



        const res =
        await fetch(url);



        const data =
        await res.json();



        console.log(
            "Respuesta:",
            data
        );




        data.forEach(l=>{


            let option =
            document.createElement("option");



            option.value =
            l.c_localidad;



            option.textContent =
            l.descrip_localidad;



            select.appendChild(option);



        });




        $("#id_localidad")
        .trigger("change.select2");



    }
    catch(error){

        console.error(
            "Error localidades:",
            error
        );

    }


}



// =========================
// GUARDAR
// =========================


async function guardarPersona(){

validarEdad();



if(!edadValida){


    Swal.fire(
        "Error",
        "La fecha de nacimiento no es válida.",
        "warning"
    );


    return;

}

if(!dniCuilValido){


    Swal.fire(
        "Error",
        "El DNI no coincide con el CUIL.",
        "warning"
    );


    return;

}

if(!cuilValido){


    Swal.fire(
        "Error",
        "CUIL inválido",
        "warning"
    );


    return;

}




const form =
document.getElementById(
    "personaForm"
);



const data =
new FormData(form);




if(personaActualId){

    data.set(
        "persona_id",
        personaActualId
    );

}





try{


Swal.fire({

    title:"Guardando...",

    allowOutsideClick:false,


    didOpen:()=>{

        Swal.showLoading();

    }

});





const res =
await fetch(

"/bnh/guardar-persona-ajax/",

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



Swal.close();





if(!json.ok){


    Swal.fire(
        "Error",
        "No se pudo guardar",
        "error"
    );


    return;


}





personaActualId =
json.id;




personaActualId = json.id;


document
.querySelectorAll("#persona_id")
.forEach(el=>{

    el.value = json.id;

});



Swal.fire({

icon:
json.created
?"success"
:"info",


title:
json.created
?"Creado"
:"Actualizado",


text:
"Guardado correctamente"


});






}
catch(error){



Swal.close();


Swal.fire(
"Error",
"Error de conexión",
"error"
);



}



}








// =========================
// LIMPIAR
// =========================


function limpiarFormulario(){



[

"id_dni",

"id_apellido",

"id_nombre",

"id_sexo",

"id_provincia",

"id_localidad",

"id_codigo_area",

"id_telefono"

]


.forEach(id=>{


const el =
document.getElementById(id);



if(el)
el.value="";



});





const whatsapp =
document.getElementById(
"id_whatsapp"
);



if(whatsapp)
whatsapp.checked=false;





if(window.jQuery && $.fn.select2){


$(".select2")
.val(null)
.trigger("change.select2");


}




}






// =========================
// BLOQUEAR FORMULARIO
// =========================


function bloquearFormulario(state){



const form =
document.getElementById(
"personaForm"
);



if(!form)
return;





const elementos =
form.querySelectorAll(
"input, select"
);





elementos.forEach(el=>{


if(el.id==="id_cuil")
return;



el.disabled =
state;



});



}






// =========================
// HELPERS
// =========================


function setValue(id,value){


const el =
document.getElementById(id);



if(el)
el.value =
value || "";



}





function setStatus(text,color){


const el =
document.getElementById(
"cuil_status"
);



if(!el)
return;



el.textContent =
text;



el.style.color =
color;



}


// =========================
// VALIDAR DNI CONTRA CUIL
// =========================

function validarDniConCuil(){


    let cuil =
        $("#id_cuil")
        .val()
        .replace(/\D/g,"");



    let dni =
        $("#id_dni")
        .val()
        .replace(/\D/g,"");



    let mensaje =
        $("#dni_status");



    if(
        cuil.length !== 11 ||
        dni.length === 0
    ){

        mensaje.text("");

        dniCuilValido = true;

        return;

    }



    let dniDelCuil =
        cuil.substring(2,10);



    if(
        dniDelCuil !== dni
    ){


        mensaje.text(
            "El DNI no coincide con el CUIL ingresado."
        );


        dniCuilValido = false;



    }
    else{


        mensaje.text(
            ""
        );


        dniCuilValido = true;


    }


}

// =========================
// VALIDAR EDAD
// =========================

function validarEdad(){


    const fecha =
        $("#id_f_nacimiento").val();


    const mensaje =
        $("#edad_status");



    if(!fecha){

        mensaje.text("");

        edadValida = true;

        return;

    }



    const nacimiento =
        new Date(fecha);



    const hoy =
        new Date();



    let edad =
        hoy.getFullYear()
        -
        nacimiento.getFullYear();



    const mes =
        hoy.getMonth()
        -
        nacimiento.getMonth();



    if(
        mes < 0 ||
        (
            mes === 0 &&
            hoy.getDate() < nacimiento.getDate()
        )
    ){

        edad--;

    }



    if(edad < 16){


        mensaje.text(
            "La persona debe tener al menos 16 años."
        );


        edadValida = false;



    }
    else if(edad > 90){


        mensaje.text(
            "La edad no puede superar los 90 años."
        );


        edadValida = false;



    }
    else{


        mensaje.text("");

        edadValida = true;


    }


}