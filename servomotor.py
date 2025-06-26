import requests
import time
import RPi.GPIO as GPIO
import json

# GPIO pin setup
BUZZER_PIN = 27     # Pin connected to buzzer
SERVO_PIN = 17      # Pin connected to servo motor

# Setup GPIO mode and pins
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Setup PWM for servo
servo = GPIO.PWM(SERVO_PIN, 50)  # 50Hz for MG90S
servo.start(0)

DEFAULT_ANGLE = 90  # Center position for MG90S
MAX_X_RESOLUTION = 1280  # Horizontal resolution of the camera
FLIP_X = True  # Set to True if image is mirrored

# Webhook configuration
WEBHOOK_TOKEN = '9c5e82ec-4ecc-433b-a176-c56955ea74b0'
API_KEY = '083ff613-961c-4da0-9df2-59805368af6f'
API_URL = f'https://webhook.site/token/{WEBHOOK_TOKEN}/requests?sorting=newest'

def calculate_servo_angle(x_coord, max_input=1280):
    """Calculate servo angle based on x coordinate"""
    min_angle = 50
    max_angle = 130
    x_coord = max(0, min(x_coord, max_input))  # Clamp within range
    angle = min_angle + ((x_coord / max_input) * (max_angle - min_angle))
    return max(min_angle, min(angle, max_angle))

def set_servo_angle(angle):
    """Move servo to a specific angle"""
    duty_cycle = (angle / 18.0) + 2.5  # Convert angle to duty cycle
    print(f"Setting servo to {angle:.1f} degrees (Duty: {duty_cycle:.2f})")
    servo.ChangeDutyCycle(duty_cycle)
    time.sleep(0.6)  # Wait for movement
    servo.ChangeDutyCycle(0)

def reset_servo():
    """Return servo to default center position"""
    print(f"Resetting servo to {DEFAULT_ANGLE} degrees")
    set_servo_angle(DEFAULT_ANGLE)
    time.sleep(0.6)

def get_latest_webhook():
    headers = {"api-key": API_KEY}

    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        requests_data = response.json().get('data', [])

        if not requests_data:
            print("No data received yet.")
            return None

        latest = requests_data[0]
        content = latest.get("content")

        if not content:
            print("Empty content field.")
            return None

        try:
            data = json.loads(content)
            print("Latest Webhook Data:", data)

            detection_type = data.get("detection_type")

            if detection_type in ["unauthorised", "bloodstain"]:
                print(f"Detected: {detection_type}")
                GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(1)
                GPIO.output(BUZZER_PIN, GPIO.LOW)

            if detection_type == "unauthorised":
                coordinates = data.get("coordinates", [])
                if len(coordinates) >= 4:
                    x1, _, x2, _ = coordinates[:4]
                    mid_x = (x1 + x2) / 2
                    x_coord = MAX_X_RESOLUTION - mid_x if FLIP_X else mid_x
                    angle = calculate_servo_angle(x_coord)
                    print(f"Moving servo to {angle:.1f} degrees based on x_coord {x_coord}")
                    set_servo_angle(angle)
                    time.sleep(1.0)
                    reset_servo()
                else:
                    print("Invalid coordinates format for unauthorised detection")

            return data

        except json.JSONDecodeError as e:
            print("Failed to parse JSON content:", e)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

if __name__ == '__main__':
    try:
        print("System starting... Resetting servo.")
        reset_servo()
        while True:
            get_latest_webhook()
            time.sleep(3)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        print("Resetting servo to center before shutdown...")
        reset_servo()
        servo.ChangeDutyCycle(0)
        servo.stop()
        GPIO.cleanup()
