import argparse

def calcular_cuil(dni, sexo):
    dni = str(dni).zfill(8)  # Asegurar que tenga 8 dígitos

    # Determinar prefijo según el sexo
    if sexo.upper() == "M":
        prefijo = "20"
    elif sexo.upper() == "F":
        prefijo = "27"
    else:
        raise ValueError("Sexo inválido. Usa 'M' o 'F'.")

    base = f"{prefijo}{dni}"

    # Coeficientes del módulo 11
    coeficientes = [5,4,3,2,7,6,5,4,3,2]

    # Calcular el dígito verificador
    suma = sum(int(base[i]) * coeficientes[i] for i in range(10))
    resto = suma % 11
    digito_verificador = 11 - resto

    # Ajustes para casos especiales
    if digito_verificador == 10:
        prefijo = "23"  # Se usa 23 si el verificador es 10
        base = f"{prefijo}{dni}"
        suma = sum(int(base[i]) * coeficientes[i] for i in range(9))
        resto = suma % 11
        digito_verificador = 11 - resto
    elif digito_verificador == 11:
        digito_verificador = 0

    return f"{prefijo}-{dni}-{digito_verificador}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar CUIL a partir de DNI y sexo.")
    parser.add_argument("dni", type=int, help="Número de DNI sin puntos")
    parser.add_argument("sexo", type=str, choices=["M", "F"], help="Sexo: M (Masculino) o F (Femenino)")
    
    args = parser.parse_args()
    cuil = calcular_cuil(args.dni, args.sexo)
    print(f"CUIL generado: {cuil}")

