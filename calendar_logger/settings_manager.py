import keyring

SERVICE_NAME = "GeminiZohoCalendarApp"

def save_credentials(client_id, client_secret, refresh_token, api_domain, portal_id, email):
    """Saves Zoho credentials securely in the system's keyring."""
    keyring.set_password(SERVICE_NAME, "client_id", client_id)
    keyring.set_password(SERVICE_NAME, "client_secret", client_secret)
    keyring.set_password(SERVICE_NAME, "refresh_token", refresh_token)
    keyring.set_password(SERVICE_NAME, "api_domain", api_domain)
    keyring.set_password(SERVICE_NAME, "portal_id", portal_id)
    keyring.set_password(SERVICE_NAME, "email", email)
    print("Credenziali salvate con successo.")

def get_credentials():
    """Retrieves Zoho credentials from the system's keyring."""
    return {
        "client_id": keyring.get_password(SERVICE_NAME, "client_id"),
        "client_secret": keyring.get_password(SERVICE_NAME, "client_secret"),
        "refresh_token": keyring.get_password(SERVICE_NAME, "refresh_token"),
        "api_domain": keyring.get_password(SERVICE_NAME, "api_domain"),
        "portal_id": keyring.get_password(SERVICE_NAME, "portal_id"),
        "email": keyring.get_password(SERVICE_NAME, "email"),
    }

def save_access_token(access_token):
    """Saves the access token. For simplicity, we save it to the keyring as well."""
    keyring.set_password(SERVICE_NAME, "access_token", access_token)

def get_access_token():
    """Retrieves the access token."""
    return keyring.get_password(SERVICE_NAME, "access_token")

def save_calendar_hours(start_hour, end_hour):
    """Saves calendar start and end hours to the keyring."""
    keyring.set_password(SERVICE_NAME, "calendar_start_hour", str(start_hour))
    keyring.set_password(SERVICE_NAME, "calendar_end_hour", str(end_hour))

def get_calendar_hours():
    """Retrieves calendar hours, returning defaults if not set."""
    start = keyring.get_password(SERVICE_NAME, "calendar_start_hour")
    end = keyring.get_password(SERVICE_NAME, "calendar_end_hour")
    return {
        "start_hour": start if start else "8",
        "end_hour": end if end else "19",
    }
