

import streamlit as st
import google.generativeai as genai
import requests
import json
#from deepface import DeepFace
from PIL import Image # Pillow for image handling with Streamlit
import io # To handle image bytes
import os # Needed for working with file paths if saving temp image

# --- Page Configuration (Optional but Recommended) ---
st.set_page_config(
    page_title="Audora",
    page_icon="🎵",
    layout="wide",
)

# --- Load API Keys from Streamlit Secrets ---
try:
    YOUTUBE_API_KEY = st.secrets["youtube"]["api_key"]
    GEMINI_API_KEY = st.secrets["gemini"]["api_key"]

    # Configure Google Gemini API
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-pro-latest") # Or "gemini-pro"

except KeyError as e:
    st.error(f"ERROR: Missing API Key in Streamlit secrets: {e}. Please check your secrets.toml or Streamlit Cloud secrets.")
    st.stop() # Stop execution if keys are missing
except Exception as e:
    st.error(f"ERROR: Could not configure Generative AI Client: {e}")
    st.stop()

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"

# --- Helper Functions (Adapted for Streamlit) ---

def detect_emotion_from_image(image_bytes):
    """Detects emotion from image bytes provided by Streamlit uploader."""
    return "unknown"

# Function to get AI therapist advice and real song recommendations (Unchanged Logically)
def get_ai_recommendation(emotion, responses):
    needs_therapy = emotion.lower() in ["sad", "angry", "fear", "disgust"] or responses["mood_level"] <= 4 # Adjusted emotion list

    user_profile = f"""
    Detected Emotion: {emotion}
    Self-Reported Happiness (1-10): {responses['mood_level']}
    Mood Swings Frequency: {responses['mood_swings']}
    Preferred Low-Mood Activity: {responses['activity']}
    Favorite Music Genre: {responses['favorite_genre']}
    Favorite Artists: {', '.join(responses['favorite_artists']) if responses['favorite_artists'] else 'None specified'}
    """
    if responses["extra_info"]:
        user_profile += "\nAdditional Context Provided:\n"
        for key, value in responses["extra_info"].items():
            if value: # Only include if user provided an answer
                 user_profile += f"- {key.replace('_', ' ').title()}: {value}\n"

    song_prompt = f"""
    Based on the following user profile:
    {user_profile}

    Generate exactly **10 diverse song recommendations** that align with the user's **current detected emotion ({emotion})** and their **music preferences**.
    Format the output strictly as:
    **Song Title - Artist Name**
    (One song per line)

    - Prioritize songs by their favorite artists ({', '.join(responses['favorite_artists']) if responses['favorite_artists'] else 'None specified'}) if suitable matches exist for the mood.
    - If favorite artists don't fit the mood, or if none were provided, suggest songs from their favorite genre ({responses['favorite_genre']}) or similar genres/artists that match the **emotion ({emotion})**.
    - Ensure the songs are real and likely available on major streaming platforms like YouTube Music.
    - Aim for variety within the mood (e.g., if sad, maybe some comforting, some cathartic).

    Return ONLY the list of 10 songs in the specified format, nothing else before or after.
    """

    therapy_prompt = ""
    if needs_therapy:
        therapy_prompt = f"""
        Based on the following user profile:
        {user_profile}

        The user seems to be experiencing challenging emotions ({emotion}) or reported low happiness ({responses['mood_level']}).
        Provide **5 distinct and actionable well-being tips or coping strategies** tailored to their situation.
        Focus on practical techniques like mindfulness, journaling, gentle exercise, connecting with others, reframing thoughts, or suggesting professional help if appropriate based on the context (like prolonged low mood or stress).
        Phrase the tips gently and supportively.

        Format the output as a numbered list (1., 2., 3., etc.).
        Return ONLY the numbered list of 5 tips, nothing else before or after.
        """

    songs = []
    therapy_recommendations = []

    try:
        with st.spinner("Generating song recommendations from AI..."):
            # Increased max_output_tokens slightly for safety, added safety_settings
            generation_config = genai.types.GenerationConfig(max_output_tokens=500, temperature=0.7)
            safety_settings = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]

            song_response = model.generate_content(
                song_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
                )

            if not song_response.candidates:
                 st.warning(f"Song generation might have been blocked. Feedback: {song_response.prompt_feedback}")
            elif hasattr(song_response, 'text'):
                raw_songs = song_response.text.strip()
                songs = [line.strip() for line in raw_songs.splitlines() if line.strip() and " - " in line and not line.strip().startswith(("*", "-"))][:10]
            else:
                 st.warning(f"Unexpected format for song response: {song_response}")

        if needs_therapy:
            with st.spinner("Generating well-being tips from AI..."):
                therapy_response = model.generate_content(
                    therapy_prompt,
                    generation_config=generation_config, # Reuse config
                    safety_settings=safety_settings # Reuse safety settings
                    )

                if not therapy_response.candidates:
                     st.warning(f"Therapy tip generation might have been blocked. Feedback: {therapy_response.prompt_feedback}")
                elif hasattr(therapy_response, 'text'):
                     raw_therapy = therapy_response.text.strip()
                     therapy_recommendations = [line.strip()[line.find('.')+1:].strip() for line in raw_therapy.splitlines() if line.strip() and line.strip()[0].isdigit() and '.' in line[:3]][:5]
                else:
                     st.warning(f"Unexpected format for therapy response: {therapy_response}")

    except Exception as e:
        st.error(f"Error generating AI recommendations: {e}")
        if "API key not valid" in str(e): st.error("Please ensure your Gemini API key is correctly configured and valid.")
        elif "quota" in str(e).lower(): st.error("You might have exceeded your API quota for Gemini.")
        songs, therapy_recommendations = [], [] # Fallback

    # Fallback messages if generation failed or produced empty results
    if not songs:
        st.info("AI could not generate specific song recommendations at this time.")
    if needs_therapy and not therapy_recommendations:
        st.info("AI could not generate specific well-being tips. Remember standard self-care practices.")
        # Add generic tips if preferred
        # therapy_recommendations = ["Remember to be kind to yourself.", ...]

    return therapy_recommendations, songs

