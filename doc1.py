import tkinter as tk
from tkinter import ttk, messagebox
from openai import OpenAI
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

# OpenAI API Key
client = OpenAI(api_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")  # Replace with your OpenAI API key

# Google Docs API Scopes
SCOPES = ['https://www.googleapis.com/auth/documents']

# Check if credentials.json exists
if not os.path.exists('credentials.json'):
    messagebox.showerror("Error", "The 'credentials.json' file is missing. Please set up the Google Docs API and download the file.")
    exit()

# Initialize Google Docs API
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

# Fetch company details using OpenAI API
def fetch_company_details(company_name):
    try:
        prompt = f"Provide a comprehensive overview of {company_name}, including the company overview, ticker symbol (if applicable), market cap & revenue (if publicly available), headquarters location, number of employees, and customer support system overview."
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        if "insufficient_quota" in str(e):
            messagebox.showerror("Error", "You have exceeded your OpenAI API quota. Please check your billing and usage details.")
        else:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        return None

# Create Google Doc
def create_google_doc(company_name, content):
    docs_service = initialize_google_docs()
    title = f"{company_name} Overview"
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']

    requests = [
        {
            'insertText': {
                'location': {
                    'index': 1,
                },
                'text': content
            }
        }
    ]

    docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    return doc_id

# Tkinter GUI
def generate_document():
    company_name = entry.get()
    if not company_name:
        messagebox.showerror("Error", "Please enter a company name")
        return

    try:
        company_details = fetch_company_details(company_name)
        if company_details:
            doc_id = create_google_doc(company_name, company_details)
            messagebox.showinfo("Success", f"Google Doc created successfully! Document ID: {doc_id}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Initialize Tkinter
root = tk.Tk()
root.title("Google Doc Generator")
root.geometry("500x300")  # Set window size
root.resizable(False, False)  # Disable resizing

# Custom Styling
style = ttk.Style()
style.configure("TFrame", background="#f0f0f0")
style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 12))
style.configure("TButton", font=("Helvetica", 12), padding=10)
style.configure("TEntry", font=("Helvetica", 12), padding=10)

# Main Frame
main_frame = ttk.Frame(root, padding="20")
main_frame.pack(fill=tk.BOTH, expand=True)

# Label
label = ttk.Label(main_frame, text="Enter Company Name:")
label.pack(pady=10)

# Entry
entry = ttk.Entry(main_frame, width=40)
entry.pack(pady=10)

# Button
button = ttk.Button(main_frame, text="Generate Document", command=generate_document)
button.pack(pady=20)

# Run the application
root.mainloop()