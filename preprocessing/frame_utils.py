import cv2


def resize_frame(frame, size=(224, 224)):
    """
    Resize frame.

    Args:
        frame
        size

    Returns:
        resized frame
    """

    return cv2.resize(frame, size)