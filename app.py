from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'evl-secret-key-2024'
DATABASE = 'volleyball.db'

# Funkcija, kas izveido savienojumu ar SQLite datubāzi
def get_db_connection():
    """Izveido savienojumu ar datubāzi"""
    # Atver savienojumu ar failu, kas definēts mainīgajā DATABASE
    conn = sqlite3.connect(DATABASE)
    # Norāda, ka rezultātus gribam saņemt kā vārdnīcas tipa objektus (pieeja pēc kolonnu nosaukumiem)
    conn.row_factory = sqlite3.Row
    # Atgriež izveidoto savienojumu
    return conn

# Galvenā lapa (maršruts '/')
@app.route('/')
def index():
    """Sākumlapa - turnīra tabula un spēles"""
    # Iegūstam DB savienojumu
    conn = get_db_connection()
    
    # 1. Atlasām visas komandas no tabulas 'teams'
    teams = conn.execute('SELECT * FROM teams').fetchall()

    standings = []
    # Cikls, lai apstrādātu katru komandu un aprēķinātu papildus statistiku
    for team in teams:
        t = dict(team) # Pārvēršam rindu par vārdnīcu, lai tajā varētu rakstīt
        total_sets = t['sets_won'] + t['sets_lost'] # Saskaitām kopējo setu skaitu
        # Aprēķinām uzvarēto setu procentu (izvairāmies no dalīšanas ar nulli)
        t['win_percentage'] = (t['sets_won'] / total_sets * 100) if total_sets > 0 else 0
        standings.append(t)

    # Sakārtojam sarakstu: vispirms pēc punktiem, tad pēc procenta (reverse=True nozīmē dilstošā secībā)
    standings = sorted(standings, key=lambda x: (x['points'], x['win_percentage']), reverse=True)

    # 2. Atlasām 3 pēdējās pabeigtās spēles, pievienojot komandu nosaukumus ar JOIN
    recent_games = conn.execute('''
        SELECT g.*, 
                ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'completed'
        ORDER BY g.date DESC, g.time DESC
        LIMIT 3
    ''').fetchall()

    # 3. Atlasām 3 tuvākās plānotās spēles
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

    # Aizveram DB savienojumu
    conn.close()

    # Nosūtām visus iegūtos datus uz HTML šablonu
    return render_template('index.html', standings=standings,recent_games=recent_games,upcoming_games=upcoming_games)

# Komandu saraksta lapa
@app.route('/teams')
def teams():
    """Komandu lapa ar statistiku"""
    conn = get_db_connection()
    # Iegūstam visas komandas, sakārtotas pēc punktiem
    teams_list = conn.execute('''
        SELECT * FROM teams
        ORDER BY points DESC, sets_won DESC
    ''').fetchall()

    # Izveidojam sarakstu, kurā pievienosim arī spēlētāju skaitu
    teams_with_counts = []
    for team in teams_list:
        # Katrai komandai saskaitām, cik spēlētāju tai ir piesaistīti
        player_count = conn.execute(
            'SELECT COUNT(*) FROM players WHERE team_id = ?',
            (team['id'],)
        ).fetchone()[0]
        # Pievienojam datus jaunā sarakstā
        teams_with_counts.append({
            'team': team,
            'player_count': player_count
        })

    conn.close()
    return render_template('teams.html', teams_data=teams_with_counts)

# Spēlētāju lapa ar filtrēšanas iespēju
@app.route('/players')
def players():
    """Spēlētāju saraksts ar filtrēšanu"""
    conn = get_db_connection()

    # Iegūstam visas komandas filtru sarakstam (nolaižamajai izvēlnei)
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    # Mēģinām iegūt izvēlētās komandas ID no URL parametriem (?team=ID)
    team_filter = request.args.get('team', '')

    if team_filter:
        # Ja filtrs ir aktīvs, atlasām spēlētājus tikai no konkrētās komandas
        players_list = conn.execute('''
            SELECT p.*, t.name as team_name
            FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE t.id = ?
            ORDER BY p.last_name
        ''', (team_filter,)).fetchall()
    else:
        # Ja filtra nav, atlasām visus spēlētājus
        players_list = conn.execute('''
            SELECT p.*, t.name as team_name
            FROM players p
            JOIN teams t ON p.team_id = t.id
            ORDER BY p.last_name
        ''').fetchall()

    conn.close()
    return render_template('players.html',players=players_list,teams=teams_list,selected_team=team_filter)

