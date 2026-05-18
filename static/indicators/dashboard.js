const nivel =
    document.getElementById('nivel');

const orientacionWrapper =
    document.getElementById(
        'orientacion-wrapper'
    );

const orientacionSelect =
    document.getElementById(
        'orientacion'
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


/* =====================================
   ORIENTACIONES
===================================== */

const ORIENTACIONES = {

    SECUNDARIA: [
        {
            value:'BACHILLER',
            text:'Bachiller'
        }
    ],

    TECNICA: [
        {
            value:'TECNICA',
            text:'Técnica'
        }
    ]
};


/* =====================================
   NIVEL
===================================== */

nivel.addEventListener(
    'change',
    ()=>{

        const opciones =
            ORIENTACIONES[
                nivel.value
            ];

        if(opciones){

            orientacionWrapper
                .style.display='block';

            orientacionSelect.innerHTML =
                '<option value="">Seleccione</option>';

            opciones.forEach(op=>{

                orientacionSelect.innerHTML += `
                    <option value="${op.value}">
                        ${op.text}
                    </option>
                `;
            });

        }else{

            orientacionWrapper
                .style.display='none';

            orientacionSelect.innerHTML =
                '<option value="">Seleccione</option>';
        }
    }
);


/* =====================================
   CONSULTA API
===================================== */

consultarBtn.addEventListener(
    'click',
    async ()=>{

        const cueanexo =
            document.getElementById(
                'cueanexo'
            ).value.trim();

        const nivelVal =
            nivel.value;

        const orientacion =
            orientacionSelect.value;

        if(!cueanexo || !nivelVal){

            results.innerHTML=`
                <div class="empty-state">
                    Complete CUEANEXO y Nivel
                </div>
            `;
            return;
        }

        let url =
            `/indica/indicators/?cueanexo=${cueanexo}&nivel=${nivelVal}`;

        if(
            nivelVal==='SECUNDARIA' ||
            nivelVal==='TECNICA'
        ){

            if(!orientacion){

                results.innerHTML=`
                    <div class="empty-state">
                        Seleccione orientación
                    </div>
                `;
                return;
            }

            url +=
                `&orientacion=${orientacion}`;
        }

        try{

            results.innerHTML=`
                <div class="panel">
                    Consultando...
                </div>
            `;

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


/* =====================================
   RENDER
===================================== */

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
        periods[0].indicators || [];

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

    results.innerHTML=
    `
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

    <div class="panel chart-panel">
        <canvas id="chart"></canvas>
    </div>

    <div class="panel">
        ${buildTables(periods)}
    </div>
    `;

    drawChart(periods);
}


/* =====================================
   PROMEDIO KPI
===================================== */

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
            ([k,v])=>Number(v)
        );

    return (
        vals.reduce(
            (a,b)=>a+b,
            0
        ) / vals.length
    );
}


/* =====================================
   TABLAS
===================================== */

function buildTables(periods){

    let html='';

    periods.forEach(period=>{

        if(
            !period.indicators ||
            period.indicators.length===0
        ){
            return;
        }

        html += `
            <h3 class="period-title">
                Periodo ${period.period}
            </h3>
        `;

        html += '<table>';

        const cols =
            Object.keys(
                period.indicators[0]
            );

        html += '<tr>';

        cols.forEach(c=>{

            html += `
                <th>${c}</th>
            `;
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


/* =====================================
   GRAFICO PRO
===================================== */

function drawChart(periods){

    const canvas =
        document.getElementById('chart');

    if(chart){
        chart.destroy();
    }

    const ctx =
        canvas.getContext('2d');

    const base =
        periods[0]
        ?.indicators
        ?.find(
            x=>x.tasa==='TPE'
        );

    if(!base){
        return;
    }

    const labels =
        Object.keys(base)
        .filter(
            k=>k!=='tasa'
        );

    const datasets=[];

    periods.forEach((period,index)=>{

        const tpe =
            period.indicators.find(
                x=>x.tasa==='TPE'
            );

        const tr =
            period.indicators.find(
                x=>x.tasa==='TR'
            );

        const tai =
            period.indicators.find(
                x=>x.tasa==='TAI'
            );

        /* TPE */

        datasets.push({

            type:'bar',

            label:
                `TPE ${period.period}`,

            data:
                labels.map(
                    l=>tpe[l]
                ),

            backgroundColor:
                index===0
                ? '#2563eb'
                : '#60a5fa',

            borderRadius:14,
            borderSkipped:false,

            categoryPercentage:.82,
            barPercentage:.95,

            maxBarThickness:42
        });

        /* TR */

        datasets.push({

            type:'bar',

            label:
                `TR ${period.period}`,

            data:
                labels.map(
                    l=>tr[l]
                ),

            backgroundColor:
                index===0
                ? '#dc2626'
                : '#f87171',

            borderRadius:14,
            borderSkipped:false,

            categoryPercentage:.82,
            barPercentage:.95,

            maxBarThickness:42
        });

        /* TAI */

        datasets.push({

            type:'line',

            label:
                `TAI ${period.period}`,

            data:
                labels.map(
                    l=>tai[l]
                ),

            borderColor:
                index===0
                ? '#059669'
                : '#34d399',

            backgroundColor:
                index===0
                ? '#059669'
                : '#34d399',

            tension:.35,

            borderWidth:4,

            pointRadius:6,
            pointHoverRadius:8,

            fill:false
        });

    });

    chart =
        new Chart(ctx,{

            data:{
                labels,
                datasets
            },

            options:{

                responsive:true,

                maintainAspectRatio:false,

                animation:{
                    duration:1000
                },

                layout:{
                    padding:{
                        top:25,
                        right:20,
                        bottom:10,
                        left:10
                    }
                },

                interaction:{
                    mode:'index',
                    intersect:false
                },

                plugins:{

                    legend:{
                        position:'top',
                        labels:{
                            usePointStyle:true,
                            pointStyle:'circle',
                            padding:22,
                            font:{
                                size:13,
                                weight:'600'
                            }
                        }
                    },

                    tooltip:{
                        backgroundColor:'#111827',
                        padding:14,
                        cornerRadius:12
                    }
                },

                scales:{

                    y:{

                        beginAtZero:false,

                        suggestedMin:-10,
                        suggestedMax:130,

                        grid:{
                            color:'#e5e7eb'
                        },

                        ticks:{
                            font:{
                                size:12
                            }
                        },

                        title:{
                            display:true,
                            text:'Porcentaje'
                        }
                    },

                    x:{

                        grid:{
                            display:false
                        },

                        ticks:{
                            padding:10,
                            font:{
                                size:12,
                                weight:'600'
                            }
                        },

                        title:{
                            display:true,
                            text:'Grados / Años'
                        }
                    }
                }
            }
        });
}