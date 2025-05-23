from flask import Flask, request, jsonify, render_template
import cv2
import numpy as np

app = Flask(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Initialize movement counters
look_away_count = 0
left_right_moves = 0
disappearance_count = 0
max_warnings = 5  # Rational threshold before flagging as cheating

@app.route("/")
def index():
    return render_template("test.html")

@app.route("/detect", methods=["POST"])
def detect_face():
    global look_away_count, left_right_moves, disappearance_count

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No image provided"}), 400

    image = np.frombuffer(file.read(), dtype=np.uint8)
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)
    
    if img is None:
        return jsonify({"error": "Image decoding failed"}), 500

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    # Detect suspicious movement
    if len(faces) == 0:
        disappearance_count += 1  # User moved away
    elif len(faces) == 1:
        x, y, w, h = faces[0]
        center_x = x + w // 2
        center_y = y + h // 2

        # Track left/right movement threshold
        if center_x < 150 or center_x > 500:  # Adjust range based on webcam feed
            left_right_moves += 1

        # Track downward head movement (looking at phone)
        if center_y > 400:  # Adjust based on head positioning
            look_away_count += 1

    # Set thresholds for cheating detection
    warning_status = "✅ Normal Behavior"
    if look_away_count >= 3 or left_right_moves >= 3:
        warning_status = "⚠️ Suspicious Movements"
    if disappearance_count >= max_warnings:
        warning_status = "❌ Cheating Alert!"

    return jsonify({
        "face_detected": len(faces) > 0,
        "look_away_count": look_away_count,
        "left_right_moves": left_right_moves,
        "disappearance_count": disappearance_count,
        "status": warning_status
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)