# Function to fetch YouTube Music details (Unchanged Logically)
def fetch_youtube_music_data(song_list):
    music_tiles = []
    if not song_list:
        return music_tiles

    with st.spinner(f"Searching YouTube for {len(song_list)} songs..."):
        for song_query in song_list:
            try:
                parts = song_query.split(" - ", 1)
                if len(parts) == 2:
                    song_title, artist = parts
                    search_term = f"{song_title} {artist} official audio"
                else:
                    song_title = song_query
                    artist = "Unknown"
                    search_term = song_query

                params = {
                    "part": "snippet",
                    "q": search_term,
                    "type": "video",
                    "videoCategoryId": "10", # Music Category
                    "key": YOUTUBE_API_KEY,
                    "maxResults": 1
                }
                response = requests.get(YOUTUBE_API_URL, params=params)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                data = response.json()

                if "items" in data and len(data["items"]) > 0:
                    video = data["items"][0]
                    video_id = video["id"]["videoId"]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    actual_title = video["snippet"]["title"]
                    thumbnails = video["snippet"]["thumbnails"]
                    # Get best available thumbnail quality
                    thumbnail_url = thumbnails.get("high", thumbnails.get("medium", thumbnails.get("default")))["url"]

                    music_tiles.append({
                        "query_title": song_title, # Keep original queried title
                        "query_artist": artist,   # Keep original queried artist
                        "youtube_title": actual_title, # Add title from YouTube
                        "thumbnail": thumbnail_url,
                        "link": video_url
                    })
                # else: # Optional: Log if no results found for a specific query
                   # print(f"No YouTube result for: {search_term}")

            except requests.exceptions.RequestException as e:
                st.warning(f"Network or API error searching YouTube for '{song_query}': {e}")
                if e.response is not None and e.response.status_code == 403:
                     st.error("YouTube API quota might be exceeded or key is invalid/restricted.")
            except Exception as e:
                st.warning(f"Unexpected error searching YouTube for '{song_query}': {e}")

    if not music_tiles and song_list:
        st.warning("Could not fetch details from YouTube for any recommended songs.")
    elif len(music_tiles) < len(song_list):
         st.info(f"Found YouTube details for {len(music_tiles)} out of {len(song_list)} recommended songs.")

    return music_tiles

# --- Streamlit App UI ---

st.title("🎵 Mood Music & Support Assistant")
st.markdown("Upload an image to detect your mood, answer a few questions, and get personalized music recommendations and well-being tips.")

# --- Step 1: Image Upload and Emotion Detection ---
st.header("Step 1: Detect Your Mood from an Image")
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "bmp", "gif"])

detected_emotion = "unknown" # Default
if uploaded_file is not None:
    # Display the uploaded image (optional)
    # st.image(uploaded_file, caption='Uploaded Image.', use_column_width=True)
    image_bytes = uploaded_file.getvalue()
    detected_emotion = detect_emotion_from_image(image_bytes)
    # Store detected emotion in session state to persist across reruns if needed,
    # otherwise it's recalculated whenever the file exists. For this flow, recalculating is fine.
