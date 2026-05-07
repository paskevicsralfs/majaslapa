from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'evl-secret-key-2024'
DATABASE = 'volleyball.db'

def get_db_connection():
    """Izveido savienojumu ar datubāzi"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# LIETOTĀJU SADAĻA
# ==========================================

@app.route('/')
def index():
    """Sākumlapa - turnīra tabula un jaunākās spēles"""
    conn = get_db_connection()
    
    # 1. Turnīra tabula
    teams = conn.execute('SELECT * FROM teams').fetchall()
    standings = []
    for team in teams:
        t = dict(team)
        total_sets = t['sets_won'] + t['sets_lost']
        t['win_percentage'] = (t['sets_won'] / total_sets * 100) if total_sets > 0 else 0
        standings.append(t)

    standings = sorted(standings, key=lambda x: (x['points'], x['win_percentage']), reverse=True)

    # 2. Pēdējās spēles
    recent_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'completed'
        ORDER BY g.date DESC, g.time DESC LIMIT 3
    ''').fetchall()

    # 3. Nākamās spēles
    upcoming_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'scheduled'
        ORDER BY g.date ASC, g.time ASC LIMIT 3
    ''').fetchall()

    conn.close()
    return render_template('index.html', standings=standings, recent_games=recent_games, upcoming_games=upcoming_games)

@app.route('/teams')
def teams():
    """Komandu saraksts"""
    conn = get_db_connection()
    teams_list = conn.execute('SELECT * FROM teams ORDER BY points DESC, sets_won DESC').fetchall()
    teams_with_counts = []
    for team in teams_list:
        player_count = conn.execute('SELECT COUNT(*) FROM players WHERE team_id = ?', (team['id'],)).fetchone()[0]
        teams_with_counts.append({'team': team, 'player_count': player_count})
    conn.close()
    return render_template('teams.html', teams_data=teams_with_counts)

@app.route('/players')
def players():
    """Spēlētāju saraksts ar filtru un punktiem"""
    conn = get_db_connection()
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    team_filter = request.args.get('team', '')
    
    # Svarīgi: Izmantojam total_points, kas ir tavā DB
    query = '''
        SELECT p.*, t.name as team_name, IFNULL(ps.total_points, 0) as points
        FROM players p
        JOIN teams t ON p.team_id = t.id
        LEFT JOIN player_stats ps ON p.id = ps.player_id
    '''
    
    if team_filter:
        players_list = conn.execute(query + ' WHERE t.id = ? ORDER BY p.last_name', (team_filter,)).fetchall()
    else:
        players_list = conn.execute(query + ' ORDER BY p.last_name').fetchall()
        
    conn.close()
    return render_template('players.html', players=players_list, teams=teams_list, selected_team=team_filter)

@app.route('/schedule')
def schedule():
    """Pilns spēļu grafiks"""
    conn = get_db_connection()
    completed_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'completed' ORDER BY g.date DESC, g.time DESC
    ''').fetchall()
    scheduled_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'scheduled' ORDER BY g.date ASC, g.time ASC
    ''').fetchall()
    conn.close()
    return render_template('schedule.html', completed_games=completed_games, scheduled_games=scheduled_games)

# ==========================================
# ADMIN SADAĻA
# ==========================================

@app.route('/admin/players')
def admin_players():
    """Spēlētāju pārvaldības lapa"""
    conn = get_db_connection()
    players_list = conn.execute('''
        SELECT p.*, t.name as team_name, IFNULL(ps.total_points, 0) as points
        FROM players p
        JOIN teams t ON p.team_id = t.id
        LEFT JOIN player_stats ps ON p.id = ps.player_id
        ORDER BY p.last_name
    ''').fetchall()
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    conn.close()
    return render_template('admin_players.html', players=players_list, teams=teams_list)

@app.route('/admin/players/add', methods=['POST'])
def add_player():
    """Pievienot jaunu spēlētāju"""
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    position = request.form.get('position')
    team_id = request.form.get('team_id')
    phone = request.form.get('phone', '')
    points = request.form.get('points', 0)

    if not first_name or not last_name:
        flash('Vārds un uzvārds ir obligāti!', 'error')
        return redirect(url_for('admin_players'))

    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO players (first_name, last_name, position, team_id, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', (first_name, last_name, position, team_id, phone))
        
        new_player_id = cursor.lastrowid
        
        # Pievieno punktus statistikā
        conn.execute('INSERT INTO player_stats (player_id, total_points) VALUES (?, ?)', 
                     (new_player_id, points))
        
        conn.commit()
        flash('Spēlētājs pievienots veiksmīgi!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Kļūda: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_players'))

@app.route('/admin/players/edit/<int:id>', methods=['GET', 'POST'])
def edit_player(id):
    """Rediģēt spēlētāju un viņa punktus"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        position = request.form.get('position')
        team_id = request.form.get('team_id')
        phone = request.form.get('phone', '')
        points = request.form.get('points', 0)

        try:
            # 1. Atjaunina pamata datus
            conn.execute('''
                UPDATE players SET first_name=?, last_name=?, position=?, team_id=?, phone=?
                WHERE id=?
            ''', (first_name, last_name, position, team_id, phone, id))

            # 2. Atjaunina punktus (izmantojot UPSERT loģiku)
            conn.execute('''
                INSERT INTO player_stats (player_id, total_points) VALUES (?, ?)
                ON CONFLICT(player_id) DO UPDATE SET total_points = excluded.total_points
            ''', (id, points))

            conn.commit()
            flash('Spēlētāja dati atjaunināti!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Kļūda saglabājot: {str(e)}', 'error')
        finally:
            conn.close()
        return redirect(url_for('admin_players'))
    
    # GET: Ielādējam datus formai
    player = conn.execute('''
        SELECT p.*, IFNULL(ps.total_points, 0) as points 
        FROM players p 
        LEFT JOIN player_stats ps ON p.id = ps.player_id 
        WHERE p.id = ?
    ''', (id,)).fetchone()
    
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    conn.close()
    
    if not player:
        flash('Spēlētājs nav atrasts!', 'error')
        return redirect(url_for('admin_players'))

    return render_template('edit_player.html', player=player, teams=teams_list)

@app.route('/admin/players/delete/<int:id>', methods=['POST'])
def delete_player(id):
    """Izdzēst spēlētāju"""
    conn = get_db_connection()
    try:
        # Dzēšam gan no statistikas, gan no spēlētājiem
        conn.execute('DELETE FROM player_stats WHERE player_id = ?', (id,))
        conn.execute('DELETE FROM players WHERE id = ?', (id,))
        conn.commit()
        flash('Spēlētājs izdzēsts!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Kļūda dzēšot: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_players'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)