from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'evl-secret-key-2024'
DATABASE = 'volleyball.db'

def get_db_connection():
    """Izveido savienojumu ar datubāzi"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Sākumlapa - turnīra tabula un spēles"""
    conn = get_db_connection()
    
    # 1. Atlasām komandas turnīra tabulai
    teams = conn.execute('SELECT * FROM teams').fetchall()

    standings = []
    for team in teams:
        t = dict(team)
        total_sets = t['sets_won'] + t['sets_lost']
        # Aprēķinām procentu kārtošanai
        t['win_percentage'] = (t['sets_won'] / total_sets * 100) if total_sets > 0 else 0
        standings.append(t)

    # Kārtojam: punkti (prioritāte), tad procents (abi dilstošā secībā)
    standings = sorted(standings, key=lambda x: (x['points'], x['win_percentage']), reverse=True)

    # 2. Atlasām pēdējās spēles
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

    # 3. Atlasām gaidāmās spēles
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

    conn.close()

    return render_template('index.html', 
                         standings=standings,
                         recent_games=recent_games,
                         upcoming_games=upcoming_games)

@app.route('/teams')
def teams():
    """Komandu lapa ar statistiku"""
    conn = get_db_connection()
    teams_list = conn.execute('''
        SELECT * FROM teams
        ORDER BY points DESC, sets_won DESC
    ''').fetchall()

    # Iegūstam spēlētāju skaitu katrai komandai
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
    """Spēlētāju saraksts ar filtrēšanu"""
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

# --- ADMIN / CRUD SEKCIJA ---

@app.route('/admin/players')
def admin_players():
    """Admin lapa - spēlētāju pārvaldība"""
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
    """Pievienot jaunu spēlētāju"""
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

    flash('Spēlētājs pievienots veiksmīgi!', 'success')
    return redirect(url_for('admin_players'))

@app.route('/admin/players/edit/<int:id>', methods=['GET', 'POST'])
def edit_player(id):
    """Labot spēlētāja datus"""
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

        flash('Spēlētājs atjaunināts veiksmīgi!', 'success')
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
        flash('Spēlētājs nav atrasts!', 'error')
        return redirect(url_for('admin_players'))

    return render_template('edit_player.html', player=player, teams=teams_list)

@app.route('/admin/players/delete/<int:id>', methods=['POST'])
def delete_player(id):
    """Dzēst spēlētāju"""
    conn = get_db_connection()
    conn.execute('DELETE FROM players WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Spēlētājs izdzēsts veiksmīgi!', 'success')
    return redirect(url_for('admin_players'))

@app.route('/schedule')
def schedule():
    """Spēļu kalendāra lapa"""
    conn = get_db_connection()

    completed_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'completed'
        ORDER BY g.date DESC, g.time DESC
    ''').fetchall()

    scheduled_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
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
    """Lapa par projektu"""
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)