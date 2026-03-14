import ffmpeg
import os


def extract_audio(video_path: str, output_audio: str):
    """
    Extract audio using ffmpeg.

    Args:
        video_path
        output_audio
    """

    os.makedirs(os.path.dirname(output_audio), exist_ok=True)

    (
        ffmpeg
        .input(video_path)
        .output(output_audio, acodec="pcm_s16le", ac=1, ar="16000")
        .overwrite_output()
        .run(quiet=True)
    )

    print("Audio saved:", output_audio)