else:
    st.info("Please upload an image to start the emotion detection.")


# --- Step 2: Questionnaire ---
st.header("Step 2: Tell Us More About You")

# Use a form to group inputs, maybe trigger analysis with a button inside form
# Or collect inputs directly - simpler for this flow if analysis runs after image upload + button click

mood_level = st.slider("On a scale of 1 (very unhappy) to 10 (very happy), how happy are you feeling right now?", 1, 10, 5)
mood_swings = st.selectbox("How often do you experience mood swings?", ["Rarely", "Sometimes", "Often", "Always"])
activity = st.text_input("What kind of activity do you usually enjoy or find comforting when feeling low?")
favorite_genre = st.text_input("What's your favorite music genre?")
favorite_artists = st.text_input("List one or more favorite music artists (comma-separated)")

extra_responses = {}
# Conditionally show extra questions based on mood_level slider
if mood_level <= 4:
    with st.expander("Optional: Tell us a bit more (since you rated your mood low)"):
        extra_responses["stress_cause"] = st.text_input("What, if anything, has been bothering you the most lately? (Optional)")
        extra_responses["coping_methods"] = st.text_input("How do you usually try to handle stress or difficult feelings? (Optional)")
        extra_responses["sleep_quality"] = st.selectbox("How would you rate your sleep quality recently? (Optional)", ["Good", "Average", "Poor", "Not Sure"])


# --- Step 3: Get Recommendations Button ---
st.header("Step 3: Get Recommendations")

if st.button("Generate Music & Tips"):
    if uploaded_file is None:
        st.warning("Please upload an image first (Step 1).")
    else:
        # Ensure emotion detection ran if file is present but detection failed earlier
        if detected_emotion == "unknown":
             st.info("Attempting emotion detection again...")
             image_bytes = uploaded_file.getvalue() # Get bytes again
             detected_emotion = detect_emotion_from_image(image_bytes)
             if detected_emotion == "unknown":
                  st.warning("Still unable to detect emotion. Proceeding without detected mood.")


        # Prepare user responses dictionary
        user_responses = {
            "mood_level": mood_level,
            "mood_swings": mood_swings,
            "activity": activity.strip(),
            "favorite_genre": favorite_genre.strip(),
            "favorite_artists": [artist.strip() for artist in favorite_artists.split(",") if artist.strip()],
            "extra_info": extra_responses # Already collected
        }

        # --- Generate AI Recommendations ---
        st.subheader("AI Recommendations")
        ai_therapy, recommended_songs = get_ai_recommendation(detected_emotion, user_responses)

        # --- Display AI Therapist Suggestions ---
        if ai_therapy:
            st.markdown("#### Well-being Suggestions:")
            for i, tip in enumerate(ai_therapy, 1):
                st.markdown(f"{i}. {tip}")
        else:
            # Displayed info message inside get_ai_recommendation if needed
            pass

        # --- Display Recommended Songs ---
        if recommended_songs:
            st.markdown("#### Recommended Songs:")
            # Store recommended songs for YouTube search below
            st.session_state['recommended_songs'] = recommended_songs # Use session state to pass to next section
            for i, song in enumerate(recommended_songs, 1):
                st.markdown(f"{i}. {song}")

            # --- Fetch and Display YouTube Music Data ---
            st.subheader("Listen on YouTube")
            music_data = fetch_youtube_music_data(recommended_songs)

            if music_data:
                # Display in columns for better layout
                num_columns = 3 # Adjust as needed
                cols = st.columns(num_columns)
                col_index = 0
                for tile in music_data:
                    with cols[col_index % num_columns]:
                        st.image(tile['thumbnail'], caption=f"{tile['query_title']} - {tile['query_artist']}", use_column_width=True)
                        st.markdown(f"**[{tile['youtube_title']}]({tile['link']})**", unsafe_allow_html=True)
                        #st.write(f"Query: {tile['query_title']} - {tile['query_artist']}") # Optional: show original query
                        st.markdown("---") # Separator

                    col_index += 1
            else:
                 st.info("Could not retrieve YouTube links or thumbnails for the recommended songs.")

            # --- Optional: Show Raw JSON ---
            with st.expander("Show Raw Music Data (JSON)"):
                st.json(music_data)

        else:
             st.info("No songs were recommended by the AI.")
             # Clear any previous recommendations if button is clicked again
             if 'recommended_songs' in st.session_state:
                  del st.session_state['recommended_songs']

# --- Footer (Optional) ---
st.markdown("---")
st.markdown("App by [Your Name/Organization] | Uses Gemini & YouTube APIs")
