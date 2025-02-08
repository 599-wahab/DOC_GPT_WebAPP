from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json

app = Flask(__name__)

# Google Docs API Scopes
SCOPES = ['https://www.googleapis.com/auth/documents']

def initialize_google_docs():
    try:
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_json:
            raise ValueError("Google credentials not found in environment variables")
            
        creds_info = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, 
            scopes=SCOPES
        )
        return build('docs', 'v1', credentials=credentials)
    except Exception as e:
        raise RuntimeError(f"Google Docs initialization failed: {str(e)}")

@app.route('/check-google-connection')
def check_google_connection():
    try:
        initialize_google_docs()
        return jsonify({"connected": True})
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)})

def fetch_company_details(company_name, details, api_key):
    try:
        client = OpenAI(api_key=api_key)
        
        selected_details = []
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
            
            Format as markdown table with 10 realistic entries.
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
        return f"Error generating content: {str(e)}"

def create_google_doc(company_name, content):
    try:
        if not content:
            return "Error: Content is empty."

        docs_service = initialize_google_docs()
        title = f"{company_name} Overview"
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']

        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        return f"https://docs.google.com/document/d/{doc_id}"
    except Exception as e:
        return f"Error creating document: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if not api_key:
            return jsonify({"error": "API key required"}), 400

        data = request.get_json()
        company_name = data.get("company_name")
        if not company_name:
            return jsonify({"error": "Company name required"}), 400
        details = data.get("details", {})

        company_details = fetch_company_details(company_name, details, api_key)
        if "Error:" in company_details:
            return jsonify({"error": company_details}), 500

        doc_url = create_google_doc(company_name, company_details)
        if "Error:" in doc_url:
            return jsonify({"error": doc_url}), 500

        return jsonify({"message": "Document created", "doc_url": doc_url})
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)