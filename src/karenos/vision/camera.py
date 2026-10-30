"""Manually launched webcam preview. No background camera access is performed."""

from __future__ import annotations


def main() -> None:
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit(
            "OpenCV is not installed. Run: python -m pip install -e '.[vision]'"
        ) from exc

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        camera.release()
        raise SystemExit("Could not open webcam. Check its connection and permissions.")

    print("KAREN OS camera preview. Press Q in the preview window to close.")
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("The camera did not return a frame.")
                break
            cv2.imshow("KAREN OS | Camera Preview", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
