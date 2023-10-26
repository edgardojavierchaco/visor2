from itertools import permutations

# Definir los elementos
elementos = ['A', 'B', 'C']

# Generar todas las permutaciones posibles de longitud 9
permutaciones = list(permutations(elementos, 3))

# Imprimir todas las permutaciones
for p in permutaciones:
    print(' '.join(p))
