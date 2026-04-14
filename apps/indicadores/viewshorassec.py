from django.views import View
from django.shortcuts import render
from django.db import connection

class DocentesPorHorasView(View):
    def get(self, request):
        # Obtener la región 
        region = request.GET.get('region', '')

        
        if not region or region == 'Provincial':
            query = """
            SELECT 
                region,
                nivel,
                denom_cargo,
                sit_rev,
                SUM(CASE 
                        WHEN hscat::int <= 6 THEN 1
                        ELSE 0 
                    END) AS hasta_6,
                SUM(CASE 
                        WHEN hscat::int > 6 AND hscat::int <= 15 THEN 1
                        ELSE 0 
                    END) AS hasta_15,
                SUM(CASE 
                        WHEN hscat::int > 15 AND hscat::int <= 30 THEN 1
                        ELSE 0 
                    END) AS hasta_30,
                SUM(CASE 
                        WHEN hscat::int > 30 AND hscat::int <= 33 THEN 1
                        ELSE 0 
                    END) AS hasta_33,
                SUM(CASE 
                        WHEN hscat::int > 33 THEN 1
                        ELSE 0 
                    END) AS mas_de_33
            FROM cenpe.docentesestatal
            WHERE ceic = '111'
            GROUP BY region, nivel,denom_cargo, sit_rev;
            """
        else:
            # caso en que se incluye 'region' en la consulta
            query = """
            SELECT 
                region, 
                nivel, 
                denom_cargo,
                sit_rev,
                SUM(CASE WHEN hscat::int <= 6 THEN 1 ELSE 0 END) AS hasta_6,
                SUM(CASE WHEN hscat::int > 6 AND hscat::int <= 15 THEN 1 ELSE 0 END) AS hasta_15,
                SUM(CASE WHEN hscat::int > 15 AND hscat::int <= 30 THEN 1 ELSE 0 END) AS hasta_30,
                SUM(CASE WHEN hscat::int > 30 AND hscat::int <= 33 THEN 1 ELSE 0 END) AS hasta_33,
                SUM(CASE WHEN hscat::int > 33 THEN 1 ELSE 0 END) AS mas_de_33
            FROM cenpe.docentesestatal
            WHERE ceic = '111' AND region = %s
            GROUP BY region, nivel, denom_cargo, sit_rev
            ORDER BY region, nivel;
            """
        
        with connection.cursor() as cursor:
            if not region or region == 'Provincial':
                cursor.execute(query)
            else:
                cursor.execute(query, [region])

            results = cursor.fetchall()

        
        data = {
            "hasta_6": 0,
            "hasta_15": 0,
            "hasta_30": 0,
            "hasta_33": 0,
            "mas_de_33": 0,
        }

        for row in results:
            data["hasta_6"] += row[4]
            data["hasta_15"] += row[5]
            data["hasta_30"] += row[6]
            data["hasta_33"] += row[7]
            data["mas_de_33"] += row[8]            
        
        for row in results:
            print(row)  
            data["hasta_6"] += row[4] if len(row) > 4 else 0
            data["hasta_15"] += row[5] if len(row) > 5 else 0
            data["hasta_30"] += row[6] if len(row) > 6 else 0
            data["hasta_33"] += row[7] if len(row) > 7 else 0
            data["mas_de_33"] += row[8] if len(row) > 8 else 0
            
            
        return render(request, 'indicadores/docentes_por_horas.html', {'data': data, 'results': results, 'region': region})
