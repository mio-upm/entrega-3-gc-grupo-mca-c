import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum

#Cargar los datos
ruta_costes = "241204_costes.xlsx"  
ruta_operaciones = "241204_datos_operaciones_programadas.xlsx"  

datos_costes = pd.ExcelFile(ruta_costes)  
datos_operaciones = pd.ExcelFile(ruta_operaciones)  

# Parsear las hojas en dataframes
costes = datos_costes.parse("costes", index_col=0)  
operaciones = datos_operaciones.parse("operaciones") 

#Filtrar operaciones
operaciones_cardiologia = operaciones[operaciones["Especialidad quirúrgica"] == "Cardiología Pediátrica"]
codigos_operaciones_cardiologia = operaciones_cardiologia["Código operación"].tolist()


costes_cardiologia = costes[codigos_operaciones_cardiologia]

# Eliminar quirófanos 
costes_cardiologia = costes_cardiologia.dropna(how='all', axis=0)

# Definir los conjuntos de operaciones y quirófanos
lista_operaciones = costes_cardiologia.columns.tolist()  
lista_quirofanos = costes_cardiologia.index.tolist()  

# Crear un diccionario con los costes de asignación de operaciones a quirófanos
diccionario_costes = {
    (quirofano, operacion): costes_cardiologia.at[quirofano, operacion]
    for quirofano in lista_quirofanos for operacion in lista_operaciones
}

# Problema de optimización

modelo1 = LpProblem("Minimizar_Costes_Cardiologia_Pediatrica", LpMinimize)


x = LpVariable.dicts("Asignar", ((quirofano, operacion) for quirofano in lista_quirofanos for operacion in lista_operaciones), cat='Binary')

modelo1 += lpSum(x[quirofano, operacion] * diccionario_costes[quirofano, operacion] for quirofano in lista_quirofanos for operacion in lista_operaciones)


for operacion in lista_operaciones:
    modelo1 += lpSum(x[quirofano, operacion] for quirofano in lista_quirofanos) == 1


modelo1.solve()  

asignaciones = {
    (quirofano, operacion): x[quirofano, operacion].varValue
    for quirofano in lista_quirofanos for operacion in lista_operaciones
    if x[quirofano, operacion].varValue > 0
}


# Crear un DataFrame para resumir las asignaciones óptimas y los costes asociados
resultados_df = pd.DataFrame(asignaciones.keys(), columns=["Quirófano", "Operación"])
resultados_df["Coste"] = resultados_df.apply(lambda row: diccionario_costes[(row["Quirófano"], row["Operación"])], axis=1)
coste_total = resultados_df["Coste"].sum()  # Calcular el coste total de la solución

# Guardar los resultados en un archivo Excel para uso posterior
resultados_df.to_excel("resultados_modelo1_cardiologia.xlsx", index=False)

# Imprimir resumen de los resultados
print(f"Optimización completa. Coste total: {coste_total}")
print("Resultados guardados en 'resultados_modelo1_cardiologia.xlsx'.")