import os
from flask import Flask, request, session, url_for, redirect, render_template
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')
scope = os.getenv('SCOPE')

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(
    client_id=client_id, 
    client_secret=client_secret, 
    redirect_uri=redirect_uri, 
    scope=scope, 
    cache_handler=cache_handler,
    show_dialog=True
)

sp = Spotify(auth_manager=sp_oauth)

@app.route('/')
def home():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('choose_playlists'))

@app.route('/callback')
def callback():
    token_info = sp_oauth.get_access_token(request.args['code'])
    session['token_info'] = token_info
    return redirect(url_for('choose_playlists'))

@app.route('/choose_playlists', methods=['GET', 'POST'])
def choose_playlists():
    if not session.get('token_info'):
        return redirect(url_for('home'))
    
    playlists = sp.current_user_playlists()
    playlists_info = [{'name': pl['name'], 'id': pl['id']} for pl in playlists['items']]

    if request.method == 'POST':
        selected_playlists = request.form.getlist('playlist')
        if len(selected_playlists) == 2:
            return redirect(url_for('find_duplicates', playlist_id1=selected_playlists[0], playlist_id2=selected_playlists[1]))
        
    return render_template('choose_playlists.html', playlists=playlists_info)

@app.route('/find_duplicates/<playlist_id1>/<playlist_id2>')
def find_duplicates(playlist_id1, playlist_id2):
    if not session.get('token_info'):
        return redirect(url_for('home'))
    
    def get_song_ids(playlist_id):
        song_ids = set()
        results = sp.playlist_tracks(playlist_id)
        
        while results:
            for song in results['items']:
                try:
                    song_id = song['track']['id']
                    song_ids.add(song_id)
                except TypeError:
                    continue

            if results['next']:
                results = sp.next(results)
            else:
                break
        return song_ids
    
    playlist1_info = sp.playlist(playlist_id1)
    playlist2_info = sp.playlist(playlist_id2)
    
    playlist1_name = playlist1_info['name']
    playlist2_name = playlist2_info['name']
      
    playlist1_song_ids = get_song_ids(playlist_id1)
    playlist2_song_ids = get_song_ids(playlist_id2)

    duplicate_song_ids = playlist1_song_ids & playlist2_song_ids

    duplicate_songs = []
    for track_id in duplicate_song_ids:
        track = sp.track(track_id)
        duplicate_songs.append(f"{track['name']} by {track['artists'][0]['name']}")

    return render_template('find_duplicates.html', 
                           playlist1_name=playlist1_name,
                           playlist2_name=playlist2_name,
                           duplicate_songs=duplicate_songs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)


