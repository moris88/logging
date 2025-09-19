import requests
from calendar_logger import settings_manager

def _make_api_call(method, api_url, json_payload=None):
    """Helper function to make an authenticated API call with token refresh logic."""
    access_token = settings_manager.get_access_token()
    if not access_token:
        access_token = refresh_access_token()
        if not access_token:
            return None, "Impossibile ottenere un access token valido."

    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

    def do_request(token):
        updated_headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        if method.upper() == 'GET':
            return requests.get(api_url, headers=updated_headers)
        elif method.upper() == 'POST':
            return requests.post(api_url, headers=updated_headers, json=json_payload)

    try:
        response = do_request(access_token)

        if response.status_code == 401:
            new_token = refresh_access_token()
            if new_token:
                response = do_request(new_token)
            else:
                return None, "Rinnovo del token fallito."

        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as e:
        return None, f"Errore API Zoho: {e.response.status_code} - {e.response.text}"
    except requests.exceptions.RequestException as e:
        return None, f"Errore di rete: {e}"

def refresh_access_token():
    """
    Uses the refresh token to get a new access token from Zoho.
    """
    creds = settings_manager.get_credentials()
    if not all([creds["refresh_token"], creds["client_id"], creds["client_secret"]]):
        return None

    token_url = f"https://accounts.zoho.eu/oauth/v2/token"
    params = {
        "refresh_token": creds["refresh_token"],
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "grant_type": "refresh_token",
    }

    try:
        response = requests.post(token_url, params=params)
        response.raise_for_status()
        token_data = response.json()
        if "access_token" in token_data:
            new_access_token = token_data["access_token"]
            settings_manager.save_access_token(new_access_token)
            return new_access_token
        return None
    except requests.exceptions.RequestException:
        return None

def get_projects(portal_id):
    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain: return None, "Dominio API non impostato."

    api_url = f"{api_domain}/restapi/portal/{portal_id}/projects/"
    data, error = _make_api_call('GET', api_url)
    return (data.get('projects', []), error) if data else (None, error)


def get_tasks(portal_id, project_id):
    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain: return None, "Dominio API non impostato."

    api_url = f"{api_domain}/restapi/portal/{portal_id}/projects/{project_id}/tasks/"
    data, error = _make_api_call('GET', api_url)
    return (data.get('tasks', []), error) if data else (None, error)

def log_time_to_zoho(portal_id, project_id, task_id, event_name, hours, notes, log_date):
    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain: return {"success": False, "message": "Dominio API non impostato."}

    api_url = f"{api_domain}/restapi/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/logs/"
    payload = {
        "name": event_name,
        "notes": notes,
        "log_date": log_date,
        "hours": str(round(hours, 2))
    }

    data, error = _make_api_call('POST', api_url, json_payload=payload)

    if error:
        return {"success": False, "message": error}
    
    print("Risposta da Zoho Projects API:", data)
    return {"success": True, "message": "Tempo loggato con successo su Zoho."}
