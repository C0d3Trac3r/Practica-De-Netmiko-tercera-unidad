#Jorge Oved Flores Lopez
import re
from netmiko import ConnectHandler

def find_device_and_neighbors(host, username, password, secret, mac_last4, visited_hosts=None, results=None, initial_host=None):
    if visited_hosts is None:
        visited_hosts = set()
    if results is None:
        results = []
    if initial_host is None:
        initial_host = host  # Guardar el primer host

    mac_last4 = mac_last4.lower().replace(":", "").replace("-", "").replace(".", "")
    # Configuración del switch
    switch = {
        "device_type": "cisco_ios",
        "host": host,
        "username": username,
        "password": password,
        "secret": secret,
    }

    try:
        print(f"\nConectando al switch {host}...")
        connection = ConnectHandler(**switch)
        connection.enable()
        visited_hosts.add(host)

        # Buscar MAC en la tabla
        print(f"Buscando MAC {mac_last4} en {host}...")
        mac_table = connection.send_command("show mac address-table")
        mac_found = False

        for line in mac_table.splitlines():
            if not line.strip() or line.startswith("Vlan"):
                continue
            columns = line.split()
            if len(columns) < 4:
                continue

            vlan, mac_full, mac_type, port = columns[:4]

            if mac_type.lower() == "static" or port.lower() == "cpu":
                continue

            #Puertos
            if mac_last4 in mac_full.replace(":", "").replace("-", "").replace(".", "").lower() and port.lower() not in ["fa1/0/47", "fa1/0/48"]:
                results.append((host, mac_full, vlan, port))
                mac_found = True

        # Obtener vecinos CDP
        print(f"\nObteniendo vecinos CDP de {host}...")
        cdp_output = connection.send_command("show cdp neighbors detail")
        neighbors = re.findall(
            r"Device ID: (.+?)\n.*?Management address\(es\):\s+IP address: (\d+\.\d+\.\d+\.\d+)",   
            cdp_output,
            re.DOTALL,
        )

        for neighbor, neighbor_ip in neighbors:
            if neighbor_ip not in visited_hosts:
                find_device_and_neighbors(neighbor_ip, username, password, secret, mac_last4, visited_hosts, results, initial_host)

        connection.disconnect()

        if not mac_found:
            print(f"\nMAC {mac_last4} no encontrada en {host}.")

    except Exception as e:
        print(f"Error al conectar o ejecutar comandos en el switch {host}: {e}")

    # Al final, imprimir solo la información del dispositivo encontrado
    if host == initial_host:  # Si es el switch inicial
        print("\n### Resultados finales ###")
        if results:
            # Mostrar únicamente la información de la MAC encontrada
            for result in results:
                print(f"MAC encontrada en {result[0]}:")
                print(f" - MAC: {result[1]}, VLAN: {result[2]}, Puerto: {result[3]}")
        else:
            print("No se encontró la MAC en toda la red explorada.")


# Solicitar datos al usuario
if __name__ == "__main__":
    print("Introduce los datos del switch inicial:")
    host = input("Dirección IP del switch: ").strip()
    username = input("Nombre de usuario: ").strip()
    password = input("Contraseña: ").strip()
    secret = input("Contraseña de modo enable: ").strip()

    mac_last4 = input("Ingresa los ultimos 4 dígitos de la MAC Address: ").strip()

    find_device_and_neighbors(host, username, password, secret, mac_last4)
