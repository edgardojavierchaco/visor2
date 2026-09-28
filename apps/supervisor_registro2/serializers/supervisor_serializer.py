def supervisor_to_dict(supervisor):
    return {
        "id": supervisor.id,
        "cuil": supervisor.usuario.username,
        "apellido": supervisor.usuario.apellido,
        "nombres": supervisor.usuario.nombres,
        "email": supervisor.email,
        "telefono": supervisor.telefono,
        "activo": supervisor.activo,
    }


def usuario_to_dict(usuario):
    return {
        "cuil": usuario.username,
        "apellido": usuario.apellido,
        "nombres": usuario.nombres,
        "correo": usuario.correo,
        "telefono": usuario.telefono,
    }