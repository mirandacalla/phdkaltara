from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import psycopg2
from psycopg2.extras import RealDictCursor
import os


app = Flask(__name__)
app.secret_key = '1234'  # Change this to a strong secret key

# Enable session management
app.config['SESSION_TYPE'] = 'filesystem'

def create_table(db_name):
    conn = sqlite3.connect(f'instance/{db_name}.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date_discussed TEXT NOT NULL,
            status TEXT,
            meeting_notes TEXT,
            revision_details TEXT
    )
''')


    conn.commit()
    conn.close()

# Call the function for both databases
create_table("provincial")
create_table("regional")

# Admin Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'admin123':  # Change this to a secure password
            session['admin'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

# Admin Logout Route
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

# Home route
@app.route('/')
def index():
    conn_provincial = sqlite3.connect('instance/provincial.db')
    conn_regional = sqlite3.connect('instance/regional.db')

    cursor_provincial = conn_provincial.cursor()
    cursor_regional = conn_regional.cursor()

    cursor_provincial.execute("SELECT * FROM drafts;")
    provincial_drafts = cursor_provincial.fetchall()
    cursor_regional.execute("SELECT * FROM drafts;")
    regional_drafts = cursor_regional.fetchall()

    provincial_count = len(provincial_drafts)
    regional_count = len(regional_drafts)

    pembahasan_count_provincial = sum(1 for draft in provincial_drafts if draft[3] == 'pembahasan')
    harmonisasi_count_provincial = sum(1 for draft in provincial_drafts if draft[3] == 'harmonisasi')
    fasilitasi_count_provincial = sum(1 for draft in provincial_drafts if draft[3] == 'fasilitasi')

    pembahasan_count_regional = sum(1 for draft in regional_drafts if draft[3] == 'pembahasan')
    harmonisasi_count_regional = sum(1 for draft in regional_drafts if draft[3] == 'harmonisasi')
    fasilitasi_count_regional = sum(1 for draft in regional_drafts if draft[3] == 'fasilitasi')



    conn_provincial.close()
    conn_regional.close()



    return render_template('index.html',
                           provincial_drafts=provincial_drafts,
                           regional_drafts=regional_drafts,
                           provincial_count=provincial_count,
                           regional_count=regional_count,
                           pembahasan_count_provincial=pembahasan_count_provincial,
                           harmonisasi_count_provincial=harmonisasi_count_provincial,
                           fasilitasi_count_provincial=fasilitasi_count_provincial,
                           pembahasan_count_regional=pembahasan_count_regional,
                           harmonisasi_count_regional=harmonisasi_count_regional,
                           fasilitasi_count_regional=fasilitasi_count_regional,
                           is_admin=session.get('admin', False))


# Insert Route
@app.route('/insert/<db_name>', methods=['GET', 'POST'])
def insert(db_name):
    if request.method == 'POST':
        # Get the form data
        title = request.form['title']
        date_discussed = request.form['date_discussed']
        status = request.form['status']
        meeting_notes = request.form['meeting_notes']
        revision_details = request.form['revision_details']



        # Store data in session before saving to the database
        session['draft'] = {
            'title': title,
            'date_discussed': date_discussed,
            'status': status,  # ✅ Status moved up
            'meeting_notes': meeting_notes,
            'revision_details': revision_details  # ✅ Correct key name
        }


        # Connect to the database and insert the data
        conn = sqlite3.connect(f'instance/{db_name}.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO drafts (title, date_discussed, status, meeting_notes, revision_details)
            VALUES (?, ?, ?, ?, ?);
        """, (title, date_discussed, status, meeting_notes, revision_details))  # ✅ Fixed


        conn.commit()
        conn.close()

        # Redirect back to the homepage
        return redirect(url_for('index'))

    return render_template('insert.html', db_name=db_name)

# Edit Route (AJAX Handling)
@app.route('/edit/<db_name>', methods=['GET', 'POST'])
@app.route('/edit/<db_name>/<int:draft_id>', methods=['GET', 'POST'])
def edit(db_name, draft_id=None):
    if draft_id:
        # Edit draft logic
        conn = sqlite3.connect(f'instance/{db_name}.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drafts WHERE id = ?;", (draft_id,))
        draft = cursor.fetchone()
        conn.close()
    else:
        draft = None  # No draft for new draft creation

    if request.method == 'POST':
        # Form data
        title = request.form['title']
        date_discussed = request.form['date_discussed']
        status = request.form['status']
        meeting_notes = request.form['meeting_notes']
        revision_details = request.form['revision_details']


        # Store data in session before saving to the database
        session['draft'] = {
            'title': title,
            'date_discussed': date_discussed,
            'status': status,  # ✅ Status moved up
            'meeting_notes': meeting_notes,
            'revision_details': revision_details  # ✅ Correct key name
        }


        # Insert or update draft in database
        conn = sqlite3.connect(f'instance/{db_name}.db')
        cursor = conn.cursor()

        if draft_id:
            # Update existing draft
            cursor.execute("""
                UPDATE drafts
                SET title = ?, date_discussed = ?, status = ?, meeting_notes = ?, revision_details = ?
                WHERE id = ?;
            """, (title, date_discussed, status, meeting_notes, revision_details, draft_id))  # ✅ Fixed order & variable name


        else:
            # Insert new draft
            cursor.execute("""
                INSERT INTO drafts (title, date_discussed, status, meeting_notes, revision_details)
                VALUES (?, ?, ?, ?, ?);
            """, (title, date_discussed, status, meeting_notes, revision_details))  # ✅ Fixed


        conn.commit()
        conn.close()

        # Return a JSON response for AJAX
        return jsonify({"success": True, "message": "Draft saved successfully!"})

    return render_template('edit.html', db_name=db_name, draft=draft)


# Add Route for Adding Data to Draft
@app.route('/add/<db_name>', methods=['GET', 'POST'])
def add(db_name):
    if request.method == 'POST':
        title = request.form.get('title')
        date_discussed = request.form.get('date_discussed')
        status = request.form.get('status')
        meeting_notes = request.form.get('meeting_notes')
        revision_details = request.form.get('revision_details')

        # Basic validation
        if title and date_discussed:
            conn = sqlite3.connect(f'instance/{db_name}.db')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO drafts (title, date_discussed, status, meeting_notes, revision_details)
                VALUES (?, ?, ?, ?, ?)
            """, (title, date_discussed, status, meeting_notes, revision_details))
            conn.commit()
            conn.close()

        return redirect(url_for('index'))

    return render_template('edit.html', db_name=db_name)


# Delete Route (Using POST for Security)
@app.route('/delete/<db_name>/<int:draft_id>', methods=['POST'])
def delete(db_name, draft_id):
    if not session.get('admin'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403  # Prevent unauthorized deletion

    try:
        # Connect to the database
        conn = sqlite3.connect(f'instance/{db_name}.db')
        cursor = conn.cursor()

        # Delete the draft from the database
        cursor.execute("DELETE FROM drafts WHERE id = ?;", (draft_id,))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Draft deleted successfully!"})

    except Exception as e:
        print("Error deleting draft:", str(e))  # Log error in terminal
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/update/<db_name>/<int:draft_id>', methods=['POST'])
def update_draft(db_name, draft_id):
    data = request.get_json()
    print("Received data:", data)  # Debugging log

    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    try:
        conn = sqlite3.connect(f'instance/{db_name}.db')
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE drafts
            SET title=?, date_discussed=?, status=?, meeting_notes=?, revision_details=?
            WHERE id=?;
        """, (
            data.get('title'),
            data.get('date_discussed'),
            data.get('status'),
            data.get('meeting_notes'),
            data.get('revision_details'),
            draft_id
        ))


        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        print("Error updating draft:", str(e))  # Log error in terminal
        return jsonify({"success": False, "message": str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True)
