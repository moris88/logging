import requests
from calendar_logger import settings_manager

def _make_api_call(method, api_url, json_payload=None):
    """Helper function to make an authenticated API call with token refresh logic."""
    access_token = settings_manager.get_access_token()
    if not access_token:
        access_token = refresh_access_token()
        if not access_token:
            return None, "Impossibile ottenere un access token valido."

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

    token_url = "https://accounts.zoho.com/oauth/v2/token"
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


def get_projects(portal_id: str):
    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain:
        return None, "Dominio API non impostato."

    all_projects = []
    page = 1
    per_page = 100

    while True:
        api_url = f"{api_domain}/api/v3/portal/{portal_id}/projects?page={page}&per_page={per_page}"
        data, error = _make_api_call("GET", api_url)
        print(f"Response error: {error}")  # Debug log

        if error:
            return None, error

        projects_batch = data
        if not projects_batch:
            break

        all_projects.extend(projects_batch)

        # Se meno di per_page progetti, significa che non ci sono altre pagine
        if len(projects_batch) < per_page:
            break

        page += 1  # Passa alla pagina successiva

    valid_statuses = ["In corso", "In sospeso", "In entrata", "Fase Finale"]
    filtered_projects = [
        p for p in all_projects
        if p.get("status", {}).get("name") in valid_statuses
    ]

    return filtered_projects, None

def get_tasks(portal_id, project_id):
    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain:
        return None, "Dominio API non impostato."

    api_url = f"{api_domain}/api/v3/portal/{portal_id}/projects/{project_id}/tasks"
    data, error = _make_api_call('GET', api_url)
    return (data.get('tasks', []), error) if data else (None, error)

def log_time_to_zoho(portal_id, project_id, task_id, event_name, notes, log_date, start_time, end_time, bill_status, owner_zpuid):
    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain:
        return {"success": False, "message": "Dominio API non impostato."}

    api_url = f"{api_domain}/api/v3/portal/{portal_id}/projects/{project_id}/log"
    payload = {
        "name": event_name,
        "notes": notes,
        "date": log_date,
        "start_time": start_time,
        "end_time": end_time,
        "bill_status": bill_status,
        "owner_zpuid": owner_zpuid,
        "module": {
            "id": task_id,
            "type": "task"
        }
    }

    data, error = _make_api_call('POST', api_url, json_payload=payload)

    if error:
        return {"success": False, "message": error}
    
    return {"success": True, "message": "Tempo loggato con successo su Zoho."}


def get_all_users(portal_id: str):
    """Fetches all users from a portal, handling pagination."""
    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain:
        return None, "Dominio API non impostato."

    all_users = []
    page = 1
    per_page = 100

    while True:
        api_url = f"{api_domain}/api/v3/portal/{portal_id}/users?page={page}&per_page={per_page}"
        print(f"Fetching users from: {api_url}")  # Debug log
        data, error = _make_api_call("GET", api_url)

        print(f"Response error: {error}")  # Debug log
        if error:
            return None, error

        users_batch = data.get("users", [])
        if not users_batch:
            break

        all_users.extend(users_batch)

        # Se meno utenti del massimo -> non ci sono altre pagine
        if len(users_batch) < per_page:
            break

        page += 1  # ✅ incremento corretto

    return all_users, None


def get_user_by_email(portal_id, email):
    """Finds a user by email and returns their object."""
    if not email:
        return None, "Email non configurata."
    users, error = get_all_users(portal_id)
    if error:
        return None, error
    for user in users:
        if user.get('email') == email:
            return user, None
    return None, "Email utente non trovata nel portale Zoho."
