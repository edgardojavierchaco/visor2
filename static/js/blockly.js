    // Crear bloques personalizados de Blockly para generar consultas SQL
Blockly.defineBlocksWithJsonArray([
    {
        "type": "sql_select",
        "message0": "SELECT %1 FROM %2",
        "args0": [
            {
                "type": "field_input",
                "name": "COLUMNS",
                "text": "*"
            },
            {
                "type": "field_input",
                "name": "TABLE",
                "text": "tabla"
            }
        ],
        "output": null,
        "colour": 160,
        "tooltip": "Genera una consulta SQL SELECT",
        "helpUrl": ""
    }
]);

// Configurar la zona de trabajo de Blockly
var workspace = Blockly.inject('blocklyDiv', {
    toolbox: `
        <xml>
            <block type="sql_select"></block>
        </xml>
    `
});

// Función para generar el código SQL
document.getElementById("generateSqlBtn").addEventListener("click", function() {
    // Generar el código de bloques en formato texto (JavaScript)
    var code = Blockly.JavaScript.workspaceToCode(workspace);

    // Convertirlo en una consulta SQL
    // En este caso, generaremos directamente el código SQL con base en los valores de los bloques
    var sqlQuery = code.replace("SELECT ", "SELECT ")
                        .replace(" FROM ", " FROM ");

    // Mostrar el SQL generado
    document.getElementById("generatedSql").value = sqlQuery;
});
