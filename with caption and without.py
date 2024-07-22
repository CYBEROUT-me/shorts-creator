import re
import os
from moviepy.editor import VideoFileClip, ColorClip
import assemblyai as aai
import cv2
import subprocess
from assemblyai.types import TranscriptError

def parse_srt(srt_file):
    with open(srt_file, 'r', encoding='utf-8') as file:
        content = file.read()

    blocks = content.strip().split('\n\n')

    subtitles = []

    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            timing_line = lines[1]
            start, end = re.findall(r'(\d{2}:\d{2}:\d{2},\d{3})', timing_line)
            text = '\n'.join(lines[2:])
            start_time = convert_srt_time_to_seconds(start)
            end_time = convert_srt_time_to_seconds(end)
            subtitles.append((start_time, end_time, text))

    return subtitles

def convert_srt_time_to_seconds(srt_time):
    time_part, milliseconds = srt_time.split(',')
    hours, minutes, seconds = map(int, time_part.split(':'))
    milliseconds = int(milliseconds)
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000

def seconds_to_frames(seconds, frame_rate):
    return int(round(seconds * frame_rate))

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

def process_subtitles(video_clip_path):
    srt_file = "subtitles.srt"
    temp_video_path = "temp_black_video.mp4"
    output_video_path = video_clip_path.replace("#shorts.mp4", "#shorts_with_captions.mp4")

    # Transcribe the extracted audio and export subtitles to SRT
    transcript = aai.Transcriber(config=config).transcribe(video_clip_path)
    subtitles_srt = transcript.export_subtitles_srt(chars_per_caption=32)

    # Save the subtitles to an SRT file
    with open(srt_file, 'w', encoding='utf-8') as file:
        file.write(subtitles_srt)

    # Parse the SRT file
    subtitles = parse_srt(srt_file)

    # Get frame rate and video size
    video = VideoFileClip(video_clip_path)
    frame_rate = video.fps
    frame_size = (int(video.w), int(video.h))

    # Create a black video with the same duration as the input video
    duration = video.duration
    black_clip = ColorClip(size=frame_size, color=(0, 0, 0), duration=duration).set_fps(frame_rate)

    # Prepare to process the black video with OpenCV
    cap = cv2.VideoCapture(video_clip_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4 format
    out = cv2.VideoWriter(temp_video_path, fourcc, frame_rate, frame_size)

    #Current frame
    frame_idx = 0

    while True:
        # Capture frames in the black video
        ret, frame = cap.read()
        if not ret:
            break  # Exit loop if no more frames

        # Fill the frame with black color
        frame[:] = (0, 0, 0)

        # Describe the type of font to be used
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_color = (0, 255, 255)  # Yellow text
        font_thickness = 2
        line_type = cv2.LINE_4

        # Write subtitles on the frame if they are in the time range
        for start_time, end_time, text in subtitles:
            start_frame = seconds_to_frames(start_time, frame_rate)
            end_frame = seconds_to_frames(end_time, frame_rate)
            if start_frame <= frame_idx <= end_frame:
                # Calculate text size and position
                text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
                text_width, text_height = text_size
                text_x = (frame.shape[1] - text_width) // 2  # Center horizontally
                text_y = (frame.shape[0] + text_height) // 2 + 500  # Center vertically
                cv2.putText(frame,
                            text,
                            (text_x, text_y),
                            font, font_scale,
                            font_color,
                            font_thickness,
                            line_type)

        out.write(frame)
        frame_idx += 1

    # Release the video capture and writer objects
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # Use ffmpeg to overlay the black video with subtitles on top of the original video
    overlay_command = f'ffmpeg -i "{video_clip_path}" -i "{temp_video_path}" -filter_complex "[1]colorkey=black:0.1:0.1[ckout];[0][ckout]overlay[out]" -map "[out]" -map 0:a -c:v libx264 -c:a copy "{output_video_path}"'
    os.system(overlay_command)

    # Clean up
    os.remove(srt_file)
    os.remove(temp_video_path)

# AssemblyAI settings
aai.settings.api_key = "API KEY"
config = aai.TranscriptionConfig(language_detection=True)


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
        output_path
    ]

    subprocess.run(ffmpeg_command)

    # Process subtitles for the current video clip
    try:
        process_subtitles(output_path)
    except (FileNotFoundError, ValueError, aai.types.TranscriptError) as e:
        print(f"Skipping subtitles processing for {output_path} due to error: {e}")

    video_number += 1
    start_time = end_time
    count_current += 1