import json



def proxyToList():
    FILE_PATH ="./WebScraping/JSON/proxy_list.json"
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as file:
            elements = json.load(file)
            proxy_list= [item["proxy"] for item in elements]
        print(f"Letti {len(proxy_list)} proxy dal file")
        return proxy_list

    except FileNotFoundError:
        print(f"File {FILE_PATH} non trovato")
        return []
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing del JSON: {str(e)}")
        return []
    except Exception as e:
        print(f"Errore generico: {str(e)}")
        return []



#debug
proxy_list = proxyToList()


# Formattazione in dizionari con chiave "http"
proxy_dict_list = [{"http": proxy} for proxy in proxy_list]

# Nome del file JSON
file_name = "WebScraping/JSON/proxies.json"

# Scrittura nel file JSON
with open(file_name, 'w') as file:
    json.dump(proxy_dict_list, file, indent=4)

print(f"Proxy salvati in {file_name}")
#print(list(proxies))