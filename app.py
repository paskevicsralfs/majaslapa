"""
Entuziastu Volejbola Otrās Vīriešu Līgas Mājaslapa
Flask Application with SQLite Database
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'evl-secret-key-2024'
DATABASE = 'volleyball.db'


def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with schema and sample data"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create teams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            logo TEXT DEFAULT '/static/volleyball.svg',
            played INTEGER DEFAULT 0,
            won INTEGER DEFAULT 0,
            lost INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            sets_won INTEGER DEFAULT 0,
            sets_lost INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            position TEXT NOT NULL,
            team_id INTEGER,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    ''')

    # Create games table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            location TEXT NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            home_sets INTEGER DEFAULT 0,
            away_sets INTEGER DEFAULT 0,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (home_team_id) REFERENCES teams (id),
            FOREIGN KEY (away_team_id) REFERENCES teams (id)
        )
    ''')



    # Check if data exists
    cursor.execute('SELECT COUNT(*) FROM teams')
    if cursor.fetchone()[0] == 0:
        # Insert sample teams
        teams_data = [
            ('Riga Stars', 10, 8, 2, 24, 24, 8),
            ('Daugavpils Warriors', 10, 7, 3, 21, 22, 12),
            ('Jelgava Eagles', 10, 6, 4, 18, 20, 15),
            ('Ventspils Titans', 10, 5, 5, 15, 18, 18),
            ('Liepaja Lions', 10, 4, 6, 12, 14, 20),
            ('Valmiera Bulls', 10, 3, 7, 9, 12, 22),
        ]
        cursor.executemany('''
            INSERT INTO teams (name, played, won, lost, points, sets_won, sets_lost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', teams_data)

        # Insert sample players
        players_data = [
            ('Janis', 'Kalnins', 'Citurpuses', 1, '29123456'),
            ('Peteris', 'Ozols', 'Citurpuses', 1, '29234567'),
            ('Maris', 'Berzins', 'Centrs', 1, '29345678'),
            ('Juris', 'Klavins', 'Piecgajiens', 1, '29456789'),
            ('Aivars', 'Zeltins', 'Piecgajiens', 2, '29567890'),
            ('Armands', 'Kangro', 'Citurpuses', 2, '29678901'),
            ('Gints', 'Kalme', 'Centrs', 2, '29789012'),
            ('Raimonds', 'Vitols', 'Citurpuses', 2, '29890123'),
            ('Andris', 'Jansons', 'Piecgajiens', 3, '29901234'),
            ('Valdis', 'Lacis', 'Centrs', 3, '29112345'),
            ('Ilmars', 'Abolins', 'Citurpuses', 3, '29223456'),
            ('Henriks', 'Zarina', 'Piecgajiens', 3, '29334567'),
            ('Uldis', 'Kalnina', 'Citurpuses', 4, '29445678'),
            ('Aleksandrs', 'Veinbergs', 'Centrs', 4, '29556789'),
            ('Davis', 'Kurss', 'Piecgajiens', 4, '29667890'),
            ('Kristaps', 'Kalnins', 'Citurpuses', 5, '29778901'),
            ('Martins', 'Vitina', 'Centrs', 5, '29889012'),
            ('Ernests', 'Petrovics', 'Piecgajiens', 5, '29990123'),
            ('Davis', 'Zeltins', 'Citurpuses', 6, '29111234'),
            ('Guntars', 'Klavins', 'Centrs', 6, '29222345'),
            ('Rolands', 'Kalninsh', 'Piecgajiens', 6, '29333456'),
            ('Bruno', 'Abolinsh', 'Citurpuses', 6, '29444567'),
        ]
        cursor.executemany('''
            INSERT INTO players (first_name, last_name, position, team_id, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', players_data)

        # Insert sample games
        games_data = [
            (1, 2, '2024-11-15', '18:00', 'Riga Sports Hall', 3, 1, 3, 1, 'completed'),
            (3, 4, '2024-11-15', '20:00', 'Jelgava Hall', 2, 3, 2, 3, 'completed'),
            (5, 6, '2024-11-16', '17:00', 'Liepaja Sports Center', 3, 0, 3, 0, 'completed'),
            (1, 3, '2024-11-22', '18:00', 'Riga Sports Hall', 3, 2, 3, 2, 'completed'),
            (2, 5, '2024-11-22', '19:00', 'Daugavpils Hall', 1, 3, 1, 3, 'completed'),
            (4, 6, '2024-11-23', '16:00', 'Ventspils Arena', 3, 1, 3, 1, 'completed'),
            (1, 4, '2024-11-29', '18:00', 'Riga Sports Hall', None, None, None, None, 'scheduled'),
            (2, 3, '2024-11-29', '19:00', 'Daugavpils Hall', None, None, None, None, 'scheduled'),
            (5, 6, '2024-11-30', '17:00', 'Liepaja Sports Center', None, None, None, None, 'scheduled'),
            (3, 1, '2024-12-06', '18:00', 'Jelgava Hall', None, None, None, None, 'scheduled'),
            (4, 2, '2024-12-06', '19:00', 'Ventspils Arena', None, None, None, None, 'scheduled'),
            (6, 5, '2024-12-07', '16:00', 'Valmiera Sports Hall', None, None, None, None, 'scheduled'),
        ]
        cursor.executemany('''
            INSERT INTO games (home_team_id, away_team_id, date, time, location, home_score, away_score, home_sets, away_sets, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', games_data)

    conn.commit()
    conn.close()


@app.route('/')
def index():
    """Home page - championship overview"""
    conn = get_db_connection()

    # Get standings (top 6 teams)
    standings = conn.execute('''
        SELECT * FROM teams
        ORDER BY points DESC, sets_won DESC
    ''').fetchall()

    # Get recent games (completed)
    recent_games = conn.execute('''
        SELECT g.*,
               ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'completed'
        ORDER BY g.date DESC, g.time DESC
        LIMIT 4
    ''').fetchall()

    # Get upcoming games
    upcoming_games = conn.execute('''
        SELECT g.*,
               ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'scheduled'
        ORDER BY g.date ASC, g.time ASC
        LIMIT 3
    ''').fetchall()

    # Get top scorers (players with most appearances)
    top_players = conn.execute('''
        SELECT p.*, t.name as team_name
        FROM players p
        JOIN teams t ON p.team_id = t.id
        LIMIT 5
    ''').fetchall()

    conn.close()

    return render_template('index.html',
                         standings=standings,
                         recent_games=recent_games,
                         upcoming_games=upcoming_games,
                         top_players=top_players)


@app.route('/teams')
def teams():
    """Teams page with detailed statistics"""
    conn = get_db_connection()
    teams_list = conn.execute('''
        SELECT * FROM teams
        ORDER BY points DESC, sets_won DESC
    ''').fetchall()

    # Get player count for each team
    teams_with_counts = []
    for team in teams_list:
        player_count = conn.execute(
            'SELECT COUNT(*) FROM players WHERE team_id = ?',
            (team['id'],)
        ).fetchone()[0]
        teams_with_counts.append({
            'team': team,
            'player_count': player_count
        })

    conn.close()
    return render_template('teams.html', teams_data=teams_with_counts)


@app.route('/players')
def players():
    """Players page with filtering"""
    conn = get_db_connection()

    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    team_filter = request.args.get('team', '')

    if team_filter:
        players_list = conn.execute('''
            SELECT p.*, t.name as team_name
            FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE t.id = ?
            ORDER BY p.last_name
        ''', (team_filter,)).fetchall()
    else:
        players_list = conn.execute('''
            SELECT p.*, t.name as team_name
            FROM players p
            JOIN teams t ON p.team_id = t.id
            ORDER BY p.last_name
        ''').fetchall()

    conn.close()
    return render_template('players.html',
                         players=players_list,
                         teams=teams_list,
                         selected_team=team_filter)


# CRUD Routes for Players
@app.route('/admin/players')
def admin_players():
    """Admin page - list all players for management"""
    conn = get_db_connection()
    players_list = conn.execute('''
        SELECT p.*, t.name as team_name
        FROM players p
        JOIN teams t ON p.team_id = t.id
        ORDER BY p.last_name
    ''').fetchall()
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    conn.close()
    return render_template('admin_players.html',
                         players=players_list,
                         teams=teams_list)


@app.route('/admin/players/add', methods=['POST'])
def add_player():
    """Add new player"""
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    position = request.form['position']
    team_id = request.form['team_id']
    phone = request.form.get('phone', '')

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO players (first_name, last_name, position, team_id, phone)
        VALUES (?, ?, ?, ?, ?)
    ''', (first_name, last_name, position, team_id, phone))
    conn.commit()
    conn.close()

    flash('Speletajs pievienots veiksmigi!', 'success')
    return redirect(url_for('admin_players'))


@app.route('/admin/players/edit/<int:id>', methods=['GET', 'POST'])
def edit_player(id):
    """Edit existing player"""
    conn = get_db_connection()

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        position = request.form['position']
        team_id = request.form['team_id']
        phone = request.form.get('phone', '')

        conn.execute('''
            UPDATE players
            SET first_name = ?, last_name = ?, position = ?, team_id = ?, phone = ?
            WHERE id = ?
        ''', (first_name, last_name, position, team_id, phone, id))
        conn.commit()
        conn.close()

        flash('Speletajs atjauinats veiksmigi!', 'success')
        return redirect(url_for('admin_players'))

    player = conn.execute('''
        SELECT p.*, t.name as team_name
        FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE p.id = ?
    ''', (id,)).fetchone()
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    conn.close()

    if player is None:
        flash('Speletajs nav atrasts!', 'error')
        return redirect(url_for('admin_players'))

    return render_template('edit_player.html', player=player, teams=teams_list)


@app.route('/admin/players/delete/<int:id>', methods=['POST'])
def delete_player(id):
    """Delete player"""
    conn = get_db_connection()
    conn.execute('DELETE FROM players WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Speletajs izdzests veiksmigi!', 'success')
    return redirect(url_for('admin_players'))


@app.route('/schedule')
def schedule():
    """Games schedule page with past and upcoming games"""
    conn = get_db_connection()

    # Get all completed games
    completed_games = conn.execute('''
        SELECT g.*,
               ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'completed'
        ORDER BY g.date DESC, g.time DESC
    ''').fetchall()

    # Get all scheduled games
    scheduled_games = conn.execute('''
        SELECT g.*,
               ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'scheduled'
        ORDER BY g.date ASC, g.time ASC
    ''').fetchall()

    conn.close()

    return render_template('schedule.html',
                         completed_games=completed_games,
                         scheduled_games=scheduled_games)



@app.route('/about')
def about():
    """Project description page"""
    return render_template('about.html')


# Initialize database on startup
init_db()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
