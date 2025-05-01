from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("yolov8n.pt")

import cv2
from collections import defaultdict

import cv2
from collections import defaultdict

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Get the first frame size to maintain consistency throughout
    ret, first_frame = cap.read()
    if not ret:
        raise ValueError("Unable to read video")

    h, w, _ = first_frame.shape  # Use the size of the first frame
    out = cv2.VideoWriter("processed.mp4", cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

    roi = (100, 100, 400, 300)  # (x, y, w, h)
    prev_positions = {}
    
    object_counts = defaultdict(set)  # object name -> set of IDs
    object_speeds = defaultdict(list)  # object name -> list of speeds

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Resize the frame to match the first frame size to ensure consistency
        frame = cv2.resize(frame, (w, h))

        results = model.track(frame, persist=True, verbose=False)
        frame = results[0].plot()

        # Draw ROI
        x, y, rw, rh = roi
        cv2.rectangle(frame, (x, y), (x + rw, y + rh), (0, 255, 0), 2)

        for box in results[0].boxes:
            tid = int(box.id[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)

            in_roi = x < cx < x + rw and y < cy < y + rh

            # Get class name (e.g., 'person', 'car')
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]

            label = f"ID:{tid}"

            if tid in prev_positions:
                px, py = prev_positions[tid]
                speed = ((cx - px)**2 + (cy - py)**2)**0.5 * fps

                object_counts[class_name].add(tid)
                object_speeds[class_name].append(speed)

                label += f" | Speed: {speed:.1f}px/s"

            prev_positions[tid] = (cx, cy)

            if in_roi:
                label += " | ROI"

            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        out.write(frame)

    cap.release()
    out.release()

    # Summarize results
    summary = {}
    pixel_to_meter_ratio = 0.05  # meters per pixel
    conversion_factor = pixel_to_meter_ratio * 3.6  # to convert px/s to km/h

    for obj, ids in object_counts.items():
        speeds = object_speeds[obj]
        avg_speed_px = sum(speeds) / len(speeds) if speeds else 0
        avg_speed_kmph = avg_speed_px * conversion_factor
        summary[obj] = {
            "count": len(ids),
            "average_speed": round(avg_speed_kmph, 2)  # in km/h
        }

    return summary