# --- ADMIN / CRUD SEKCIJA (Datu pievienošana, labošana, dzēšana) ---

# Admin sākumlapa spēlētājiem
@app.route('/admin/players')
def admin_players():
    """Admin lapa - spēlētāju pārvaldība"""
    conn = get_db_connection()
    # Atlasām spēlētājus un visas komandas formām
    players_list = conn.execute('''
        SELECT p.*, t.name as team_name
        FROM players p
        JOIN teams t ON p.team_id = t.id
        ORDER BY p.last_name
    ''').fetchall()
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    conn.close()
    return render_template('admin_players.html',players=players_list,teams=teams_list)

# Jauna spēlētāja pievienošana (tikai caur POST metodi)
@app.route('/admin/players/add', methods=['POST'])
def add_player():
    """Pievienot jaunu spēlētāju"""
    # Nolasa datus no iesūtītās formas
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    position = request.form['position']
    team_id = request.form['team_id']
    phone = request.form.get('phone', '') # .get izmanto, ja lauks var būt tukšs

    conn = get_db_connection()
    # Ievieto jaunu ierakstu datubāzē
    conn.execute('''
        INSERT INTO players (first_name, last_name, position, team_id, phone)
        VALUES (?, ?, ?, ?, ?)
    ''', (first_name, last_name, position, team_id, phone))
    conn.commit() # Saglabā izmaiņas datubāzē
    conn.close()

    flash('Spēlētājs pievienots veiksmīgi!', 'success') # Ziņojums lietotājam
    return redirect(url_for('admin_players')) # Pāradresē atpakaļ uz sarakstu

# Spēlētāja labošana
@app.route('/admin/players/edit/<int:id>', methods=['GET', 'POST'])
def edit_player(id):
    """Labot spēlētāja datus"""
    conn = get_db_connection()

    if request.method == 'POST':
        # Ja forma iesūtīta (POST), atjaunina datus DB
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

    # Ja metode ir GET, ielādē spēlētāja datus, lai tos parādītu formā
    player = conn.execute('''
        SELECT p.*, t.name as team_name
        FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE p.id = ?
    ''', (id,)).fetchone()
    teams_list = conn.execute('SELECT * FROM teams ORDER BY name').fetchall()
    conn.close()

    # Ja spēlētājs ar tādu ID neeksistē
    if player is None:
        flash('Spēlētājs nav atrasts!', 'error')
        return redirect(url_for('admin_players'))

    return render_template('edit_player.html', player=player, teams=teams_list)

# Spēlētāja dzēšana
@app.route('/admin/players/delete/<int:id>', methods=['POST'])
def delete_player(id):
    """Dzēst spēlētāju"""
    conn = get_db_connection()
    # Izpilda dzēšanas komandu pēc ID
    conn.execute('DELETE FROM players WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Spēlētājs izdzēsts veiksmīgi!', 'success')
    return redirect(url_for('admin_players'))

# Spēļu kalendāra lapa
@app.route('/schedule')
def schedule():
    """Spēļu kalendāra lapa"""
    conn = get_db_connection()

    # Iegūstam visas pabeigtās spēles (sakārtotas no jaunākajām)
    completed_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'completed'
        ORDER BY g.date DESC, g.time DESC
    ''').fetchall()

    # Iegūstam visas gaidāmās spēles (sakārtotas pēc tuvākā datuma/laika)
    scheduled_games = conn.execute('''
        SELECT g.*, ht.name as home_team, at.name as away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.status = 'scheduled'
        ORDER BY g.date ASC, g.time ASC
    ''').fetchall()

    conn.close()
    return render_template('schedule.html',completed_games=completed_games,scheduled_games=scheduled_games)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)