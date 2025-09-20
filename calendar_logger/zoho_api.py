import requests
from calendar_logger import settings_manager
from concurrent.futures import ThreadPoolExecutor
import time

# --- CACHE IN MEMORIA ---
_cache = {
    "projects": {},
    "tasks": {},
    "users": None,
    "access_token": None,
    "token_expiry": 0
}

# --- LOGGING ---


def log_debug(msg):
    # Attiva/disattiva debug facilmente
    print(f"[DEBUG] {msg}")

# --- TOKEN MANAGEMENT ---


def get_access_token():
    """Restituisce il token valido, rinfrescandolo se necessario."""
    now = time.time()
    if _cache["access_token"] and _cache["token_expiry"] > now:
        return _cache["access_token"]
    token = refresh_access_token()
    return token


def refresh_access_token():
    log_debug("Tentativo di refresh del token...")
    creds = settings_manager.get_credentials()
    if not all([creds.get("refresh_token"), creds.get("client_id"), creds.get("client_secret")]):
        log_debug("Credenziali incomplete.")
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
        access_token = token_data.get("access_token")
        if access_token:
            _cache["access_token"] = access_token
            _cache["token_expiry"] = time.time(
            ) + token_data.get("expires_in", 3600) - 60
            settings_manager.save_access_token(access_token)
            log_debug(f"Nuovo access token salvato: {access_token}")
            return access_token
    except requests.exceptions.RequestException as e:
        log_debug(f"Errore refresh token: {e}")
        return None

# --- API CALL ---


def _make_api_call(method, api_url, json_payload=None):
    token = get_access_token()
    if not token:
        return None, "Impossibile ottenere un access token valido."

    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    try:
        if method.upper() == 'GET':
            response = requests.get(api_url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(
                api_url, headers=headers, json=json_payload)
        else:
            return None, f"Metodo {method} non supportato"

        if response.status_code == 401:
            # Token scaduto, refresh
            token = refresh_access_token()
            if not token:
                return None, "Rinnovo token fallito"
            headers = {"Authorization": f"Zoho-oauthtoken {token}"}
            if method.upper() == 'GET':
                response = requests.get(api_url, headers=headers)
            else:
                response = requests.post(
                    api_url, headers=headers, json=json_payload)

        response.raise_for_status()
        return response.json(), None

    except requests.exceptions.RequestException as e:
        return None, str(e)

# --- PROGETTI ---


def get_projects(portal_id: str):
    if portal_id in _cache["projects"]:
        return _cache["projects"][portal_id], None

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
        if error:
            return None, error
        if not data:
            break

        all_projects.extend(data)
        if len(data) < per_page:
            break
        page += 1

    valid_statuses = ["In corso", "In sospeso", "In entrata", "Fase Finale"]
    filtered_projects = [p for p in all_projects if p.get(
        "status", {}).get("name") in valid_statuses]

    _cache["projects"][portal_id] = filtered_projects
    return filtered_projects, None

# --- TASKS ---


def get_tasks(portal_id, project_id):
    
    user_email = settings_manager.get_credentials().get("email")
    if (portal_id, project_id) in _cache["tasks"]:
        return _cache["tasks"][(portal_id, project_id)], None

    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain:
        return None, "Dominio API non impostato."

    api_url = f"{api_domain}/api/v3/portal/{portal_id}/projects/{project_id}/tasks"
    data, error = _make_api_call('GET', api_url)
    if error:
        return None, error

    tasks = data.get('tasks', []) if data else []
    print(f"Recuperati {len(tasks)} tasks per il progetto {project_id}")
    filtered_tasks = []
    for task in tasks:
        owners_and_work = task.get("owners_and_work", {})
        owners = owners_and_work.get("owners", [])
        # Controlla se zpuid è tra gli owners
        if any(owner.get("email") == user_email for owner in owners):
            filtered_tasks.append(task)
    print(filtered_tasks)
    _cache["tasks"][(portal_id, project_id)] = filtered_tasks
    return filtered_tasks, None

# --- GET ALL TASKS PARALLEL ---


def get_all_tasks_parallel(portal_id, projects):
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(
            get_tasks, portal_id, p['id']): p['id'] for p in projects}
        for future in future_map:
            project_id = future_map[future]
            tasks, error = future.result()
            results[project_id] = tasks
    return results

# --- UTENTI ---


def get_all_users(portal_id: str):
    if _cache["users"] is not None:
        return _cache["users"], None

    creds = settings_manager.get_credentials()
    api_domain = creds.get("api_domain")
    if not api_domain:
        return None, "Dominio API non impostato."

    all_users = []
    page = 1
    per_page = 100

    while True:
        api_url = f"{api_domain}/api/v3/portal/{portal_id}/users?page={page}&per_page={per_page}"
        data, error = _make_api_call("GET", api_url)
        if error:
            return None, error

        users_batch = data.get("users", [])
        if not users_batch:
            break

        all_users.extend(users_batch)
        if len(users_batch) < per_page:
            break
        page += 1

    _cache["users"] = all_users
    return all_users, None


def get_user_by_email(portal_id, email):
    users, error = get_all_users(portal_id)
    if error:
        return None, error
    for user in users:
        if user.get('email') == email:
            return user, None
    return None, "Email utente non trovata nel portale Zoho."

# --- LOG TIME ---


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
        "module": {"id": task_id, "type": "task"}
    }

    data, error = _make_api_call('POST', api_url, json_payload=payload)
    if error:
        return {"success": False, "message": error}
    return {"success": True, "message": "Tempo loggato con successo su Zoho."}
