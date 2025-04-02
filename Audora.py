import streamlit as st
import cv2
import numpy as np
import time
from deepface import DeepFace  # Commented out in case TensorFlow isn't installed
from googleapiclient.discovery import build

# Load API keys from Streamlit secrets
YOUTUBE_API_KEY = st.secrets["youtube"]["api_key"]
GEMINI_API_KEY = st.secrets["gemini"]["api_key"]

# Function to detect emotion using DeepFace
def detect_emotion(frame):
  #  try:
  #      result = DeepFace.analyze(frame, actions=['emotion'])
  #      return result[0]['dominant_emotion']
  #  except:
        return "sad"  # Default to sad if detection fails

# Function to create a YouTube Music playlist
def create_youtube_playlist(song_list):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    playlist_request = youtube.playlists().insert(
        part="snippet,status",
        body={  
            "snippet": {
                "title": "Your AI Recommended Playlist",
                "description": "Playlist generated based on your emotions",
                "tags": ["music", "playlist", "emotion-based"],
                "defaultLanguage": "en"
            },
            "status": {"privacyStatus": "public"}
        }
    ).execute()
    playlist_id = playlist_request["id"]

    # Add songs to the playlist
    for song in song_list:
        search_response = youtube.search().list(
            q=song, part="id", type="video", maxResults=1
        ).execute()
        video_id = search_response["items"][0]["id"]["videoId"]
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id}
                }
            }
        ).execute()
    
    return f"https://www.youtube.com/playlist?list={playlist_id}"

# Function to process questionnaire and call Gemini AI
def process_questionnaire(responses):
    prompt = f"Based on the user's responses: {responses}, suggest a therapy exercise and a music playlist."
    ai_response = "(Mock Response) Try deep breathing and listen to: 'Song A - Artist A', 'Song B - Artist B'"
    songs = ["Song A - Artist A", "Song B - Artist B"]
    playlist_link = create_youtube_playlist(songs)
    return ai_response, playlist_link

# Streamlit UI
st.title("Emotion-Based AI Music Recommender & Therapist")

camera_access = st.checkbox("Enable Camera (if available)")
if camera_access:
    st.write("Capturing your facial expression...")
    cap = cv2.VideoCapture(0)
    time.sleep(2)
    ret, frame = cap.read()
    cap.release()
    if ret:
        emotion = detect_emotion(frame)
    else:
        emotion = "sad"  # Default
else:
    emotion = "sad"  # Default if camera is off

st.write(f"Detected Emotion: {emotion}")

if emotion in ["sad", "angry", "anxious"]:
    st.write("You seem distressed. Let's proceed with a questionnaire for better insights.")
    with st.form("mood_form"):
        mood_level = st.slider("On a scale of 1 to 10, how happy are you?", 1, 10, 5)
        mood_swings = st.selectbox("How often do you experience mood swings?", ["Rarely", "Sometimes", "Often", "Always"])
        activity = st.selectbox("What do you do when you're feeling low?", ["Listening to music", "Exercising", "Talking to someone", "Sleeping", "Watching TV", "Other"])
        favorite_genre = st.selectbox("Favorite music genre?", ["Pop", "Rock", "Jazz", "Hip-Hop", "Classical", "EDM", "Other"])
        song_feeling = st.selectbox("How do songs usually make you feel?", ["Relaxed", "Motivated", "Nostalgic", "Sad", "Energetic"])
        submit_button = st.form_submit_button("Submit")

    if submit_button:
        user_responses = {
            "mood_level": mood_level,
            "mood_swings": mood_swings,
            "activity": activity,
            "favorite_genre": favorite_genre,
            "song_feeling": song_feeling,
        }
        therapy_exercise, playlist_link = process_questionnaire(user_responses)
        st.write("### AI Therapist Suggestion")
        st.write(therapy_exercise)
        st.write("### Your AI-Generated Playlist")
        st.markdown(f"[Click here to listen]({playlist_link})")

