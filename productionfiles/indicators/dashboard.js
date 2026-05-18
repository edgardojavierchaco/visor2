const nivel =
    document.getElementById('nivel');

const orientacionWrapper =
    document.getElementById(
        'orientacion-wrapper'
    );

const consultarBtn =
    document.getElementById(
        'consultar-btn'
    );

const results =
    document.getElementById(
        'dashboard-results'
    );

let chart = null;


/* NIVEL */

nivel.addEventListener(
    'change',
    ()=>{

        if(
            nivel.value==='SECUNDARIA' ||
            nivel.value==='TECNICA'
        ){
            orientacionWrapper
                .style.display='flex';
        }
        else{
            orientacionWrapper
                .style.display='none';
        }
    }
);


/* CONSULTA */

consultarBtn.addEventListener(
    'click',
    async ()=>{

        const cueanexo =
            document.getElementById(
                'cueanexo'
            ).value;

        const nivelVal =
            nivel.value;

        const orientacion =
            document.getElementById(
                'orientacion'
            ).value;

        let url =
            `/indica/indicators/?cueanexo=${cueanexo}&nivel=${nivelVal}`;

        if(
            nivelVal==='SECUNDARIA' ||
            nivelVal==='TECNICA'
        ){
            url +=
            `&orientacion=${orientacion}`;
        }

        try{

            const response =
                await fetch(url);

            if(!response.ok){
                throw new Error(
                    `HTTP ${response.status}`
                );
            }

            const data =
                await response.json();

            renderDashboard(data);

        }catch(error){

            results.innerHTML=`
                <div class="panel">
                    Error consultando API
                </div>
            `;

            console.error(error);
        }

    }
);


/* RENDER */

function renderDashboard(data){

    if(
        !data ||
        !data.results ||
        data.results.length===0
    ){
        results.innerHTML=`
            <div class="empty-state">
                Sin datos
            </div>
        `;
        return;
    }

    const periods =
        data.results;

    const first =
        periods[0].indicators;

    const tpe =
        first.find(
            x=>x.tasa==='TPE'
        );

    const tr =
        first.find(
            x=>x.tasa==='TR'
        );

    const tai =
        first.find(
            x=>x.tasa==='TAI'
        );

    results.innerHTML=`

    <div class="cards-grid">

        <div class="kpi-card tpe">
            <div class="kpi-title">
                TPE
            </div>

            <div class="kpi-value">
                ${avg(tpe).toFixed(1)}%
            </div>
        </div>

        <div class="kpi-card tr">
            <div class="kpi-title">
                TR
            </div>

            <div class="kpi-value">
                ${avg(tr).toFixed(1)}%
            </div>
        </div>

        <div class="kpi-card tai">
            <div class="kpi-title">
                TAI
            </div>

            <div class="kpi-value">
                ${avg(tai).toFixed(1)}%
            </div>
        </div>

    </div>

    <div class="panel">
        <canvas id="chart"></canvas>
    </div>

    <div class="panel">
        ${buildTables(periods)}
    </div>
    `;

    drawChart(periods);
}


/* PROMEDIO */

function avg(obj){

    if(!obj){
        return 0;
    }

    const vals =
        Object.entries(obj)
        .filter(
            ([k])=>k!=='tasa'
        )
        .map(
            ([k,v])=>v
        );

    return (
        vals.reduce(
            (a,b)=>a+b,
            0
        ) / vals.length
    );
}


/* TABLAS */

function buildTables(periods){

    let html='';

    periods.forEach(period=>{

        html += `
            <h3 class="period-title">
                ${period.period}
            </h3>
        `;

        html += '<table>';

        const cols =
            Object.keys(
                period.indicators[0]
            );

        html += '<tr>';

        cols.forEach(c=>{
            html += `<th>${c}</th>`;
        });

        html += '</tr>';

        period.indicators.forEach(r=>{

            html += '<tr>';

            cols.forEach(c=>{
                html += `
                    <td>${r[c]}</td>
                `;
            });

            html += '</tr>';
        });

        html += '</table>';
    });

    return html;
}


/* GRAFICO */

function drawChart(periods){

    const ctx =
        document.getElementById(
            'chart'
        );

    if(chart){
        chart.destroy();
    }

    const tpe =
        periods[0].indicators.find(
            x=>x.tasa==='TPE'
        );

    const labels =
        Object.keys(tpe)
        .filter(
            x=>x!=='tasa'
        );

    const datasets=[];

    periods.forEach(period=>{

        ['TPE','TR','TAI']
        .forEach(tasa=>{

            const row =
                period.indicators.find(
                    x=>x.tasa===tasa
                );

            let color='#3b82f6';

            if(tasa==='TR'){
                color='#ef4444';
            }

            if(tasa==='TAI'){
                color='#10b981';
            }

            datasets.push({

                label:
                    `${tasa} ${period.period}`,

                data:
                    labels.map(
                        l=>row[l]
                    ),

                backgroundColor:
                    color,

                borderRadius:8
            });
        });

    });

    chart =
        new Chart(ctx,{

            type:'bar',

            data:{
                labels,
                datasets
            },

            options:{

                responsive:true,

                plugins:{
                    legend:{
                        position:'top'
                    }
                },

                scales:{
                    y:{
                        beginAtZero:true,
                        grid:{
                            color:'#eef2f7'
                        }
                    },
                    x:{
                        grid:{
                            display:false
                        }
                    }
                }
            }
        });
}