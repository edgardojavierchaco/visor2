from .models import Examen, Preguntas, GrupoAplicante
from django.shortcuts import get_object_or_404

def make_new_examen(id_grupo, materia, tipo):
    
    grupo_aplicante = get_object_or_404(GrupoAplicante, pk=id_grupo)
    
    examen = Examen.objects.create(
        idgrupo = grupo_aplicante,
        materia = materia,
        tipo = tipo,
    )
    if tipo == '1': #primaria
        if materia == 'CONTEXTO':
            preguntas = [
                Preguntas(num_pregunta='1', limite='5', idexamen=examen),
                Preguntas(num_pregunta='2', limite='5', idexamen=examen),
                Preguntas(num_pregunta='3', limite='5', idexamen=examen),
                Preguntas(num_pregunta='4', limite='5', idexamen=examen),
                Preguntas(num_pregunta='5.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='5.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='5.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='6.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='6.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='6.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='6.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.5', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.5', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.6', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.7', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.8', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.9', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.5', limite='2', idexamen=examen),


            ]
            
        elif materia == 'MATEMATICA':
            preguntas = [
                Preguntas(num_pregunta='1.1', limite='3', idexamen=examen), # modificada
                Preguntas(num_pregunta='1.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='1.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='5', limite='2', idexamen=examen),
                Preguntas(num_pregunta='6', limite='3', idexamen=examen),
                Preguntas(num_pregunta='7', limite='3', idexamen=examen),
                Preguntas(num_pregunta='8.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='8.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9', limite='3', idexamen=examen),
                Preguntas(num_pregunta='10.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='10.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='10.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='11.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='11.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='11.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='12.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='12.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='12.3', limite='2', idexamen=examen),
            ]
        elif materia == 'NATURALES':
            preguntas = [
                Preguntas(num_pregunta='13', limite='2', idexamen=examen),
                Preguntas(num_pregunta='14.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='14.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='14.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='15', limite='3', idexamen=examen),  
                Preguntas(num_pregunta='16', limite='3', idexamen=examen),
                Preguntas(num_pregunta='17', limite='3', idexamen=examen), 
                Preguntas(num_pregunta='18.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='18.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='18.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='19', limite='3', idexamen=examen),  
                Preguntas(num_pregunta='20', limite='3', idexamen=examen),
                Preguntas(num_pregunta='21.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='21.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='21.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='22.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='22.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='22.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='23.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='23.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='23.3', limite='2', idexamen=examen), 
                Preguntas(num_pregunta='24.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='24.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='24.3', limite='2', idexamen=examen),                                                 
                                            
            ]
            
        elif materia == 'LENGUA':
            preguntas = [
                Preguntas(num_pregunta='25.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='25.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='25.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='26', limite='2', idexamen=examen),
                Preguntas(num_pregunta='27', limite='3', idexamen=examen),
                Preguntas(num_pregunta='28.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='28.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='28.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='29.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='29.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='29.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='30.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='30.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='30.3', limite='2', idexamen=examen), 
                Preguntas(num_pregunta='31.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='31.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='31.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='32', limite='3', idexamen=examen),
                Preguntas(num_pregunta='33.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='33.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='33.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='34', limite='3', idexamen=examen),
                Preguntas(num_pregunta='35', limite='3', idexamen=examen),
                Preguntas(num_pregunta='36', limite='3', idexamen=examen),           
  
                
            ]
            
        elif materia == 'SOCIALES':
            preguntas = [
                # Preguntas(num_pregunta='1.1', correcta='2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='37', limite='3', idexamen=examen),
                Preguntas(num_pregunta='38', limite='3', idexamen=examen),
                Preguntas(num_pregunta='39', limite='2', idexamen=examen),
                Preguntas(num_pregunta='40', limite='2', idexamen=examen),
                Preguntas(num_pregunta='41.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='41.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='41.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='42', limite='3', idexamen=examen),
                Preguntas(num_pregunta='43.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='43.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='43.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='44', limite='3', idexamen=examen),
                Preguntas(num_pregunta='45.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='45.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='45.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='46.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='46.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='46.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='47.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='47.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='47.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='48.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='48.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='48.3', limite='3', idexamen=examen),
            ]
            

            
        # Guarda todas las Preguntas en la base de datos
        Preguntas.objects.bulk_create(preguntas)
    
    elif tipo == '2': # SECUNDARIA
        if materia == 'CONTEXTO':
            preguntas = [
                Preguntas(num_pregunta='1', limite='5', idexamen=examen),
                Preguntas(num_pregunta='2', limite='5', idexamen=examen),
                Preguntas(num_pregunta='3', limite='5', idexamen=examen),
                Preguntas(num_pregunta='4', limite='5', idexamen=examen),
                Preguntas(num_pregunta='5.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='5.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='5.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='5.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='6', limite='4', idexamen=examen),
                Preguntas(num_pregunta='7.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9.5', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.5', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.6', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.7', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.8', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.9', limite='2', idexamen=examen),
                Preguntas(num_pregunta='10.10', limite='2', idexamen=examen),
                Preguntas(num_pregunta='11.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='11.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='11.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='11.4', limite='2', idexamen=examen),
                Preguntas(num_pregunta='11.5', limite='2', idexamen=examen),            

            ]
            
        elif materia == 'MATEMATICA':
            preguntas = [
                Preguntas(num_pregunta='1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='3.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='3.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='3.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='4.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='4.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='4.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='5', limite='3', idexamen=examen),
                Preguntas(num_pregunta='6', limite='2', idexamen=examen),
                Preguntas(num_pregunta='7', limite='3', idexamen=examen),
                Preguntas(num_pregunta='8.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='8.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='8.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='9', limite='3', idexamen=examen),
                Preguntas(num_pregunta='10.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='10.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='10.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='11.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='11.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='11.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='12.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='12.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='12.3', limite='3', idexamen=examen),

            ]
        elif materia == 'NATURALES':
            preguntas = [
                Preguntas(num_pregunta='13', limite='2', idexamen=examen),
                Preguntas(num_pregunta='14.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='14.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='14.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='15', limite='2', idexamen=examen),  
                Preguntas(num_pregunta='16.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='16.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='16.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='17', limite='2', idexamen=examen), 
                Preguntas(num_pregunta='18', limite='3', idexamen=examen),
                Preguntas(num_pregunta='19', limite='2', idexamen=examen),  
                Preguntas(num_pregunta='20.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='20.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='20.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='21.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='21.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='21.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='22.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='22.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='22.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='23.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='23.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='23.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='24', limite='3', idexamen=examen),
                                                                          
            ]
            
        elif materia == 'LENGUA':
            preguntas = [
                Preguntas(num_pregunta='25.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='25.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='25.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='26', limite='2', idexamen=examen),
                Preguntas(num_pregunta='27.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='27.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='27.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='28.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='28.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='28.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='29.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='29.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='29.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='30', limite='2', idexamen=examen),
                Preguntas(num_pregunta='31.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='31.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='31.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='32', limite='3', idexamen=examen),
                Preguntas(num_pregunta='33', limite='3', idexamen=examen),
                Preguntas(num_pregunta='34.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='34.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='34.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='35.1', limite='3', idexamen=examen),
                Preguntas(num_pregunta='35.2', limite='3', idexamen=examen),
                Preguntas(num_pregunta='35.3', limite='3', idexamen=examen),
                Preguntas(num_pregunta='36', limite='3', idexamen=examen),           
  
   
            ]
            
        elif materia == 'SOCIALES':
            preguntas = [
                # Preguntas(num_pregunta='1.1', correcta='2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='37.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='37.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='37.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='38', limite='2', idexamen=examen),
                Preguntas(num_pregunta='39', limite='2', idexamen=examen),
                Preguntas(num_pregunta='40.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='40.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='40.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='41', limite='3', idexamen=examen),
                Preguntas(num_pregunta='42', limite='3', idexamen=examen),
                Preguntas(num_pregunta='43', limite='3', idexamen=examen),
                Preguntas(num_pregunta='44.1', limite='2', idexamen=examen), # modificada
                Preguntas(num_pregunta='44.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='44.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='45', limite='3', idexamen=examen),
                Preguntas(num_pregunta='46.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='46.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='46.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='47.1', limite='2', idexamen=examen),
                Preguntas(num_pregunta='47.2', limite='2', idexamen=examen),
                Preguntas(num_pregunta='47.3', limite='2', idexamen=examen),
                Preguntas(num_pregunta='48', limite='3', idexamen=examen),

            ]
            
        # Guarda todas las Preguntas en la base de datos
        Preguntas.objects.bulk_create(preguntas)
