import cv2
import os


def video_to_frames(video_path: str, output_dir: str, fps: int = 2):
    """
    Extract frames from video.

    Args:
        video_path: path to video
        output_dir: folder to save frames
        fps: frames per second to extract
    """

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / fps)

    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        if frame_count % frame_interval == 0:
            frame_path = os.path.join(
                output_dir, f"frame_{saved_count:04d}.jpg"
            )
            cv2.imwrite(frame_path, frame)
            saved_count += 1

        frame_count += 1

    cap.release()

    print(f"Saved {saved_count} frames")