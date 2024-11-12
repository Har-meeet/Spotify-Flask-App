import requests
import time

def playlist_generator(track_ids, playlist_length, access_token):
        
        user_track_ids = get_all_user_tracks(access_token)

        concatenated_track_ids = ''
        audio_features = []
        for id in track_ids:
            if len(concatenated_track_ids) > 2000:
                audio_features += get_audio_features(access_token, concatenated_track_ids[:-1])['audio_features']
                concatenated_track_ids = ''
            concatenated_track_ids += id + ','

        audio_features += get_audio_features(access_token, concatenated_track_ids[:-1])['audio_features']

        avg_features = compute_playlist_features(audio_features)

        unique_recommendations = []
        recommendation_ids = set()

        while len(unique_recommendations) < playlist_length:
            time.sleep(0.5)  # Avoid rate limiting
            i = 0
            track_ids = track_ids[(5 * i) % len(track_ids) : (5 * (i + 1)) % len(track_ids)]
            seed_tracks = ",".join(track_ids[5 * i: 5 * (i + 1)])

            recommendations_url = "https://api.spotify.com/v1/recommendations"
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            params = {
                "seed_tracks": seed_tracks,
                "target_danceability": adjust_audio_features(avg_features["danceability"], i),
                "target_energy": adjust_audio_features(avg_features["energy"], i),
                "target_valence": adjust_audio_features(avg_features["valence"], i),
                "target_acousticness": adjust_audio_features(avg_features["acousticness"], i),
                "target_instrumentalness": adjust_audio_features(avg_features["instrumentalness"], i),
                "target_liveness": adjust_audio_features(avg_features["liveness"], i),
                "target_loudness": avg_features["loudness"],
                "target_speechiness": adjust_audio_features(avg_features["speechiness"], i),
                "target_tempo": avg_features["tempo"],
                "limit": 100  
            }
            response = requests.get(recommendations_url, headers=headers, params=params)

            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 0))
                print(f"Rate limit exceeded. Retrying after {retry_after + 1} seconds...")
                time.sleep(retry_after + 1)
                continue 

            response.raise_for_status()
            recommendations = response.json()

            for track in recommendations['tracks']:
                if track['id'] not in user_track_ids and track['id'] not in recommendation_ids:
                    unique_recommendations.append(track)
                    recommendation_ids.add(track['id'])

                if len(unique_recommendations) >= playlist_length:
                    break

            i += 1

        generated_tracks = [
            {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else ''
            }
            for track in unique_recommendations
        ]

        return generated_tracks

def get_user_saved_tracks(access_token): # Get all liked songs
    saved_tracks = []
    url = "https://api.spotify.com/v1/me/tracks"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        saved_tracks.extend(data['items'])
        url = data.get('next')
    liked_track_ids = {item['track']['id'] for item in saved_tracks if item['track']}
    return liked_track_ids

def get_user_playlists(access_token):
    playlists = []
    url = "https://api.spotify.com/v1/me/playlists"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        playlists.extend(data['items'])
        url = data.get('next')
    return playlists

def get_all_playlist_tracks(access_token, playlists):
    all_track_ids = set()
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    for playlist in playlists:
        playlist_id = playlist['id']
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            all_track_ids.update(
                item['track']['id'] for item in data['items'] if item['track']
            )
            url = data.get('next')
    return all_track_ids

def get_all_user_tracks(access_token):
    liked_track_ids = get_user_saved_tracks(access_token)

    playlists = get_user_playlists(access_token)

    playlist_track_ids = get_all_playlist_tracks(access_token, playlists)

    all_unique_track_ids = list(liked_track_ids.union(playlist_track_ids))
    return all_unique_track_ids

def get_audio_features(access_token, track_ids):
    url = f"https://api.spotify.com/v1/audio-features"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "ids": track_ids
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


# Compute averages from audio features
def compute_playlist_features(playlist_features):
    features = {
        "danceability": 0, "energy": 0, "valence": 0, 
        "acousticness": 0, "instrumentalness": 0, 
        "liveness": 0, "loudness": 0, "speechiness": 0, "tempo": 0
    }
    
    for track in playlist_features:
        for feature in features:
            features[feature] += track[feature]
    return {k: v / len(playlist_features) for k, v in features.items()}

def adjust_audio_features(feature, i):
    if i % 2 == 0:
        return min(feature + i * 0.01, 1)
    else:
        return max(feature - (i + 1) * 0.01, 0)