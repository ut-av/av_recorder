# ROS2 Bag Recorder

A ROS2 node for managing rosbag recording with topic filtering and control via topics and joystick buttons.

## Features

- **Multiple Control Methods**:
  - Binary topic (`/record`) for programmatic control
  - PS4 controller buttons for manual control
  - GUI integration for visual status feedback

- **Topic Filtering**: Select which topics to record
- **Status Publishing**: Broadcasts recording status to other nodes
- **Automatic Storage**: Saves bags with timestamped filenames

## Installation

Build the package:

```bash
cd ~/roboracer_ws
colcon build --packages-select recorder
source install/setup.bash
```

## Usage

### Starting the Recorder Node

```bash
ros2 run recorder bag_recorder
```

The node will create a directory at `~/rosbag_recordings` where all recordings will be saved.

### Control Methods

#### 1. Topic Control

Start recording:
```bash
ros2 topic pub /record std_msgs/msg/Bool "data: true" --once
```

Stop recording:
```bash
ros2 topic pub /record std_msgs/msg/Bool "data: false" --once
```

#### 2. PS4 Controller

- **Green Triangle Button**: Start recording
- **Red Square Button**: Stop recording

#### 3. GUI Integration

The GUI displays:
- **Recording Indicator**: A "REC" label with LED indicator
  - Red: Currently recording
  - Grey: Not recording
- **Recorder Tab**: Select which topics to record

### Topic Configuration

#### View Current Topics

```bash
ros2 topic echo /recorder/topics
```

#### Set Topics to Record

Send a JSON array of topic names:

```bash
ros2 topic pub /recorder/set_topics std_msgs/msg/String "data: '[\"'/scan'\", \"'/camera_0/image_raw'\", \"'/joystick'\"]'" --once
```

**Note**: Topics cannot be changed while recording is in progress.

### Check Recording Status

```bash
ros2 topic echo /recording
```

Returns:
- `1`: Currently recording
- `0`: Not recording

## Default Topics

The following topics are recorded by default:

- `/scan` - LiDAR data
- `/camera_0/image_raw` - Camera images
- `/ackermann_curvature_drive` - Drive commands
- `/car_status` - Vehicle status
- `/joystick` - Joystick inputs
- `/imu` - IMU data
- `/odom` - Odometry

## Recorded Files

Files are saved with the following naming convention:

```
~/rosbag_recordings/roboracer_YYYYMMDD_HHMMSS/
```

Example: `roboracer_20250109_143022`

## Architecture

### Published Topics

- `/recording` (`std_msgs/Int32`) - Recording status (1 = recording, 0 = not recording)
- `/recorder/topics` (`std_msgs/String`) - Current list of topics to record (JSON array)

### Subscribed Topics

- `/record` (`std_msgs/Bool`) - Start/stop recording
- `/joystick` (`sensor_msgs/Joy`) - PS4 controller input
- `/recorder/set_topics` (`std_msgs/String`) - Update topic list (JSON array)

## Troubleshooting

### Recording Not Starting

1. Check if the node is running:
   ```bash
   ros2 node list | grep bag_recorder
   ```

2. Verify topics exist:
   ```bash
   ros2 topic list
   ```

3. Check node logs:
   ```bash
   ros2 run recorder bag_recorder
   ```

### Disk Space

The recorder saves to `~/rosbag_recordings`. Monitor disk space:

```bash
df -h ~
```

The GUI also displays a disk space indicator at the bottom.

### Topics Not Being Recorded

Ensure the topics you want to record:
1. Are actually being published
2. Are in the selected topics list
3. Were selected **before** starting recording

## Integration with Other Nodes

### Publishing Recording Commands

From your own node:

```python
from std_msgs.msg import Bool

# In your node
self.record_pub = self.create_publisher(Bool, '/record', 10)

# Start recording
msg = Bool()
msg.data = True
self.record_pub.publish(msg)

# Stop recording
msg.data = False
self.record_pub.publish(msg)
```

### Monitoring Recording Status

```python
from std_msgs.msg import Int32

# In your node
self.recording_sub = self.create_subscription(
    Int32,
    '/recording',
    self.recording_callback,
    10
)

def recording_callback(self, msg):
    if msg.data == 1:
        self.get_logger().info('Recording active')
    else:
        self.get_logger().info('Recording inactive')
```

## License

TODO: License declaration

