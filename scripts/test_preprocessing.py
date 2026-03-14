from preprocessing.video_to_frames import video_to_frames
from preprocessing.audio_extract import extract_audio

VIDEO = "data/sample.mp4"

video_to_frames(
    VIDEO,
    "storage/frames",
    fps=2,
)

extract_audio(
    VIDEO,
    "storage/audio/audio.wav",
)