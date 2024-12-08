import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum

datos_costes = pd.read_excel("241204_costes.xlsx", sheet_name="costes")
datos_operaciones = pd.read_excel("241204_datos_operaciones_programadas.xlsx")

# Limpiar nombres de columnas
datos_operaciones.columns = datos_operaciones.columns.str.strip()

# Seleccionamos operaciones
servicios_indicados = [
    "Cardiología Pediátrica",
    "Cirugía Cardíaca Pediátrica",
    "Cirugía Cardiovascular",
    "Cirugía General y del Aparato Digestivo"
]

operaciones_filtradas = datos_operaciones[
    datos_operaciones["Especialidad quirúrgica"].isin(servicios_indicados)
]

# pasar a datetime las fechas
operaciones_filtradas.loc[:, "Hora inicio"] = pd.to_datetime(operaciones_filtradas["Hora inicio"])
operaciones_filtradas.loc[:, "Hora fin"] = pd.to_datetime(operaciones_filtradas["Hora fin"])


#funcion de planificaciones
def generar_planes_optimizados(operaciones):
    """Genera un conjunto reducido de planificaciones factibles optimizando el uso del tiempo."""
    operaciones_ordenadas = operaciones.sort_values(by="Hora inicio").to_dict(orient="records")
    planes_factibles = []

    while operaciones_ordenadas:
        plan = []
        hora_fin_actual = pd.Timestamp.min

        # Construir una planificación seleccionando operaciones compatibles
        for op in list(operaciones_ordenadas):  # Usamos lista para modificar la lista original
            if op["Hora inicio"] >= hora_fin_actual:
                plan.append(op)
                hora_fin_actual = op["Hora fin"]
                operaciones_ordenadas.remove(op)  # Eliminar operación ya planificada

        planes_factibles.append(plan)

    return planes_factibles

# generamos planificaciones optimizadas
planes_optimizados = generar_planes_optimizados(operaciones_filtradas)

# pasamos a diccionario
matriz_costes = datos_costes.set_index("Unnamed: 0").to_dict(orient="index")


# matriz para operaciones y planificaciones
lista_operaciones = operaciones_filtradas["Código operación"].unique()
B_ik = {op: [] for op in lista_operaciones}
for plan_idx, plan in enumerate(planes_optimizados):
    for operacion in plan:
        B_ik[operacion["Código operación"]].append(plan_idx)

        
costes_medios = {
    op: sum(matriz_costes[nombre_quir][op] for nombre_quir in matriz_costes) / len(matriz_costes)
    for op in lista_operaciones
}
        

#coste de una planificacion 
def calcular_coste_plan(B_ik, plan_idx, costes_medios):
    """Calcula el costo total del plan k basado en B_ik y los costos promedio."""
    coste_plan = 0
    for op in B_ik:  # Recorremos todas las operaciones
        if plan_idx in B_ik[op]:  # Solo consideramos las operaciones cubiertas por este plan
            coste_plan += costes_medios[op]  # Usamos el costo promedio de la operación
    return coste_plan


#costes de las planificaciones
costes_plan_optimizados = [calcular_coste_plan(B_ik, plan_idx, costes_medios) for plan_idx in range(len(planes_optimizados))]


#creamos el modelo
model = LpProblem("Set_Covering_Optimized_Plans", LpMinimize)

y_var = [LpVariable(f"Plan_{k}", cat="Binary") for k in range(len(planes_optimizados))]

# Función objetivo
model += lpSum(y_var[k] * calcular_coste_plan(B_ik, k, costes_medios) for k in range(len(planes_optimizados)))

# Restricciones
for op, covering_plans in B_ik.items():
    model += lpSum(y_var[k] for k in covering_plans) >= 1, f"Cover_{op}"

model.solve()

#Resultados
planes_seleccionados = [k for k in range(len(y_var)) if y_var[k].varValue == 1]
costes_planes_seleccionados = [(k, costes_plan_optimizados[k]) for k in planes_seleccionados]

num_quirofanos = sum(1 for yVar in y_var if yVar.varValue == 1)
print(f"Total quirófanos utilizados: {num_quirofanos}")

print("Planes seleccionados:", planes_seleccionados)

for plan_idx in planes_seleccionados:
    print(f"Plan {plan_idx}:")
    for operacion in planes_optimizados[plan_idx]:
        print(f"  - {operacion['Código operación']}")
        

