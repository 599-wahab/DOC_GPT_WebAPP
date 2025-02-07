from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

app = Flask(__name__)

# Google Docs API Scopes
SCOPES = ['https://www.googleapis.com/auth/documents']

def initialize_google_docs():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('docs', 'v1', credentials=creds)

@app.route('/check-google-connection')
def check_google_connection():
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        return jsonify({"connected": creds and creds.valid})
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)})

def fetch_company_details(company_name, details, api_key):
    try:
        client = OpenAI(api_key=api_key)
        
        base_prompt = []
        selected_details = []
        
        # Base details
        if details.get("overview"):
            selected_details.append("Company Overview")
        if details.get("ticker"):
            selected_details.append("Ticker Symbol")
        if details.get("market_cap"):
            selected_details.append("Market Cap & Revenue")
        if details.get("headquarters"):
            selected_details.append("Headquarters Location")
        if details.get("employees"):
            selected_details.append("Number of Employees")
        if details.get("support"):
            selected_details.append("Customer Support System Overview")
        if details.get("contacts"):
            selected_details.append("Contact Information (Phone, Email, Social Media)")

        base_query = f"""
        Provide a comprehensive overview of {company_name} including:
        {', '.join(selected_details) if selected_details else 'basic company information'}.
        Format with clear section headers and emojis for readability.
        """
        
        base_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": base_query}],
            max_tokens=3000
        ).choices[0].message.content

        # Advanced Instagram Search
        advanced_content = ""
        if details.get("advanced_search"):
            instagram_query = f'site:instagram.com "{company_name}" "United States" "@gmail.com"'
            
            advanced_prompt = f"""
            Analyze simulated Instagram search results for: {instagram_query}
            
            Create a structured table containing:
            - Profile Name (with Instagram link)
            - Email Addresses (📧)
            - Phone Numbers (📱)
            - Location (📍)
            - Key Keywords
            
            Format as:
            | Profile | Email | Phone | Location | Keywords |
            |---------|-------|-------|----------|----------|
            [Add 10 realistic entries with some missing data]
            
            Include a disclaimer about data accuracy.
            """
            
            advanced_response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": advanced_prompt}],
                max_tokens=2000
            )
            advanced_content = "\n\n## 🔍 Advanced Instagram Search Results\n" + advanced_response.choices[0].message.content

        return f"{base_response}{advanced_content}"
    
    except Exception as e:
        return f"Error: {str(e)}"

def create_google_doc(company_name, content):
    if not content:
        return "Error: Content is empty."

    docs_service = initialize_google_docs()
    title = f"{company_name} Overview"
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']

    requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
    docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    return f"https://docs.google.com/document/d/{doc_id}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not api_key:
        return jsonify({"error": "API key required"}), 400

    data = request.json
    company_name = data.get("company_name")
    details = data.get("details", {})

    company_details = fetch_company_details(company_name, details, api_key)
    doc_url = create_google_doc(company_name, company_details)

    return jsonify({"message": "Document created", "doc_url": doc_url})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
