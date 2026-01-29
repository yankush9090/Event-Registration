# Flask and dependencies
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from flask_mail import Mail, Message
import json
import os
from openpyxl import Workbook
from flask import send_file
import tempfile
import sqlite3

# Path to your SQLite database file
DB_PATH = 'registrations.db'


# Initialize Flask app and CORS
app = Flask(__name__)
CORS(app)


# Export registrations for a specific event as Excel
@app.route('/export-excel', methods=['GET'])
def export_excel():
    event_name = request.args.get('event')
    registrations = load_registrations()
    filtered_regs = []
    if event_name:
        for reg in registrations:
            # Handle both list and string event fields
            if 'events' in reg:
                if isinstance(reg['events'], list):
                    if any(str(e).lower() == event_name.lower() for e in reg['events']):
                        filtered_regs.append(reg)
                elif isinstance(reg['events'], str):
                    if reg['events'].lower() == event_name.lower():
                        filtered_regs.append(reg)
    else:
        filtered_regs = registrations

    # Create Excel file
    wb = Workbook()
    ws = wb.active
    ws.title = event_name if event_name else "Registrations"

    # Header (add more fields as needed)
    ws.append(["Name", "Email", "Student ID", "Phone", "Gender", "Events", "Activity"])

    # For sports event, group boys and girls separately
    if event_name and event_name.lower() == 'sports':
        boys = []
        girls = []
        others = []
        for reg in filtered_regs:
            gender = (reg.get('gender') or '').lower()
            activity = reg.get('projectName') or reg.get('otherActivity')
            if not activity:
                sports = reg.get('sports')
                if sports:
                    if isinstance(sports, list):
                        activity = ', '.join(sports)
                    else:
                        activity = str(sports)
                else:
                    activity = 'N/A'
            row = [
                reg.get('name', ''),
                reg.get('email', ''),
                reg.get('studentId', ''),
                reg.get('phone', ''),
                reg.get('gender', ''),
                ', '.join(reg['events']) if isinstance(reg.get('events'), list) else reg.get('events', ''),
                activity
            ]
            if gender == 'male':
                boys.append(row)
            elif gender == 'female':
                girls.append(row)
            else:
                others.append(row)
        # Write boys section
        ws.append([])
        ws.append(["--- Boys Registrations ---"])
        ws.append(["Name", "Email", "Student ID", "Phone", "Gender", "Events", "Activity"])
        for row in boys:
            ws.append(row)
        # Write girls section
        ws.append([])
        ws.append(["--- Girls Registrations ---"])
        ws.append(["Name", "Email", "Student ID", "Phone", "Gender", "Events", "Activity"])
        for row in girls:
            ws.append(row)
        # Write others section if any
        if others:
            ws.append([])
            ws.append(["--- Other/Unspecified Gender Registrations ---"])
            ws.append(["Name", "Email", "Student ID", "Phone", "Gender", "Events", "Activity"])
            for row in others:
                ws.append(row)
    else:
        for reg in filtered_regs:
            activity = reg.get('projectName') or reg.get('otherActivity')
            if not activity:
                if event_name and event_name.lower() == 'sports' and reg.get('sports'):
                    sports = reg.get('sports')
                    if isinstance(sports, list):
                        activity = ', '.join(sports)
                    else:
                        activity = str(sports)
                else:
                    activity = 'N/A'
            ws.append([
                reg.get('name', ''),
                reg.get('email', ''),
                reg.get('studentId', ''),
                reg.get('phone', ''),
                reg.get('gender', ''),
                ', '.join(reg['events']) if isinstance(reg.get('events'), list) else reg.get('events', ''),
                activity
            ])

    # Auto-size columns
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        col_letter = column_cells[0].column_letter
        ws.column_dimensions[col_letter].width = length + 2

    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(temp_file.name)

    download_filename = f"{event_name}_registrations.xlsx" if event_name else "registrations.xlsx"
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=download_filename
    )

# Flask-Mail configuration (update with your SMTP server details)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your_gmail@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your_gmail_app_password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'your_gmail@gmail.com')
mail = Mail(app)

# --- Admin users setup ---
# --- Admin users setup ---
ADMINS = [
    {
        "username": "Ashi",
        "password": "2110",
        "profile": {
            "name": "Ashi Singh",
            "email": "anshikav2700@gmail.com",
            "image": "ashi.jpeg",
            "description": "Designer, Planner, Developer, and Administrator of this website."
        }
    },
    {
        "username": "Aarthi",
        "password": "2005",
        "profile": {
            "name": "Aarthi Madiwal",
            "email": "aarthimadiwal67@gmial.com",
            "image": "Aarthi.jpeg",
            "description": "Co-Planner, Content Contributor, and Event Organizer for this website."
        }
    },
    {
        "username": "Uma",
        "password": "2005",
        "profile": {
            "name": "Uma Maheshwari",
            "email": "yankush9090@gmail.com",
            "image": "uma.jpeg",
            "description": "Support, Testing, and Event Management for this website."
        }
    }
]

