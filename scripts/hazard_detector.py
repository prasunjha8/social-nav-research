import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np
import cv2

class HazardDetector(Node):
    def __init__(self):
        super().__init__('hazard_detector')
        self.subscription = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.frame_count = 0
        self.get_logger().info('Hazard Detector started...')

    def image_callback(self, msg):
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Red/orange person detection
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        red_mask1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        red_mask2 = cv2.inRange(hsv, (160, 100, 100), (180, 255, 255))
        orange_mask = cv2.inRange(hsv, (10, 100, 100), (25, 255, 255))
        person_mask = cv2.bitwise_or(red_mask1, cv2.bitwise_or(red_mask2, orange_mask))
        person_pixels = cv2.countNonZero(person_mask)

        # Edge density per zone
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        w = edges.shape[1]
        l = cv2.countNonZero(edges[:, :w//3])
        c = cv2.countNonZero(edges[:, w//3:2*w//3])
        r = cv2.countNonZero(edges[:, 2*w//3:])
        total = max(l + c + r, 1)

        hazard = {
            'left':   round(l / total, 2),
            'center': round(c / total, 2),
            'right':  round(r / total, 2)
        }

        if person_pixels > 100:
            status = f'PERSON DETECTED ({person_pixels} px)'
        elif hazard['center'] > 0.4:
            status = 'DANGER AHEAD'
        elif hazard['left'] > hazard['right']:
            status = 'STEER RIGHT'
        elif hazard['right'] > hazard['left']:
            status = 'STEER LEFT'
        else:
            status = 'PATH CLEAR'

        self.get_logger().info(
            f'Hazard | L:{hazard["left"]} C:{hazard["center"]} R:{hazard["right"]} | {status}'
        )

        self.frame_count += 1
        if self.frame_count % 30 == 0:
            h = frame_bgr.shape[0]
            cv2.rectangle(frame_bgr, (0, 0), (w//3, h), (0,255,0) if hazard['left']<0.3 else (0,0,255), 3)
            cv2.rectangle(frame_bgr, (w//3, 0), (2*w//3, h), (0,255,0) if hazard['center']<0.3 else (0,0,255), 3)
            cv2.rectangle(frame_bgr, (2*w//3, 0), (w, h), (0,255,0) if hazard['right']<0.3 else (0,0,255), 3)
            cv2.imwrite('/tmp/hazard_frame.png', frame_bgr)
            self.get_logger().info('Saved /tmp/hazard_frame.png')

def main(args=None):
    rclpy.init(args=args)
    node = HazardDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
