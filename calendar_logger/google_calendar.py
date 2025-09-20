from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

CRED_PATH = Path(__file__).parent / 'credentials.json'
TOKEN_PATH = Path(__file__).parent / 'token.json'

def get_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CRED_PATH), SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_events(max_results=50):
    service = get_service()
    now = datetime.utcnow().isoformat() + 'Z'  # adesso in UTC
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])


def get_events_for_week(week_start, week_end, max_results=50):
    """
    Recupera eventi Google tra week_start e week_end
    week_start e week_end devono essere datetime
    """
    service = get_service()
    time_min = week_start.isoformat() + 'Z'
    time_max = week_end.isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])
