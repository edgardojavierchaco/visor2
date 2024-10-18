from django.shortcuts import render
from django.db import connection

def asistencia_view(request):
    cueanexo = request.user.username  

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                cueanexo, 
                dni,
                ape_nombre,
                hs_cat,
                SUM(debio_asistir) AS total_debio_asistir,
                SUM(oblig_conc) AS total_oblig_conc,
                SUM(lic_perm) AS total_lic_perm,
                SUM(inasist_inj) AS total_inasist_inj,
                SUM(inasist_o_causas) AS total_inasist_o_causas,
                SUM(inasist_just) AS total_inasist_just,
                SUM(hs_paro) AS total_hs_paro
            FROM 
                docentes.asistencia_horas
            WHERE
                cueanexo = %s
            GROUP BY 
                cueanexo, 
                dni,
                ape_nombre,
                hs_cat;
        """, [cueanexo])
        results = cursor.fetchall()

    context = {
        'results': results
    }
    return render(request, 'asistendoc/asistenciadoc.html', context)


def asistencia_cargos_view(request):
    cueanexo = request.user.username  

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                cueanexo, 
                dni,
                ape_nombre,
                cargos,
                SUM(debio_asistir) AS total_debio_asistir,
                SUM(oblig_conc) AS total_oblig_conc,
                SUM(lic_perm) AS total_lic_perm,
                SUM(inasist_inj) AS total_inasist_inj,
                SUM(inasist_o_causas) AS total_inasist_o_causas,
                SUM(inasist_just) AS total_inasist_just,
                SUM(hs_paro) AS total_hs_paro
            FROM 
                docentes.asistencia_cargos
            WHERE
                cueanexo = %s
            GROUP BY 
                cueanexo, 
                dni,
                ape_nombre,
                cargos;
        """, [cueanexo])
        results = cursor.fetchall()

    context = {
        'results': results
    }
    return render(request, 'asistendoc/asistenciacargos.html', context)


