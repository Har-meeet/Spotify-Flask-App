import requests
import base64
import os
from urllib.parse import urlencode
from flask import Flask, request, redirect, render_template_string, session
from flask_session import Session
from playlist_generator import playlist_generator
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)


# Configuring session
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Spotify API credentials
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = "http://localhost:8888/callback"
SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public user-library-read"


@app.route('/')
def login():
    auth_url = "https://accounts.spotify.com/authorize"
    query_params = urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE
    })
    return redirect(f"{auth_url}?{query_params}")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = get_access_token(code)
    session['access_token'] = token_info['access_token']
    return redirect('/playlists')

@app.route('/playlists')
def playlists():
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/')
    playlists = get_user_playlists(access_token)
    if playlists and playlists['items']:
        return render_playlists(playlists['items'])
    else:
        return "No playlists found."

@app.route('/playlist/<playlist_id>')
def playlist(playlist_id):
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/')
    tracks = get_playlist_tracks(access_token, playlist_id)
    return render_tracks(tracks, playlist_id)

@app.route('/generate_playlist/<playlist_id>', methods=['GET', 'POST'])
def generate_playlist(playlist_id):
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/')

    if request.method == 'POST':
        # Get user-defined playlist length
        playlist_length = int(request.form.get('length'))

        # Get the original playlist's tracks
        tracks = get_playlist_tracks(access_token, playlist_id)
        track_ids = [item['track']['id'] for item in tracks['items'] if item['track'] and item['track']['id']]
        session['generated_tracks'] = playlist_generator(track_ids, playlist_length, access_token)

        return render_generated_playlist(session['generated_tracks'], playlist_length, playlist_id)

    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Generate Playlist</title>
        </head>
        <body>
            <h1>Generate a Playlist Based on Selected Playlist</h1>
            <form method="post">
                <label for="length">Playlist Length (25 to 100):</label>
                <input type="number" id="length" name="length" min="25" max="100" required>
                <button type="submit">Generate Playlist</button>
            </form>
            <a href='/playlists'>Back to Playlists</a>
        </body>
        </html>
    ''')

def get_access_token(code):
    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(token_url, headers=headers, data=payload)
    response.raise_for_status()
    return response.json()

def render_playlists(playlists):
    html_content = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Spotify Playlists</title>
        <style>
            .playlist-item {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }
            .playlist-item img {
                margin-right: 15px;
            }
        </style>
    </head>
    <body>
        <h1>Your Playlists</h1>
        <ul style="list-style-type: none; padding: 0;">
    """
    for playlist in playlists:
        playlist_name = playlist['name']
        playlist_id = playlist['id']
        playlist_image = playlist['images'][0]['url'] if playlist['images'] else ''
        html_content += f"<li class='playlist-item'><img src='{playlist_image}' alt='Playlist Image' width='50' height='50'> <a href='/playlist/{playlist_id}'>{playlist_name}</a></li>"
    html_content += """
        </ul>
    </body>
    </html>
    """
    return html_content

def render_tracks(tracks, playlist_id):
    track_list = []
    for item in tracks['items']:
        track = item['track']
        if not track:
            continue
        track_name = track['name'] if 'name' in track and track['name'] else 'Unknown'
        artist_name = track['artists'][0]['name'] if track['artists'] else 'Unknown'
        track_image = track['album']['images'][0]['url'] if track['album']['images'] else ''
        track_list.append((track_name, artist_name, track_image))

    html_content = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Spotify Playlist Tracks</title>
        <style>
            .track-item {{
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }}
            .track-item img {{
                margin-right: 15px;
            }}
            .button-container {{
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                align-items: center;
            }}
        </style>
    </head>
    <body>
        <div class="button-container">
            <form action="/playlists" method="get" style="display: inline;">
                <button type="submit">Back to Playlists</button>
            </form>
            <form action="/generate_playlist/{playlist_id}" method="get" style="display: inline;">
                <button type="submit">Generate Playlist</button>
            </form>
        </div>
        <h1>Tracks in Selected Playlist</h1>
        <ul style="list-style-type: none; padding: 0;">
    """
    for track_name, artist_name, track_image in track_list:
        html_content += f"<li class='track-item'><img src='{track_image}' alt='Track Image' width='50' height='50'> {track_name} by {artist_name}</li>"
    html_content += """
        </ul>
    </body>
    </html>
    """

    return html_content

def render_generated_playlist(generated_tracks, playlist_length, playlist_id):
    html_content = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Generated Playlist</title>
        <style>
            .track-item {{
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }}
            .track-item img {{
                margin-right: 15px;
            }}
        </style>
    </head>
    <body>
        <h1>Generated Playlist ({} tracks)</h1>
        <ul style="list-style-type: none; padding: 0;">
    """.format(playlist_length)
    for track in generated_tracks:
        html_content += f"<li class='track-item'><img src='{track['image_url']}' alt='Track Image' width='50' height='50'> {track['name']} by {track['artist']}</li>"
    html_content += f"""
        </ul>
        <form method="post" action="/accept_playlist">
            <input type="hidden" name="playlist_id" value="{playlist_id}">
            <button type="submit" name="accept" value="yes">Accept Playlist</button>
            <button type="submit" name="accept" value="no">Deny Playlist</button>
        </form>
    </body>
    </html>
    """
    return html_content

# Route to handle playlist acceptance and prompt for playlist name
@app.route('/accept_playlist', methods=['POST'])
def accept_playlist():
    playlist_id = request.form.get('playlist_id')
    if request.form['accept'] == 'yes':
        return redirect(f'/name_playlist/{playlist_id}')
    else:
        return redirect('/playlists')
    

# Route to name the playlist and save it to Spotify
@app.route('/name_playlist/<playlist_id>', methods=['GET', 'POST'])
def name_playlist(playlist_id):
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/')

    if request.method == 'POST':
        playlist_name = request.form.get('playlist_name')

        create_playlist_url = "https://api.spotify.com/v1/me/playlists"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": playlist_name,
            "description": "Generated playlist based on your selected tracks",
            "public": False
        }
        response = requests.post(create_playlist_url, headers=headers, json=payload)
        response.raise_for_status()
        new_playlist = response.json()
        new_playlist_id = new_playlist['id']

        generated_tracks = session.get('generated_tracks', [])
        track_uris = [f"spotify:track:{track['id']}" for track in generated_tracks]
        add_tracks_url = f"https://api.spotify.com/v1/playlists/{new_playlist_id}/tracks"
        requests.post(add_tracks_url, headers=headers, json={"uris": track_uris})

        return redirect('/playlists')

    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Name Your Playlist</title>
        </head>
        <body>
            <h1>Name Your New Playlist</h1>
            <form method="post">
                <label for="playlist_name">Playlist Name:</label>
                <input type="text" id="playlist_name" name="playlist_name" required>
                <button type="submit">Save Playlist</button>
            </form>
        </body>
        </html>
    ''')

def get_user_playlists(access_token):
    url = "https://api.spotify.com/v1/me/playlists"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_playlist_tracks(access_token, playlist_id):
    tracks = []
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        tracks.extend(data['items'])
        url = data.get('next')
    return {'items': tracks}

if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Please set your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.")
    else:
        app.run(port=8888)
