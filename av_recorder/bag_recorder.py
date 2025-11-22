#!/usr/bin/env python3

"""
ROS2 Bag Recorder Node
Manages rosbag recording with topic filtering and control via topics and joystick.
"""

import rclpy
from rclpy.node import Node
from rclpy.serialization import serialize_message
from std_msgs.msg import Bool, String, Int32
from sensor_msgs.msg import Joy
import rosbag2_py
from datetime import datetime
import os
import threading
import json


class BagRecorder(Node):
    """Node for managing ROS2 bag recording with topic filtering."""
    
    # PS4 Controller button mappings
    BUTTON_CIRCLE = 1  # Red circle - toggle recording
    
    def __init__(self):
        super().__init__('bag_recorder')
        
        # Recording state
        self.is_recording = False
        self.writer = None
        self.recording_lock = threading.Lock()
        
        # Default topics to record
        self.topics_to_record = [
            '/scan',
            '/camera_0/image_raw/compressed',
            '/ackermann_curvature_drive',
            '/car_status',
            '/joystick',
            '/imu',
            '/odom',
            '/tf',
            '/tf_static'
        ]
        
        # Storage location for bags
        self.bag_storage_path = os.path.expanduser('~/roboracer_ws/data/rosbags')
        if not os.path.exists(self.bag_storage_path):
            os.makedirs(self.bag_storage_path)
        
        # Subscribers
        self.record_sub = self.create_subscription(
            Bool,
            '/record',
            self.record_callback,
            10
        )
        
        self.joystick_sub = self.create_subscription(
            Joy,
            '/joystick',
            self.joystick_callback,
            10
        )
        
        self.topic_list_sub = self.create_subscription(
            String,
            '/recorder/set_topics',
            self.set_topics_callback,
            10
        )
        
        # Publishers
        self.recording_status_pub = self.create_publisher(
            Int32,
            '/recording',
            10
        )
        
        self.topics_list_pub = self.create_publisher(
            String,
            '/recorder/topics',
            10
        )
        
        # Publish status and topic list periodically
        self.status_timer = self.create_timer(0.5, self.publish_status)
        
        # Track previous joystick button state
        self.prev_circle = 0
        
        self.get_logger().info('Bag Recorder Node initialized')
        self.get_logger().info(f'Recording directory: {self.bag_storage_path}')
        self.publish_current_topics()
    
    def record_callback(self, msg):
        """Handle /record topic messages to start/stop recording."""
        if msg.data and not self.is_recording:
            self.start_recording()
        elif not msg.data and self.is_recording:
            self.stop_recording()
    
    def joystick_callback(self, msg):
        """Handle joystick input for PS4 controller recording control."""
        if len(msg.buttons) <= self.BUTTON_CIRCLE:
            return
        
        # Detect button press (transition from 0 to 1)
        circle_pressed = msg.buttons[self.BUTTON_CIRCLE] == 1 and self.prev_circle == 0
        
        # Update previous state
        self.prev_circle = msg.buttons[self.BUTTON_CIRCLE]
        
        # Toggle recording on circle button press
        if circle_pressed:
            if self.is_recording:
                self.get_logger().info('Circle button pressed - stopping recording')
                self.stop_recording()
            else:
                self.get_logger().info('Circle button pressed - starting recording')
                self.start_recording()
    
    def set_topics_callback(self, msg):
        """Handle topic list updates via /recorder/set_topics."""
        try:
            # Expect JSON array of topic names
            new_topics = json.loads(msg.data)
            if isinstance(new_topics, list):
                with self.recording_lock:
                    if self.is_recording:
                        self.get_logger().warn('Cannot change topics while recording')
                        return
                    self.topics_to_record = new_topics
                    self.get_logger().info(f'Updated topics to record: {new_topics}')
                    self.publish_current_topics()
            else:
                self.get_logger().error('Invalid topic list format (expected JSON array)')
        except json.JSONDecodeError as e:
            self.get_logger().error(f'Failed to parse topic list: {e}')
    
    def publish_status(self):
        """Publish recording status (1 for recording, 0 for not recording)."""
        msg = Int32()
        msg.data = 1 if self.is_recording else 0
        self.recording_status_pub.publish(msg)
    
    def publish_current_topics(self):
        """Publish current list of topics to record."""
        msg = String()
        msg.data = json.dumps(self.topics_to_record)
        self.topics_list_pub.publish(msg)
    
    def start_recording(self):
        """Start recording a new bag file."""
        with self.recording_lock:
            if self.is_recording:
                self.get_logger().warn('Already recording')
                return
            
            # Generate bag file name with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            bag_path = os.path.join(self.bag_storage_path, f'roboracer_{timestamp}')
            
            try:
                # Create the writer
                storage_options = rosbag2_py.StorageOptions(
                    uri=bag_path,
                    storage_id='sqlite3'
                )
                
                converter_options = rosbag2_py.ConverterOptions(
                    input_serialization_format='cdr',
                    output_serialization_format='cdr'
                )
                
                self.writer = rosbag2_py.SequentialWriter()
                self.writer.open(storage_options, converter_options)
                
                # Subscribe to topics and register them with the bag
                self.topic_subscriptions = []
                
                # Get available topics
                available_topics = self.get_topic_names_and_types()
                available_topic_dict = {name: types for name, types in available_topics}
                
                for topic_name in self.topics_to_record:
                    if topic_name in available_topic_dict:
                        topic_types = available_topic_dict[topic_name]
                        if topic_types:
                            topic_type = topic_types[0]  # Use first type if multiple
                            
                            # Create topic metadata
                            topic_metadata = rosbag2_py.TopicMetadata(
                                name=topic_name,
                                type=topic_type,
                                serialization_format='cdr'
                            )
                            
                            try:
                                self.writer.create_topic(topic_metadata)
                                
                                # Create subscription to capture messages
                                # We need to use GenericSubscription since we don't know the type
                                # For now, we'll create subscriptions for known types
                                self._create_topic_subscription(topic_name, topic_type)
                                
                                self.get_logger().info(f'Recording topic: {topic_name} ({topic_type})')
                            except Exception as e:
                                self.get_logger().error(f'Failed to create topic {topic_name}: {e}')
                    else:
                        self.get_logger().warn(f'Topic {topic_name} not available')
                
                self.is_recording = True
                self.get_logger().info(f'Started recording to {bag_path}')
                
            except Exception as e:
                self.get_logger().error(f'Failed to start recording: {e}')
                if self.writer:
                    try:
                        self.writer.close()
                    except:
                        pass
                    self.writer = None
    
    def _create_topic_subscription(self, topic_name, topic_type):
        """Create a subscription for recording a specific topic."""
        # Import message types dynamically based on topic type
        # This is a simplified version - in production you'd want better type handling
        
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy
        
        # Use a permissive QoS for recording
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        try:
            # Create a generic subscription that serializes and writes to bag
            sub = self.create_subscription(
                self._get_message_class(topic_type),
                topic_name,
                lambda msg, topic=topic_name: self._record_message(topic, msg),
                qos_profile
            )
            self.topic_subscriptions.append(sub)
        except Exception as e:
            self.get_logger().error(f'Failed to subscribe to {topic_name}: {e}')
    
    def _get_message_class(self, topic_type):
        """Get the message class for a given topic type string."""
        # Parse topic type string (e.g., 'sensor_msgs/msg/LaserScan')
        parts = topic_type.split('/')
        if len(parts) == 3:
            package, _, msg_name = parts
            try:
                # Import the message class dynamically
                module = __import__(f'{package}.msg', fromlist=[msg_name])
                return getattr(module, msg_name)
            except (ImportError, AttributeError) as e:
                self.get_logger().error(f'Failed to import {topic_type}: {e}')
                # Return a generic message type as fallback
                from std_msgs.msg import String
                return String
        
        # Fallback
        from std_msgs.msg import String
        return String
    
    def _record_message(self, topic_name, msg):
        """Record a message to the bag file."""
        if not self.is_recording or not self.writer:
            return
        
        try:
            # Serialize and write the message
            serialized_msg = serialize_message(msg)
            timestamp = self.get_clock().now().nanoseconds
            self.writer.write(topic_name, serialized_msg, timestamp)
        except Exception as e:
            self.get_logger().error(f'Failed to write message to bag: {e}')
    
    def stop_recording(self):
        """Stop the current recording."""
        with self.recording_lock:
            if not self.is_recording:
                self.get_logger().warn('Not currently recording')
                return
            
            try:
                # Clean up subscriptions
                if hasattr(self, 'topic_subscriptions'):
                    for sub in self.topic_subscriptions:
                        self.destroy_subscription(sub)
                    self.topic_subscriptions = []
                
                # Close the writer
                if self.writer:
                    self.writer.close()
                    self.writer = None
                
                self.is_recording = False
                self.get_logger().info('Stopped recording')
                
            except Exception as e:
                self.get_logger().error(f'Error stopping recording: {e}')
                self.is_recording = False
                self.writer = None
    
    def destroy_node(self):
        """Clean up on node shutdown."""
        if self.is_recording:
            self.stop_recording()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    recorder = BagRecorder()
    
    try:
        rclpy.spin(recorder)
    except KeyboardInterrupt:
        pass
    finally:
        recorder.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

