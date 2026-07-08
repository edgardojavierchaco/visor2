document.addEventListener(
    "DOMContentLoaded",
    function(){


        const inputCue =
            document.getElementById(
                "id_cueanexo"
            );


        const lista =
            document.getElementById(
                "resultadoEscuelas"
            );



        const inputCui =
            document.getElementById(
                "id_cui"
            );


        const inputOferta =
            document.getElementById(
                "id_oferta"
            );


        const inputNombre =
            document.getElementById(
                "id_nom_est"
            );



        if(!inputCue){

            return;

        }



        let temporizador = null;



        inputCue.addEventListener(
            "keyup",
            function(){



                const texto =
                    this.value.trim();



                limpiarTimer();



                if(texto.length < 3){


                    lista.innerHTML="";


                    return;

                }



                temporizador =
                    setTimeout(
                        function(){

                            buscarEscuelas(texto);


                        },
                        300
                    );



            }
        );





        function limpiarTimer(){


            if(temporizador){


                clearTimeout(
                    temporizador
                );

            }

        }







        function buscarEscuelas(texto){


            fetch(
                `/sirtee/api/escuelas/?q=${texto}`
            )


            .then(
                response =>
                    response.json()
            )


            .then(
                data => {


                    mostrarResultados(
                        data
                    );


                }
            )

            .catch(
                error => {

                    console.error(
                        error
                    );

                }
            );


        }






        function mostrarResultados(
            escuelas
        ){


            lista.innerHTML="";

            if(!Array.isArray(escuelas)){
                return;
            }

            escuelas.forEach(
                function(escuela){



                    const boton =
                        document.createElement(
                            "button"
                        );


                    boton.type =
                        "button";


                    boton.className =
                        "list-group-item list-group-item-action";



                    boton.innerHTML = `

                        <strong>
                            ${escuela.cueanexo}
                        </strong>

                        <br>

                        ${escuela.nom_est}

                        <br>

                        <small>
                            ${escuela.oferta}
                        </small>

                    `;



                    boton.addEventListener(
                        "click",
                        function(){


                            seleccionarEscuela(
                                escuela
                            );


                        }
                    );



                    lista.appendChild(
                        boton
                    );



                }
            );


        }








        function seleccionarEscuela(
            escuela
        ){


            inputCue.value =
                escuela.cueanexo;


            inputCui.value =
                escuela.cui ||
                escuela.cui_loc ||
                "";



            inputOferta.value =
                escuela.oferta || "";



            inputNombre.value =
                escuela.nom_est || "";



            lista.innerHTML="";

        }



    }
);