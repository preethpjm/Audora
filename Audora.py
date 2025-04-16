import streamlit as st
import json
import requests
import google.generativeai as genai
from google.generativeai.types import generation_types
import re

# --- API Keys ---
genai.configure(api_key="AIzaSyC-YcoknhndO6EeYtuKTEPThksrM4iwwPk")
model = genai.GenerativeModel("gemini-1.5-pro-latest")
YOUTUBE_API_KEY = "AIzaSyCztcIa6XNyWW6fmaWAk-r3nirx_A1P9dM"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
video_cache = {}

# --- Helper Functions ---
def get_ai_recommendation(emotion, responses):
    needs_therapy = responses["mood_level"] <= 4
    prompt = f"""
    The user is feeling {emotion} and has provided the following responses: {responses}.

    **Music Recommendations:**
    Find **10** real and existing songs that match their mood and favorite artists.
    Ensure the recommendations are **actual, released songs** and not hypothetical titles.
    If the artist is less well known, or the genre is "Other", prioritize finding songs that are known to exist.
    For each song, provide a **short, one-sentence description** explaining why it might suit the user's mood.
    Provide the songs in the following JSON format:
    [
        {{"title": "Song Title", "artist": "Artist Name", "description": "Short description of the song's vibe"}},
        // ... (up to 10 songs)
    ]

    {'**Therapy Recommendations:** Provide 5 meaningful therapy exercises, mindfulness activities, or coping techniques for the user in the following JSON format:' if needs_therapy else ''}
    {'For each tip, provide a concise, uppercase heading followed by a colon and then the description. Example: [{"tip": "BREATHING EXERCISE: Take slow, deep breaths..."}]'}
    {'[{"tip": "Tip Description"}, {"tip": "Tip Description"}, {"tip": "Tip Description"}, {"tip": "Tip Description"}, {"tip": "Tip Description"}]' if needs_therapy else ''}

    Return ONLY the JSON objects, nothing else.
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        json_matches = re.findall(r"\[.*?\]", text, re.DOTALL)
        songs_data = []
        therapy_recommendations = []
        if json_matches:
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        if data and "title" in data[0] and "artist" in data[0] and "description" in data[0]:
                            songs_data = data[:10]
                        elif data and "tip" in data[0]:
                            therapy_recommendations = [item["tip"] for item in data if "tip" in item][:5]
                except json.JSONDecodeError as e:
                    print(f"JSON Decode Error: {e}, text: {json_str}")
        return therapy_recommendations, songs_data
    except Exception as e:
        print(f"Error in get_ai_recommendation: {e}")
        return [], []

def fetch_youtube_music_data(song_data):
    music_tiles = []
    for song_info in song_data:
        song_title = song_info['title']
        artist = song_info['artist']
        description = song_info['description']
        cache_key = f"{song_title} - {artist}"
        if cache_key in video_cache:
            cached_tile = video_cache[cache_key].copy()
            cached_tile['description'] = description
            music_tiles.append(cached_tile)
            continue
        params = {
            "part": "snippet",
            "q": f"{song_title} {artist} official music audio",
            "type": "video",
            "key": YOUTUBE_API_KEY,
            "maxResults": 1,
        }
        try:
            response = requests.get(YOUTUBE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                video = data["items"][0]
                video_id = video["id"]["videoId"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                thumbnails = video["snippet"]["thumbnails"]
                thumbnail_url = thumbnails.get("maxres", thumbnails.get("high", thumbnails.get("default")))["url"]
                music_tile = {
                    "title": song_title,
                    "artist": artist,
                    "thumbnail": thumbnail_url,
                    "link": video_url,
                    "description": description,
                }
                music_tiles.append(music_tile)
                video_cache[cache_key] = music_tile
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching YouTube data for {song_title}: {e}")
        except json.JSONDecodeError as e:
            st.error(f"Error decoding JSON for {song_title}: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
    return music_tiles


# --- Styling ---
st.markdown("""
<style>
    /* Main app styling */
    .main-title {
        text-align: center;
    }
    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #878787;
        margin-bottom: 30px;
    }

    /* Therapy card carousel styling */
    .carousel-container {
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 30px 0;
    }

    .arrow-button-container {
        display: flex;
        align-items: center; /* Vertically align items */
        justify-content: center;
        height: 100%; /* Make container take full height of the row */
    }

    .arrow-button {
        background-color: transparent;
        color: #df678c;
        border: none;
        font-size: 40px;
        cursor: pointer;
        padding: 0 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 60px;
        width: 60px;
        border-radius: 50%;
        transition: background-color 0.3s;
    }

    .arrow-button:hover {
        background-color: rgba(223, 103, 140, 0.1);
    }

    .therapy-card-container {
        display: flex;
        justify-content: center; /* Center the card horizontally */
        width: 100%;
    }

    .therapy-card {
        background-color: #1e2129;
        border-radius: 15px;
        padding: 25px 20px 20px 20px;
        width: 300px;
        height: 250px;
        position: relative;
        margin: 0 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }

    .card-number {
        color: #df678c; /* Pink color */
        font-size: 60px; /* Bigger size */
        font-weight: bold; /* Bolder text */
        position: absolute;
        top: 10px;
        left: 20px;
        line-height: 1;
    }

    .card-title {
        color: #ffffff;
        font-size: 16px; /* Adjust title font size */
        text-transform: uppercase; /* Ensure heading is uppercase */
        margin-top: 50px; /* Adjust margin to accommodate card number */
        margin-bottom: 5px; /* Space between heading and content */
    }

    .card-content {
        color: #cccccc;
        font-size: 14px;
        line-height: 1.5;
    }

    /* Music recommendation styling */
    .music-container {
        background-color: #1e2129;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        display: flex;
        align-items: center; /* Vertically align items in the center */
    }

    .music-thumbnail {
        width: 150px; /* Fixed width */
        height: auto; /* Adjust height to maintain aspect ratio */
        max-height: 100px; /* Limit maximum height of the thumbnail */
        border-radius: 5px;
        object-fit: contain; /* Ensures the entire image fits within the container */
        margin-right: 15px;
        border: 1px solid #d3d3d3; /* Grey border */
    }

    .music-info {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: center; /* Center text vertically */
        height: auto;
    }

    .music-title {
        color: #ffffff;
        font-size: 18px;
        font-weight: bold;
        margin-top: 0;
        margin-bottom: 0px; /* Reduced bottom margin */
    }

    .music-artist {
        color: #878787;
        font-size: 14px;
        margin-top: 1px; /* Reduced top margin */
        margin-bottom: 1px; /* Reduced bottom margin */
    }

    .music-description {
        color: #cccccc;
        font-size: 12px;
        margin-top: 3px; /* Reduced top margin */
        margin-bottom: 4px; /* Reduced bottom margin */
    }

    .music-button {
        background-color: #df678c;
        color: white !important; /* Override link color */
        padding: 8px 16px; /* Restore original padding */
        border: none;
        border-radius: 5px;
        cursor: pointer;
        text-decoration: none !important; /* Remove underline */
        display: inline-block;
        font-size: 14px;
        font-weight: bold; /* Make font thicker */
        font-family: 'Poppins', sans-serif; /* Example of using Poppins if available */
        width: fit-content; /* Button width fits content */
        margin-top: 6px; /* Adjusted top margin for the button */
    }

    /* Therapy card styling */
    .therapy-card .card-title {
        font-size: 16px; /* Adjust title font size */
        text-transform: uppercase; /* Ensure heading is uppercase */
        margin-bottom: 5px; /* Space between heading and content */
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for carousel
if 'current_card_index' not in st.session_state:
    st.session_state.current_card_index = 0
if 'therapy_recommendations' not in st.session_state:
    st.session_state.therapy_recommendations = []
if 'recommended_songs_data' not in st.session_state:
    st.session_state.recommended_songs_data = []
if 'music_data' not in st.session_state:
    st.session_state.music_data = []
if 'therapy_available' not in st.session_state:
    st.session_state.therapy_available = None
if 'rerun_trigger' not in st.session_state:
    st.session_state.rerun_trigger = False

def next_card():
    if st.session_state.current_card_index < len(st.session_state.therapy_recommendations) - 1:
        st.session_state.current_card_index += 1
        st.session_state.rerun_trigger = not st.session_state.rerun_trigger # Trigger a rerun

def prev_card():
    if st.session_state.current_card_index > 0:
        st.session_state.current_card_index -= 1
        st.session_state.rerun_trigger = not st.session_state.rerun_trigger # Trigger a rerun

# Display the PNG image as the main title
st.image("C:\\Users\\Preeth\\Downloads\\Audora\\Title.png", use_container_width=False, width=250, output_format="PNG")

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
user_responses["mood_level"] = int(user_responses["mood_level"])

if st.button("Get Recommendations"):
    needs_therapy = user_responses["mood_level"] <= 4
    print(f"needs_therapy value: {needs_therapy}")  # Debugging

    ai_therapy, recommended_songs_data = get_ai_recommendation("unknown", user_responses)

    # Store therapy recommendations and music data in session state
    st.session_state.therapy_recommendations = ai_therapy
    st.session_state.recommended_songs_data = recommended_songs_data
    st.session_state.music_data = [] # Clear previous music data
    st.session_state.therapy_available = len(ai_therapy) > 0 # Set therapy availability

    # Reset card index when getting new recommendations
    st.session_state.current_card_index = 0
    st.session_state.rerun_trigger = not st.session_state.rerun_trigger # Trigger a rerun

# Fetch and display music recommendations (only if new recommendations are available)
if st.session_state.recommended_songs_data and not st.session_state.music_data:
    st.session_state.music_data = fetch_youtube_music_data(st.session_state.recommended_songs_data)

# This line will force a rerun whenever st.session_state.rerun_trigger changes
rerun = st.session_state.rerun_trigger

# Display therapy recommendations as a carousel
if st.session_state.therapy_available is True:
    st.subheader("AI Therapist Suggestions:")

    col_left, col_center, col_right = st.columns([1, 3, 1])

    with col_left:
        st.markdown('<div class="arrow-button-container" style="height: 250px; display: flex; align-items: center; justify-content: center;">', unsafe_allow_html=True)
        st.button("←", key="prev_button", on_click=prev_card, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_center:
        if st.session_state.therapy_recommendations:
            current_index = st.session_state.current_card_index
            current_tip = st.session_state.therapy_recommendations[current_index]

            if ":" in current_tip:
                title, content = current_tip.split(":", 1)
                card_title = title.strip()
                card_content = content.strip()
            else:
                card_title = "Suggestion"
                card_content = current_tip.strip()

            st.markdown(f"""
            <div class="therapy-card-container">
                <div class="therapy-card">
                    <div class="card-number">{current_index + 1}.</div>
                    <div class="card-title">{card_title}</div>
                    <div class="card-content">{card_content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="text-align: center; margin-top: 10px; color: #878787;">
                Card {current_index + 1} of {len(st.session_state.therapy_recommendations)}
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="arrow-button-container" style="height: 250px; display: flex; align-items: center; justify-content: center;">', unsafe_allow_html=True)
        st.button("→", key="next_button", on_click=next_card, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
elif st.session_state.therapy_available is False:
    st.write("AI Therapist suggestions are not available.")
elif st.session_state.therapy_available is None:
    pass # Do not show the message initially

# Display music recommendations
if st.session_state.music_data:
    st.subheader("Recommended Songs:")
    for i, tile in enumerate(st.session_state.music_data):
        st.markdown(f"""
        <div class="music-container">
            <img src="{tile['thumbnail']}" class="music-thumbnail">
            <div class="music-info">
                <h3 class="music-title">{tile['title']}</h3>
                <p class="music-artist">{tile['artist']}</p>
                <p class="music-description">{tile['description']}</p>
                <a href="{tile['link']}" target="_blank" class="music-button">Listen on YouTube</a>
            </div>
        </div>
        """, unsafe_allow_html=True)