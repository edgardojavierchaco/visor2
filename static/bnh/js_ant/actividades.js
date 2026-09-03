// =========================
// INIT
// =========================

$(document).ready(function(){


    // =========================
    // SELECT2
    // =========================

    $(".select2").select2({
        width:"100%"
    });



    // =========================
    // FECHA F_HASTA AUTOMÁTICA
    // TITULAR / INTERINO
    // =========================

    $("#id_sit_revista").on(
        "change",
        function(){


            let texto = 
                $("#id_sit_revista option:selected")
                .text()
                .trim()
                .toUpperCase();



            console.log(
                "Situación revista:",
                texto
            );



            if(
                texto === "TITULAR" ||
                texto === "INTERINO"
            ){


                let hoy =
                    new Date();



                let anio =
                    hoy.getFullYear() + 28;



                let fecha =
                    anio + "-12-31";



                console.log(
                    "Fecha hasta:",
                    fecha
                );



                $("#id_f_hasta")
                    .val(fecha)
                    .trigger("change");


            }


        }
    );





    // =========================
    // FILTROS AJAX
    // =========================

    $(document).on(
        "change",
        "#id_modalidad,#id_niveles",
        actualizarFiltros
    );





    // =========================
    // BOTON GUARDAR
    // =========================

    $("#btnGuardarActividad")
        .on(
            "click",
            guardarActividad
        );



// =========================
// AYUDAS AUTOMÁTICAS
// =========================


$("#id_sit_revista")
.on(
"change",
function(){

    mostrarAyuda(
        "situacion",
        $(this).val()
    );

});




$("#id_cond_actividad")
.on(
"change",
function(){

    mostrarAyuda(
        "condicion",
        $(this).val()
    );

});




$("#id_t_designacion")
.on(
"change",
function(){

    mostrarAyuda(
        "t_designacion",
        $(this).val()
    );

});




$("#id_funciones")
.on(
"change",
function(){

    mostrarAyuda(
        "funcion",
        $(this).val()
    );

});

});


// =========================
// FILTROS AJAX
// =========================

async function actualizarFiltros(){


    console.log(
        "🔥 actualizarFiltros ejecutado"
    );



    let modalidad =
        $("#id_modalidad").val();



    let nivel =
        $("#id_niveles").val();



    let url =
    `/bnh/filtrar-datos-actividad/?modalidad=${modalidad || ""}&nivel=${nivel || ""}`;



    try{


        let respuesta =
            await fetch(
                url,
                {

                    headers:{
                        "X-Requested-With":
                        "XMLHttpRequest"
                    }

                }
            );



        let data =
            await respuesta.json();



        cargarSelect(
            "#id_ceic",
            data.ceic,
            "c_ceic",
            "descripcion"
        );



        cargarSelect(
            "#id_grado_anio",
            data.grado,
            "c_grado_anio",
            "nombre_grado_anio"
        );



        cargarSelect(
            "#id_secciones",
            data.secciones,
            "c_seccion",
            "nombre_seccion"
        );



    }
    catch(error){


        console.error(
            "Error filtros:",
            error
        );


    }


}

// =========================
// RECARGAR SELECT
// =========================

function cargarSelect(
    selector,
    data,
    valueKey,
    textKey
){


    let select =
        document.querySelector(selector);



    if(!select)
        return;



    let valorActual =
        $(select).val();



    $(select)
        .select2("destroy");



    $(select)
        .empty();



    $(select)
        .append(
            new Option(
                "---------",
                ""
            )
        );



    data.forEach(
        item=>{


            $(select)
                .append(

                    new Option(
                        item[textKey],
                        item[valueKey]
                    )

                );


        }
    );



    $(select)
        .val(valorActual);



    $(select)
        .select2({

            width:"100%"

        });


}

// =========================
// GUARDAR ACTIVIDAD
// =========================

async function guardarActividad(){


    console.log(
        "💾 Guardando actividad..."
    );



    const form =
        document.querySelector(
            "#actividadForm"
        );



    if(!form){


        console.error(
            "No existe actividadForm"
        );


        return;

    }



    const datos =
        new FormData(form);




    try{


        const respuesta =
            await fetch(

                window.location.pathname,

                {

                    method:"POST",

                    body:datos,


                    headers:{

                        "X-Requested-With":
                        "XMLHttpRequest"

                    }


                }

            );



        const json =
            await respuesta.json();



        console.log(
            "RESPUESTA DJANGO:",
            json
        );



        if(json.ok){



            alert(
                json.mensaje
            );



            window.location.href =
            `/bnh/personas/${json.persona_id}/carga-personal/`;



        }
        else{


            console.log(
                json.errores
            );



            alert(

                json.mensaje ||
                "Error al guardar actividad"

            );


        }



    }
    catch(error){


        console.error(
            "Error guardando:",
            error
        );


    }


}

// =========================
// MOSTRAR AYUDA MODAL
// =========================

async function mostrarAyuda(tipo,id){


    if(!id){
        return;
    }


    try{


        const respuesta =
            await fetch(
                `/bnh/ayuda-renpe/?tipo=${tipo}&id=${id}`
            );



        const data =
            await respuesta.json();



        if(!data.ok){

            console.log(
                "Sin ayuda"
            );

            return;
        }



        $("#modalAyudaTitulo")
            .text(data.titulo);



        $("#modalAyudaTexto")
            .html(data.ayuda);



        const modal =
            new bootstrap.Modal(
                document.getElementById("modalAyuda")
            );



        modal.show();



    }
    catch(error){


        console.error(
            "Error ayuda:",
            error
        );


    }


}