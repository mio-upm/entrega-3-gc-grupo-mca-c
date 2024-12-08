import pulp
import pandas as pd

# Cargar datos

datos_costes = pd.read_excel("241204_costes.xlsx", sheet_name="costes")
datos_operaciones = pd.read_excel("241204_datos_operaciones_programadas.xlsx")

# Limpiar nombres de columnas
datos_operaciones.columns = datos_operaciones.columns.str.strip()

# Filtrar operaciones por especialidades solicitadas
servicios_indicados = [
    "Cardiología Pediátrica",
    "Cirugía Cardíaca Pediátrica",
    "Cirugía Cardiovascular",
    "Cirugía General y del Aparato Digestivo"
]

operaciones_filtradas = datos_operaciones[
    datos_operaciones["Especialidad quirúrgica"].isin(servicios_indicados)
]

# Transformar el archivo de costes a un formato largo
datos_costes.rename(columns={'Unnamed: 0': 'Quirófano'}, inplace=True)
datos_costes_largo = datos_costes.melt(id_vars=['Quirófano'], var_name='Código operación', value_name='Coste')

# Extraer operaciones y duraciones del archivo de operaciones
operaciones = datos_operaciones['Código operación'].tolist()
duraciones = datos_operaciones[['Hora inicio', 'Hora fin']].values

# Generar planificaciones iniciales
def generar_planificaciones_eficientes(operaciones, duraciones):
    """
    Genera planificaciones iniciales agrupando operaciones que no solapen.
    """
    planificaciones = []
    operaciones_pendientes = list(range(len(operaciones)))

    while operaciones_pendientes:
        planificacion_actual = []
        for i in operaciones_pendientes[:]:
            if all(duraciones[i][1] <= duraciones[j][0] or duraciones[i][0] >= duraciones[j][1] for j in planificacion_actual):
                planificacion_actual.append(i)
                operaciones_pendientes.remove(i)
        planificaciones.append(planificacion_actual)

    return planificaciones

planificaciones_iniciales = generar_planificaciones_eficientes(operaciones, duraciones)

# Definir la función de factibilidad
def es_factible(planificacion, duraciones):
    """
    Verifica si una planificación es factible (sin solapamientos).
    """
    for i in range(len(planificacion)):
        for j in range(i + 1, len(planificacion)):
            op1, op2 = planificacion[i], planificacion[j]
            if not (duraciones[op1][1] <= duraciones[op2][0] or duraciones[op1][0] >= duraciones[op2][1]):
                return False
    return True

# Modelo maestro
def modelo_maestro(planificaciones):
    """
    Crea y resuelve el modelo maestro restringido.
    """
    modelo = pulp.LpProblem("Modelo_Maestro", pulp.LpMinimize)

    
    y = pulp.LpVariable.dicts("y", range(len(planificaciones)), cat='Binary')

    
    modelo += pulp.lpSum(y[k] for k in range(len(planificaciones)))

    
    for i, operacion in enumerate(operaciones):
        modelo += pulp.lpSum(y[k] for k in range(len(planificaciones)) if i in planificaciones[k]) >= 1, f"Restriccion_{i}"

    
    modelo.solve()
    return modelo, y

# Generación de columnas
def generar_columnas(precios_duales, operaciones, duraciones):
    """
    Genera nuevas columnas basadas en precios duales y factibilidad.
    """
    nuevas_planificaciones = []
    for i in range(len(operaciones)):
        planificacion = [i]
        if es_factible(planificacion, duraciones):
            coste_reducido = -sum(precios_duales.get(i, 0) for i in planificacion)
            if coste_reducido < -1e-6:  # Si mejora el modelo
                nuevas_planificaciones.append(planificacion)
    return nuevas_planificaciones

# Algoritmo de generación de columnas
def algoritmo_generacion_columnas():
    """
    Implementa el algoritmo de generación de columnas.
    """
    planificaciones = planificaciones_iniciales
    iteracion = 0

    while True:
        print(f"Iteración {iteracion}: Resolviendo modelo maestro...")
        modelo, y = modelo_maestro(planificaciones)

        
        precios_duales = {i: modelo.constraints[f"Restriccion_{i}"].pi for i in range(len(operaciones))}

        
        nuevas_columnas = generar_columnas(precios_duales, operaciones, duraciones)

        if not nuevas_columnas:  
            break

        # Agregar nuevas columnas al conjunto de planificaciones
        planificaciones.extend(nuevas_columnas)
        iteracion += 1

    return modelo, planificaciones


modelo_final, planificaciones_finales = algoritmo_generacion_columnas()

# Resultados finales
numero_quirofanos = pulp.value(modelo_final.objective)
print(f"Número mínimo de quirófanos necesarios: {numero_quirofanos}")
