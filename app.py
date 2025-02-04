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

# Check Google Docs connection status
@app.route('/check-google-connection')
def check_google_connection():
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        return jsonify({"connected": creds and creds.valid})
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)})

# Fetch company details using OpenAI API
def fetch_company_details(company_name, details, api_key):
    try:
        client = OpenAI(api_key=api_key)
        
        # Collect details based on user input
        selected_details = []
        if details.get("overview"):
            selected_details.append("Company Overview")
        if details.get("ticker"):
            selected_details.append("Ticker Symbol")
        if details.get("marketCap"):
            selected_details.append("Market Cap & Revenue")
        if details.get("hq"):
            selected_details.append("Headquarters Location")
        if details.get("employees"):
            selected_details.append("Number of Employees")
        if details.get("support"):
            selected_details.append("Customer Support System Overview")
        if details.get("contacts"):
            selected_details.append("Contact Information (Phone, Email, Social Media)")

        # Construct the Facebook search query for email and phone
        facebook_query = f'site:Facebook.com "{company_name}" "USA" "@gmail.com"'

        prompt = f"""
        Provide a comprehensive, detailed, and well-organized overview of {company_name} in details, including the following:

        {', '.join(selected_details)}. Each section should be labeled clearly, and any missing information should be stated explicitly. 

        The contact section should include the following information in a structured format:

        | Phone Number | Email Address | Location | Website | Instagram | Facebook | LinkedIn | X (Twitter) |

        Include the following simulated search results for the query:
        "{facebook_query}" as if you searched it on Facebook. Even though you cannot directly access Facebook, please construct a realistic set of results that would include email addresses, phone numbers, and social media links. 

        If information is missing or unavailable, please clearly indicate this. Be sure to include only relevant details for lead generation.

        Please use emojis to enhance readability and engagement, especially for contact information. For example, add a 📧 for emails, 📱 for phone numbers, and 🔗 for social media links. 

        Also, format the data into 3 pages with well-organized sections, so it is clear and easy to navigate.
        """
        
        response = client.chat.completions.create(
            model="chatgpt-40-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=9000,  
        )
        
        return response.choices[0].message.content or "No details available"
    
    except Exception as e:
        return f"Error: {str(e)}"


# Create Google Doc
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
    # Get the API key from the Authorization header
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not api_key:
        return jsonify({"error": "No API key provided. Please enter your API key in settings."}), 400

    data = request.json
    company_name = data.get("company_name")
    details = data.get("details", {})

    company_details = fetch_company_details(company_name, details, api_key)
    doc_url = create_google_doc(company_name, company_details)

    return jsonify({"message": "Google Doc created successfully!", "doc_url": doc_url})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