# Collect all admin emails
ADMIN_EMAILS = [admin['profile']['email'] for admin in ADMINS if 'profile' in admin and 'email' in admin['profile']]

@app.route('/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    for admin in ADMINS:
        if admin['username'].lower() == username and admin['password'] == password:
            return jsonify({
                "status": "success",
                "admin": admin['username'],
                "profile": admin.get('profile', {})
            })
    return jsonify({"status": "fail", "error": "Invalid credentials"}), 401

# Update event enabled/disabled state
@app.route('/events/enabled', methods=['POST'])
def update_event_enabled():
    data = request.json
    enabled_map = data.get('enabled_map', {})
    events = load_events()
    disabled_events = []
    for event in events:
        if event['name'] in enabled_map:
            # If event is being disabled now, add to disabled_events
            if event['enabled'] and not enabled_map[event['name']]:
                disabled_events.append(event['name'])
            event['enabled'] = enabled_map[event['name']]
    save_events(events)
    # Remove registrations for disabled events
    if disabled_events:
        registrations = load_registrations()
        new_regs = []
        for reg in registrations:
            # Remove disabled events from reg['events']
            if 'events' in reg and isinstance(reg['events'], list):
                reg['events'] = [e for e in reg['events'] if e not in disabled_events]
                # If no events left, skip this registration
                if not reg['events']:
                    continue
            elif 'events' in reg and reg['events'] in disabled_events:
                continue
            new_regs.append(reg)
        save_registrations(new_regs)
    return jsonify({"status": "success"})
# Delete registration endpoint
@app.route('/registrations', methods=['DELETE'])
def delete_registration():
    data = request.json
    index = data.get('index')
    registrations = load_registrations()
    if index is not None and 0 <= index < len(registrations):
        registrations.pop(index)
        save_registrations(registrations)
        return jsonify({"status": "success"})
    return jsonify({"status": "fail", "error": "Invalid index"}), 400

# Registration storage
REGISTRATIONS_FILE = 'registrations.json'

def load_registrations():
    if not os.path.exists(REGISTRATIONS_FILE):
        return []
    with open(REGISTRATIONS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_registrations(registrations):
    with open(REGISTRATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(registrations, f, ensure_ascii=False, indent=2)


# Add registration endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    registrations = load_registrations()
    # Prevent duplicate registration by studentId
    student_id = data.get('studentId')
    # Validate studentId: must be exactly 12 digits
    if not student_id or not str(student_id).isdigit() or len(str(student_id)) != 12:
        return jsonify({"status": "fail", "error": "Student ID must be exactly 12 digits."}), 400
    if any(r.get('studentId') == student_id for r in registrations):
        return jsonify({"status": "fail", "error": "Student ID already registered."}), 400
    registrations.append(data)
    save_registrations(registrations)
    return jsonify({"status": "success", "registration": data})

# Get all registrations endpoint
@app.route('/registrations', methods=['GET'])
def get_registrations():
    registrations = load_registrations()
    return jsonify(registrations)

# Set your OpenAI API key here
openai.api_key = "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"


# File to store events
EVENTS_FILE = 'events.json'

def load_events():
    if not os.path.exists(EVENTS_FILE):
        return []
    with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_events(events):
    with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


# Add event endpoint
@app.route('/add_event', methods=['POST'])
def add_event():
    data = request.json
    events = load_events()
    events.append(data)
    save_events(events)
    return jsonify({"status": "success", "event": data})

# Get all events endpoint
@app.route('/events', methods=['GET'])
def get_events():
    events = load_events()
    return jsonify(events)

# Delete event endpoint
@app.route('/events', methods=['DELETE'])
def delete_event():
    data = request.json
    index = data.get('index')
    events = load_events()
    if index is not None and 0 <= index < len(events):
        # Get event name before deleting
        event_name = events[index]['name']
        events.pop(index)
        save_events(events)
        # Remove registrations for this event
        registrations = load_registrations()
        registrations = [r for r in registrations if event_name not in (r.get('events') if isinstance(r.get('events'), list) else [r.get('events')])]
        save_registrations(registrations)
        return jsonify({"status": "success"})
    return jsonify({"status": "fail", "error": "Invalid index"}), 400

# Example AI route (chatbot or suggestion)
@app.route('/ai', methods=['POST'])
def ai():
    user_message = request.json.get('message', '')
    # Call OpenAI API for response
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_message}]
    )
    ai_reply = response.choices[0].message['content']
    return jsonify({"reply": ai_reply})

# Health check
# Health check
@app.route('/')
def home():
    return "Backend is running!"


# Contact Admin endpoint
@app.route('/contact-admin', methods=['POST'])
def contact_admin():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()
    if not name or not email or not message:
        return jsonify({'status': 'fail', 'error': 'All fields are required.'}), 400
    try:
        msg = Message(
            subject=f"[Student Query] New message from {name}",
            recipients=ADMIN_EMAILS,
            body=f"Student Name: {name}\nStudent Email: {email}\n\nMessage:\n{message}"
        )
        mail.send(msg)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'fail', 'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
