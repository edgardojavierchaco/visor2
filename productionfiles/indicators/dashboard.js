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

    const p2023 =
        periods.find(
            p=>p.period==='2023_2024'
        );

    const p2024 =
        periods.find(
            p=>p.period==='2024_2025'
        );

    const tpe23 =
        p2023?.indicators.find(
            x=>x.tasa==='TPE'
        );

    const tpe24 =
        p2024?.indicators.find(
            x=>x.tasa==='TPE'
        );

    const tr23 =
        p2023?.indicators.find(
            x=>x.tasa==='TR'
        );

    const tr24 =
        p2024?.indicators.find(
            x=>x.tasa==='TR'
        );

    const tai23 =
        p2023?.indicators.find(
            x=>x.tasa==='TAI'
        );

    const tai24 =
        p2024?.indicators.find(
            x=>x.tasa==='TAI'
        );

    results.innerHTML=
    `
    <div class="cards-grid">

        <!-- TPE -->

        <div class="kpi-card tpe">

            <div class="kpi-title">
                TPE
            </div>

            <div class="kpi-period">
                2023_2024
            </div>

            <div class="kpi-value">
                ${avg(tpe23).toFixed(1)}%
            </div>

            <div class="kpi-period second">
                2024_2025
            </div>

            <div class="kpi-value small">
                ${avg(tpe24).toFixed(1)}%
            </div>

        </div>


        <!-- TR -->

        <div class="kpi-card tr">

            <div class="kpi-title">
                TR
            </div>

            <div class="kpi-period">
                2023_2024
            </div>

            <div class="kpi-value">
                ${avg(tr23).toFixed(1)}%
            </div>

            <div class="kpi-period second">
                2024_2025
            </div>

            <div class="kpi-value small">
                ${avg(tr24).toFixed(1)}%
            </div>

        </div>


        <!-- TAI -->

        <div class="kpi-card tai">

            <div class="kpi-title">
                TAI
            </div>

            <div class="kpi-period">
                2023_2024
            </div>

            <div class="kpi-value">
                ${avg(tai23).toFixed(1)}%
            </div>

            <div class="kpi-period second">
                2024_2025
            </div>

            <div class="kpi-value small">
                ${avg(tai24).toFixed(1)}%
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
                    l=>Number(tpe[l])
                ),

            backgroundColor:
                index===0
                ? '#2563eb'
                : '#60a5fa',

            borderRadius:0,
            borderSkipped:false,

            categoryPercentage:.70,
            barPercentage:.90,

            maxBarThickness:50
        });


        /* TR */

        datasets.push({

            type:'bar',

            label:
                `TR ${period.period}`,

            data:
                labels.map(
                    l=>Number(tr[l])
                ),

            backgroundColor:
                index===0
                ? '#dc2626'
                : '#f87171',

            borderRadius:0,
            borderSkipped:false,

            categoryPercentage:.70,
            barPercentage:.90,

            maxBarThickness:50
        });


        /* TAI */

        datasets.push({

            type:'bar',

            label:
                `TAI ${period.period}`,

            data:
                labels.map(
                    l=>Number(tai[l])
                ),

            backgroundColor:
                index===0
                ? '#059669'
                : '#34d399',

            borderRadius:0,
            borderSkipped:false,

            categoryPercentage:.70,
            barPercentage:.90,

            maxBarThickness:50
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
                maintainAspectRatio:false,

                animation:{
                    duration:1100,
                    easing:'easeOutQuart'
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
                            pointStyle:'rect',
                            padding:18,

                            font:{
                                size:13,
                                weight:'600'
                            }
                        }
                    },

                    tooltip:{
                        backgroundColor:'#111827',
                        padding:14,
                        cornerRadius:6
                    }
                },

                scales:{

                    y:{

                        beginAtZero:false,

                        suggestedMin:-15,
                        suggestedMax:130,

                        grid:{
                            color:'#e5e7eb'
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