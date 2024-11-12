import requests

access_token = 'BQClNYZqB2p5tdQBUxa2Q6WwVIwdUD5ajxlKHcLsLHOUTi2gTPxL5Xt6ynYK70s-XF5UUFZd7OVZQUISZzbzrvuZqWIiI4M3JdCogzXd6j2c3sdUmI0bcYXuf5svlbrUY3BQvIXvK4UJm__fxlQ8j9CCfF1SzbaTJFtGqP_2Ual5FeDpPP5WwldA8HkKbn0vc3DJuAeGZhLq8kqqKPiz2X8BmZLH54PkJXm6CkoJQ8o7Jr4zDOrrqwwDGlmMmxFQOu1KRgZgjvcb5CsVkh4'
recommendations_url = "https://api.spotify.com/v1/recommendations"
headers = {
    "Authorization": f"Bearer {access_token}"
}
params = {
    "seed_tracks": "2BJSMvOGABRxokHKB0OI8i",  # Use first 5 tracks as seeds
    "target_energy": 0.5,
    "target_danceability": 0.5,
    "limit": 20  # Fetch a larger batch to reduce the number of API calls
}
response = requests.get(recommendations_url, headers=headers, params=params)
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 0))  # Default to 1 second if not provided
    print(f"Rate limit exceeded. Retrying after {retry_after + 1} seconds...")
