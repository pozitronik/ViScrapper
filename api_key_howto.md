### Step-by-Step Guide to Creating a Service Account JSON Key

#### Phase 1: Google Cloud Project and API Setup

1.  **Go to the Google Cloud Console:**
    *   Open your web browser and navigate to the [Google Cloud Console](https://console.cloud.google.com/). Log in with your Google account if you haven't already.

2.  **Create or Select a Project:**
    *   At the top of the page, you'll see a project selector dropdown.
    *   If you don't have a project, click the dropdown, then click **"NEW PROJECT"**. Give it a name (e.g., "API Scraper Project") and click **"CREATE"**.
    *   If you already have a project you want to use, simply select it from the list.

3.  **Enable the Necessary APIs:**
    *   You need to enable the Google Drive and Google Sheets APIs for this project.
    *   Use the navigation menu (☰) on the left and go to **APIs & Services > Library**.
    *   Search for **"Google Drive API"**, select it, and click the **"ENABLE"** button.
    *   Go back to the Library, search for **"Google Sheets API"**, select it, and click **"ENABLE"**.

#### Phase 2: Create the Service Account and Key

4.  **Navigate to Service Accounts:**
    *   In the navigation menu (☰), go to **IAM & Admin > Service Accounts**.

5.  **Create the Service Account:**
    *   Click the **"+ CREATE SERVICE ACCOUNT"** button at the top.
    *   **Service account name:** Give it a descriptive name, like `viparser-sheet-writer`.
    *   **Service account ID:** This will be automatically generated based on the name. You can leave it as is.
    *   **Description:** Add a short description if you like, e.g., "Service account for writing product data to Google Sheets".
    *   Click **"CREATE AND CONTINUE"**.

6.  **Grant Permissions (Important):**
    *   In the "Grant this service account access to project" step, you need to give it a role.
    *   Click the "Select a role" dropdown. For simplicity and to ensure it has enough permissions, select **Project > Editor**.
    *   Click **"CONTINUE"**.

7.  **Grant User Access (Optional):**
    *   You can skip this step. Click **"DONE"**.

8.  **Generate the JSON Key:**
    *   You will now be back on the Service Accounts page. Find the account you just created in the list.
    *   Click on the three vertical dots (⋮) under the "Actions" column for your new service account, and select **"Manage keys"**.
    *   Click on **ADD KEY > Create new key**.
    *   A dialog will pop up. Make sure **JSON** is selected as the key type.
    *   Click **"CREATE"**.

The JSON key file will be automatically generated and downloaded to your computer. **Treat this file like a password; do not share it publicly or commit it to a Git repository.**

#### Phase 3: Final Steps

9.  **Share Your Google Sheet with the Service Account:**
    *   Open the JSON file you just downloaded in a text editor.
    *   Find the `client_email` property. It will look something like `viparser-sheet-writer@your-project-id.iam.gserviceaccount.com`. Copy this email address.
    *   Open the Google Sheet you want to write data to.
    *   Click the **"Share"** button in the top right corner.
    *   Paste the `client_email` address into the sharing dialog, give it **Editor** permissions, and click **"Share"**. This is a critical step that allows your script, acting as the service account, to access and modify the sheet.

10. **Configure Your Project:**
    *   Move the downloaded JSON file to a secure location on your computer (e.g., within your project directory but listed in `.gitignore`).
    *   Update the `backend/.env` file in your project with the **absolute path** to this JSON file.
        ```
        GOOGLE_SERVICE_ACCOUNT_JSON_PATH="/path/to/your/downloaded-key-file.json"
        ```
