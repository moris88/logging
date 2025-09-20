# Calendar Logger with Zoho and Google Calendar Integration

This Python desktop application provides a calendar interface to create and manage events, with a specific feature to log time spent on Zoho Projects. It also syncs with your Google Calendar to display your events.

## Table of Contents

1. [Features](#features)
2. [Technologies Used](#technologies-used)
3. [Project Structure](#project-structure)
4. [Key Logic Implemented](#key-logic-implemented)
    * [Calendar Rendering](#calendar-rendering)
    * [Zoho API and Authentication Management](#zoho-api-and-authentication-management)
    * [Google Calendar Integration](#google-calendar-integration)
    * [Secure Credential Storage](#secure-credential-storage)
5. [Installation and Startup](#installation-and-startup)
6. [Initial Configuration](#initial-configuration)
7. [Automated Build and Release](#automated-build-and-release)
8. [Possible Future Improvements](#possible-future-improvements)

---

## Features

* **Calendar View**: Displays a weekly grid from Monday to Friday, with configurable time slots.
* **Complete CRUD for Events**: You can Create, Read, Modify, and Delete events.
* **Local Persistence**: All events are saved in a local SQLite database (`events.db`), ensuring that data is not lost between sessions.
* **Integration with Zoho Projects**: For completed events, you can log time directly to Zoho Projects through a dedicated form.
* **Google Calendar Sync**: Automatically fetches and displays events from your primary Google Calendar.
* **Immutability of Logged Events**: Once an event is logged to Zoho, it is locked and can no longer be modified or deleted.
* **Settings Panel**: A dedicated window to securely enter and save Zoho and Google API credentials.
* **Secure Credential Management**: API keys are not stored in plain text but are entrusted to the operating system's credential manager.

---

## Technologies Used

* **Python 3**: Main programming language.
* **CustomTkinter**: Library chosen for the GUI. It offers modern widgets and a more pleasing appearance than standard Tkinter.
* **SQLite 3**: Database engine. SQLite was chosen because it is integrated into Python and is perfect for single-user desktop applications.
* **Requests**: De-facto standard library for making HTTP calls, used for all communications with the Zoho APIs.
* **Keyring**: A fundamental library for security. It interfaces with the native credential manager of the operating system (e.g., Windows Credential Manager, macOS Keychain) to save and retrieve sensitive data.
* **Google API Client Library for Python**: Used to interact with the Google Calendar API.
* **PyInstaller**: To create the application executable.

---

## Project Structure

The code is organized in a package structure to improve maintainability and clarity.

* `main.py`: (Root) The application's entry point.
* `calendar_logger/`: (Package) Contains all the application's source code.
  * `__init__.py`: Makes the folder a Python package.
  * `app.py`: The heart of the application, manages the GUI and main logic.
  * `database.py`: Manages data persistence on SQLite.
  * `settings_manager.py`: Manages the secure saving and loading of credentials.
  * `zoho_api.py`: Contains all the logic for communicating with the Zoho APIs.
  * `google_calendar.py`: Handles integration with the Google Calendar API.
* `scripts/`: Contains accessory scripts.
  * `build.py`: Script to create the application executable via PyInstaller.
* `.github/workflows/`: Contains the CI/CD pipeline.
  * `release.yml`: A GitHub Actions workflow that automatically builds and releases executables for Linux, macOS, and Windows when a new tag is pushed.
* `requirements.txt`: Lists the Python dependencies.
* `.gitignore`: Specifies the files to be ignored in version control.

---

## Key Logic Implemented

### Calendar Rendering

The display of events is handled in the `refresh_events()` method in `app.py`. The logic is as follows:

1. **Cleanup**: All previously drawn event widgets are destroyed to avoid duplicates.
2. **Fetch**: All events are retrieved from the local database and Google Calendar.
3. **Iteration and Drawing**: For each event, its position in the grid (row and column) is calculated based on date and time.

### Zoho API and Authentication Management

The logic resides in `zoho_api.py` and follows the OAuth 2.0 flow with Refresh Token.

1. **Token Refresh**: The `refresh_access_token()` function is responsible for requesting a new `access_token` from Zoho.
2. **API Call with Automatic Retry**: The `log_time_to_zoho()` function is robust: it automatically retries the API call with a new token if the current one is expired.

### Google Calendar Integration

The `google_calendar.py` module handles the connection to the Google Calendar API.

1. **OAuth 2.0 Authentication**: On the first run, it guides the user through an authentication process to grant the application read-only access to their calendar.
2. **Token Storage**: The obtained credentials are securely stored in a `token.json` file for subsequent sessions.
3. **Event Fetching**: The `get_events_for_week` function retrieves all events for the displayed week.

### Secure Credential Storage

In `settings_manager.py`, the `keyring` library is used to never expose credentials in the code or in text files.

---

## Installation and Startup

1. Make sure you have Python 3 installed.
2. It is advisable to create a virtual environment: `python -m venv venv` and activate it.
3. Install the dependencies: `pip install -r requirements.txt`.
4. Start the application from the project root folder: `python main.py`.

### Create the Executable

To create a standalone `.exe` file, run the build script from the root folder:

```bash
python scripts/build.py
```

The compiled application will be in `dist/CalendarLogger`.

---

## Initial Configuration

To make the integrations work, follow these steps:

1. **Get Zoho credentials**: Go to the Zoho API console (`https://api-console.zoho.eu/`) and create a new **Self-Client** type client. This will provide you with a `Client ID`, a `Client Secret`, and a `Refresh Token`.
2. **Get Google Calendar credentials**:
    * Go to the [Google Cloud Console](https://console.cloud.google.com/).
    * Create a new project.
    * Enable the "Google Calendar API".
    * Create credentials for a "Desktop app" OAuth client.
    * Download the `credentials.json` file and place it in the `calendar_logger` folder.
3. **Start the app** and click the **"Settings"** button.
4. **Enter the credentials** obtained in the respective fields.
5. Click **"Save Settings"**.

---

## Automated Build and Release

This project uses **GitHub Actions** to automate the creation of executables for Windows, macOS, and Linux. The workflow, defined in `.github/workflows/release.yml`, is triggered every time a new tag (e.g., `v1.0.1`) is pushed to the repository.

The workflow automatically builds the executables and attaches them as assets to a new GitHub Release.

---

## Possible Future Improvements

* **UI for Errors**: Show error messages in dialog windows instead of on the console.
* **Datepicker Widget**: Replace manual date entry with a calendar widget to improve usability.
* **Fetch of Projects/Tasks**: Instead of manually entering project and task IDs, implement API calls that retrieve the list of existing projects and tasks and show them in a dropdown menu.
* **Drag and Drop**: Implement moving and resizing events with the mouse.
