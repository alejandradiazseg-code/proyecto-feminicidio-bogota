import os

def main():
    print("====================================")
    print(" ETL 07: Condiciones Territoriales")
    print("====================================")
    print("El Índice de Seguridad Nocturna no se encuentra publicado como un dataset")
    print("público descargable vía CKAN en Datos Abiertos Bogotá ni en un formato M2M")
    print("directo desde el servicio ESRI REST de Catastro de manera aisable as GeoJSON.")
    print("\nLa tabla 'condiciones_territoriales' se mantendrá vacía en la base de datos")
    print("hasta que la SDI o IDECA provean el acceso directo o API.")
    print("La carga se detiene sin arrojar error para mantener el pipeline limpio.")
    pass

if __name__ == "__main__":
    main()
