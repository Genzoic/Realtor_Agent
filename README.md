# Realtor_Agent
## Overview

This project is a web application built using Streamlit that automates the process of sending personalized real estate emails to clients based on their preferences and nearby property details. The application integrates with Google Sheets to fetch client and property data, and utilizes a language model to generate tailored email content.

## Features

- **Client and Property Management**: Store and manage client and property details in a SQLite database.
- **Email Generation**: Automatically generate personalized emails for clients based on their preferences and nearby amenities.
- **Follow-Up Emails**: Generate follow-up emails based on previous communications.
- **Google Sheets Integration**: Fetch client and property data from Google Sheets.
- **Dynamic UI**: A user-friendly interface built with Streamlit for easy navigation and interaction.

## Technologies Used

- Python
- Streamlit
- SQLite
- Google Sheets API
- Langchain
- BeautifulSoup
- Pydantic
- SMTP for email sending

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Genzoic/Realtor_Agent.git
   cd Realtor_Agent
   ```

2. **Create a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Required Packages**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Google Sheets API**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project and enable the Google Sheets API.
   - Create credentials (OAuth 2.0 Client IDs) and download the `credentials.json` file.
   - Place the `credentials.json` file in the project root directory.

5. **Set Up Environment Variables**:
   - Create a `.env` file in the project root directory and add the following variables:
     ```
     GROQ_API_KEY=your_groq_api_key          # Required for the LLM model
     GOOGLE_MAPS_API_KEY=your_google_maps_api_key
     password=your_email_password
     ```

## Usage

1. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

2. **Navigate the Application**:
   - Use the sidebar to select between "Configurations" and "Customizations".
   - Input the Google Sheets URLs for client and property details.
   - Click on "Submit" to load the data into the application.
   - Generate personalized emails based on the client details and nearby properties.

3. **Email Sending**:
   - After generating an email, you can send it directly from the application.
   - The application will log the email details in the SQLite database for future reference.
