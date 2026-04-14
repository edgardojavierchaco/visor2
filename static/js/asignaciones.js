function cambiarEstado(id, estado) {

    fetch(`/asignaciones/${id}/estado/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: "estado=" + estado
    })
    .then(r => r.json())
    .then(data => {

        if (data.ok) {
            document.getElementById(`estado-${id}`).innerText = data.estado;
        } else {
            alert(data.error);
        }
    });
}