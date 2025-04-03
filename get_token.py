import json

def get_aem_token():
    try:
        with open('local_development_token.json', 'r') as f:
            data = json.load(f)
            return data.get('accessToken')
    except Exception as e:
        print(f"Error reading token: {e}")
        return None

if __name__ == "__main__":
    token = get_aem_token()
    if token:
        print(f"export AEM_TOKEN='{token}'") 