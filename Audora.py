import streamlit as st
import json
import requests
import google.generativeai as genai

# Set up Google Gemini API
genai.configure(api_key="AIzaSyC-YcoknhndO6EeYtuKTEPThksrM4iwwPk")  # Replace with actual API Key
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# YouTube Music API Key (Replace with your actual API Key)
YOUTUBE_API_KEY = "AIzaSyAICAlFoXnLGbdQn1oZWYozn8QEMUg8edU"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"


# Function to get AI therapist advice and real song recommendations
def get_ai_recommendation(emotion, responses):
    needs_therapy = responses["mood_level"] <= 4

    song_prompt = f"""
    The user prefers '{responses['favorite_genre']}' music.
    They like the following artists: {responses['favorite_artists']}.
    Generate exactly **10 real song recommendations** in the following format:
    **Song Title - Artist Name**
    Make sure:
    - The songs exist in real streaming platforms.
    - If no exact artist match is found, suggest similar songs based on genre & mood.
    - Avoid generic explanations—list only song titles and artists.
    - Ensure the songs fit the user's detected mood and coping mechanisms.
    Return ONLY the list of songs, nothing else.
    """

    therapy_prompt = f"""
    The user has provided these responses: {responses}.
    Provide **5 actionable therapy suggestions** based on their mood and extra responses.
    Focus on **real, useful techniques** (e.g., mindfulness, exercise, journaling).
    """

    song_response = model.generate_content(song_prompt).text.strip()
    therapy_response = model.generate_content(therapy_prompt).text.strip() if needs_therapy else ""

    songs = [line.strip() for line in song_response.split("\n") if "-" in line][:10]

    therapy_recommendations = [
        line.strip() for line in therapy_response.split("\n") if line.strip() and not any(c.isdigit() for c in line)
    ][:5] if needs_therapy else []

    return therapy_recommendations, songs

# Function to fetch YouTube Music details (thumbnail & link)
def fetch_youtube_music_data(song_list):
    music_tiles = []

    for song in song_list:
        song_title, artist = song.split(" - ")

        params = {
            "part": "snippet",
            "q": f"{song_title} {artist} official audio",
            "type": "video",
            "key": YOUTUBE_API_KEY,
            "maxResults": 1
        }

        response = requests.get(YOUTUBE_API_URL, params=params)
        data = response.json()

        if "items" in data and len(data["items"]) > 0:
            video = data["items"][0]
            video_id = video["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            thumbnails = video["snippet"]["thumbnails"]
            thumbnail_url = thumbnails.get("maxres", thumbnails.get("high", thumbnails.get("default")))["url"]

            music_tiles.append({
                "title": song_title,
                "artist": artist,
                "thumbnail": thumbnail_url,
                "link": video_url
            })

    return music_tiles

# Streamlit UI
st.title("Emotional Music Therapy & Recommendations")

# Questionnaire
st.header("Answer a few questions:")
mood_level = st.slider("On a scale of 1-10, how happy are you?", 1, 10, 5)
mood_swings = st.radio("How often do you experience mood swings?", ["Rarely", "Sometimes", "Often", "Always"])
activity = st.text_input("What do you do when feeling low?")
favorite_genre = st.selectbox("Favorite music genre?", ["Pop", "Rock", "Hip-hop", "Classical", "Electronic", "Jazz", "Country", "Other"])
favorite_artists = st.text_input("List your favorite music artists (comma-separated):")

extra_responses = {}
if mood_level <= 4:
    st.write("\nYou seem to be struggling. Please answer a few more questions.")
    extra_responses["stress_cause"] = st.text_input("What has been bothering you the most lately?")
    extra_responses["coping_methods"] = st.text_input("How do you usually handle stress?")
    sleep_quality = st.radio("How well have you been sleeping?", ["Good", "Average", "Poor"])
    extra_responses["sleep_quality"] = sleep_quality

user_responses = {
    "mood_level": mood_level,
    "mood_swings": mood_swings,
    "activity": activity,
    "favorite_genre": favorite_genre,
    "favorite_artists": [artist.strip() for artist in favorite_artists.split(",")],
    "extra_info": extra_responses
}

if st.button("Get Recommendations"):
    # Get AI therapist recommendations (if needed) and real song list
    ai_therapy, recommended_songs = get_ai_recommendation("unknown", user_responses) #Emotion is unknown as we removed webcam.

    # Print therapist advice (if needed)
    if ai_therapy:
        st.subheader("AI Therapist Suggestions:")
        for i, tip in enumerate(ai_therapy, 1):
            st.write(f"{i}. {tip}")

    # Print & structure songs properly
    st.subheader("Recommended Songs:")
    for i, song in enumerate(recommended_songs, 1):
        st.write(f"{i}. {song}")

    # Fetch YouTube Music details (album art & link)
    music_data = fetch_youtube_music_data(recommended_songs)

    # Print formatted music tiles
    st.subheader("Music Tiles:")
    for tile in music_data:
        st.write(f"🎵 {tile['title']} - {tile['artist']}")
        st.markdown(f"🔗 [Listen on YouTube]({tile['link']})")
        st.image(tile['thumbnail'], caption="Album Art", use_column_width=True)

    # JSON output for UI integration
    st.write("Music Data (Structured for UI/API):", json.dumps(music_data, indent=2))

# Function to get AI therapist advice and real song recommendations
def get_ai_recommendation(emotion, responses):
    needs_therapy = responses["mood_level"] <= 4

    song_prompt = f"""
    The user prefers '{responses['favorite_genre']}' music.
    They like the following artists: {responses['favorite_artists']}.
    Generate exactly **10 real song recommendations** in the following format:
    **Song Title - Artist Name**
    Make sure:
    - The songs exist in real streaming platforms.
    - If no exact artist match is found, suggest similar songs based on genre & mood.
    - Avoid generic explanations—list only song titles and artists.
    - Ensure the songs fit the user's detected mood and coping mechanisms.
    Return ONLY the list of songs, nothing else.
    """

    therapy_prompt = f"""
    The user has provided these responses: {responses}.
    Provide **5 actionable therapy suggestions** based on their mood and extra responses.
    Focus on **real, useful techniques** (e.g., mindfulness, exercise, journaling).
    """

    song_response = model.generate_content(song_prompt).text.strip()
    therapy_response = model.generate_content(therapy_prompt).text.strip() if needs_therapy else ""

    songs = [line.strip() for line in song_response.split("\n") if "-" in line][:10]

    therapy_recommendations = [
        line.strip() for line in therapy_response.split("\n") if line.strip() and not any(c.isdigit() for c in line)
    ][:5] if needs_therapy else []

    return therapy_recommendations, songs

# Function to fetch YouTube Music details (thumbnail & link)
def fetch_youtube_music_data(song_list):
    music_tiles = []

    for song in song_list:
        song_title, artist = song.split(" - ")

        params = {
            "part": "snippet",
            "q": f"{song_title} {artist} official audio",
            "type": "video",
            "key": YOUTUBE_API_KEY,
            "maxResults": 1
        }

        response = requests.get(YOUTUBE_API_URL, params=params)
        data = response.json()

        if "items" in data and len(data["items"]) > 0:
            video = data["items"][0]
            video_id = video["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            thumbnails = video["snippet"]["thumbnails"]
            thumbnail_url = thumbnails.get("maxres", thumbnails.get("high", thumbnails.get("default")))["url"]

            music_tiles.append({
                "title": song_title,
                "artist": artist,
                "thumbnail": thumbnail_url,
                "link": video_url
            })

    return music_tiles