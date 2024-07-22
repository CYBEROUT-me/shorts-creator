import os
import subprocess

def get_video_duration(video_path):
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

# Get user input for the video file path
video_path = input("Enter the path for a video file: ")
count = int(input("Enter the number of videos: "))
time = int(input("Input the length of each subclip (in seconds): "))
start_point = int(input("Input the start point of the film (in seconds): "))
fps = float(input("Input the fps of the video: "))
start = int(input("Enter count of already existing videos: "))

# Get the total duration of the video
video_duration = get_video_duration(video_path)

filename_without_extension = os.path.splitext(os.path.basename(video_path))[0]
output_folder = f".\\{filename_without_extension}"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

start_time = start_point + start * time
end_time = start_time + time
video_number = 1 + start
count_current = 1

while end_time <= video_duration and count_current <= count:
    # Ensure end_time does not exceed video duration
    end_time = min(start_time + time, video_duration)

    output_path = os.path.join(output_folder, f"{filename_without_extension} (part {video_number}) #shorts.mp4")

    # Get video dimensions
    probe_command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(probe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    width, height = map(int, result.stdout.strip().split('\n'))

    # Define the target aspect ratio (9:16 for output video)
    target_width = 1080
    target_height = 1920
    aspect_ratio_target = target_width / target_height
    aspect_ratio_video = width / height

    # Calculate dimensions for cropping to 3:4 aspect ratio
    if aspect_ratio_video > 3/4:
        # Video is wider than 3:4, crop width
        crop_width = int(height * (3/4))
        crop_height = height
        crop_x = (width - crop_width) / 2
        crop_y = 0
    else:
        # Video is taller than 3:4, crop height
        crop_width = width
        crop_height = int(width * (4/3))
        crop_x = 0
        crop_y = (height - crop_height) / 2

    # Scale the cropped video to 9:16 resolution and apply horizontal mirroring
    ffmpeg_command = [
        "ffmpeg",
        "-y",  # Overwrite output files without asking
        "-ss", str(start_time),
        "-i", video_path,
        "-t", str(end_time - start_time),
        "-vf", f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},scale={target_width}:{target_height},fps={fps},hflip",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-strict", "experimental",
        output_path
    ]

    subprocess.run(ffmpeg_command)

    # Check the output video properties
    probe_command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=width,height",
        "-of", "default=noprint_wrappers=1:nokey=1",
        output_path
    ]
    result = subprocess.run(probe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    video_number += 1
    start_time = end_time
    count_current += 1