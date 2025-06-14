import asyncio
# import logging # Removed import
import uuid
import json
import os
import sys
import base64
import io
import traceback
import warnings
from datetime import datetime
from PIL import Image as PILImage # Renamed to avoid conflict if Image is used elsewhere
import mss
import google.genai as genai
from loguru import logger # Added import

from dotenv import load_dotenv

# Load environment variables from a .env file into the environment
load_dotenv()

# Suppress warnings from the genai library about non-data parts
warnings.filterwarnings("ignore", message=".*non-data parts in the response.*")

from aiohttp import web
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay


# For simplicity, we'll keep track of peer connections in memory.
pcs = set()
relay = MediaRelay() # Used to relay tracks if needed, or can be adapted to save to file

# --- Gemini Screen Streaming Constants ---
GEMINI_MODEL_NAME = "models/gemini-2.0-flash-live-001"
# Config updated to only include TEXT responses (one modality only is supported)
GEMINI_CONFIG = {"response_modalities": ["TEXT"]}
SCREEN_CAPTURE_INTERVAL = 2.0  # seconds (increased to reduce load)

# --- Frame Saving Configuration ---
SAVE_FRAMES = True  # Set to False to disable frame saving
FRAMES_DIR = "captured_frames"  # Directory to save frames

# --- Gemini Descriptions Configuration ---
SAVE_DESCRIPTIONS = True  # Set to False to disable description saving
DESCRIPTIONS_DIR = "gemini_descriptions"  # Directory to save descriptions
# Create timestamped filename for descriptions
session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
DESCRIPTIONS_FILE = os.path.join(DESCRIPTIONS_DIR, f"descriptions_{session_timestamp}.md")  # File to save descriptions
DESCRIPTIONS_HTML_FILE = os.path.join(DESCRIPTIONS_DIR, f"descriptions_{session_timestamp}.html")  # HTML file to save descriptions

# Store descriptions in memory for easy HTML generation
descriptions_list = []

# Create frames directory if it doesn't exist
if SAVE_FRAMES and not os.path.exists(FRAMES_DIR):
    os.makedirs(FRAMES_DIR)
    logger.info(f"Created frames directory: {FRAMES_DIR}")

# Create descriptions directory if it doesn't exist
if SAVE_DESCRIPTIONS and not os.path.exists(DESCRIPTIONS_DIR):
    os.makedirs(DESCRIPTIONS_DIR)
    logger.info(f"Created descriptions directory: {DESCRIPTIONS_DIR}")

# Helper function to save description to both markdown and HTML
def save_description_to_files(description_text):
    """Save description to both markdown and HTML files"""
    if not SAVE_DESCRIPTIONS or not description_text:
        return
        
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Add to descriptions list
    descriptions_list.append({
        'text': description_text,
        'timestamp': timestamp
    })
    
    try:
        # Write markdown file
        with open(DESCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# Gemini Screen Descriptions Log\n\n")
            f.write(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"---\n\n")
            
            for desc in descriptions_list:
                f.write(f"**{desc['timestamp']}:** {desc['text']}\n\n")
        
        # Write HTML file
        descriptions_html = ""
        for desc in descriptions_list:
            descriptions_html += f'''            <div class="description-item">
                <div class="description-time">
                    <span class="live-indicator"></span>
                    {desc['timestamp']}
                </div>
                <div class="description-text">{desc['text']}</div>
            </div>
'''
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini Screen Descriptions - {session_timestamp}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .header .timestamp {{
            margin: 10px 0 0 0;
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .description-item {{
            background: #f8f9fa;
            border-left: 4px solid #2a5298;
            margin: 20px 0;
            padding: 20px;
            border-radius: 0 10px 10px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .description-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .description-time {{
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        .description-text {{
            font-size: 1.1em;
            color: #2c3e50;
            line-height: 1.7;
        }}
        .stats {{
            background: #e9ecef;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            text-align: center;
        }}
        .stats-item {{
            display: inline-block;
            margin: 0 20px;
            text-align: center;
        }}
        .stats-number {{
            font-size: 2em;
            font-weight: bold;
            color: #2a5298;
            display: block;
        }}
        .stats-label {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }}
        .live-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #28a745;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span class="live-indicator"></span>Gemini Screen Descriptions</h1>
            <div class="timestamp">Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="content">
            <div class="stats">
                <div class="stats-item">
                    <span class="stats-number">{len(descriptions_list)}</span>
                    <span class="stats-label">Descriptions</span>
                </div>
                <div class="stats-item">
                    <span class="stats-number">Live</span>
                    <span class="stats-label">Status</span>
                </div>
            </div>
            
            <div id="descriptions-container">
{descriptions_html}            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Gemini Screen Capture System | Last updated: {timestamp}</p>
        </div>
    </div>
</body>
</html>'''

        with open(DESCRIPTIONS_HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.debug(f"Saved description to both files: {DESCRIPTIONS_FILE} and {DESCRIPTIONS_HTML_FILE}")
        
    except Exception as e:
        logger.error(f"Error writing description to files: {e}")

# Create/initialize description files if enabled
if SAVE_DESCRIPTIONS:
    logger.info(f"Descriptions will be saved to: {DESCRIPTIONS_FILE} and {DESCRIPTIONS_HTML_FILE}")

# --- Helper function for screen capture ---
def _capture_screen_frame():
    try:
        with mss.mss() as sct:
            # sct.monitors[0] is the entire virtual screen, [1] is the primary monitor
            # Using [1] for primary monitor as it's often what's intended for "screen"
            monitor = sct.monitors[1] 
            sct_img = sct.grab(monitor)

            # Convert to PIL Image
            img = PILImage.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)

            # Save frame as image file if enabled
            if SAVE_FRAMES:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
                filename = f"frame_{timestamp}.jpg"
                filepath = os.path.join(FRAMES_DIR, filename)
                img.save(filepath, format="JPEG", quality=85)
                logger.debug(f"Saved frame to: {filepath}")

            # Save to BytesIO as JPEG for Gemini
            image_io = io.BytesIO()
            img.save(image_io, format="JPEG")
            image_io.seek(0)
            image_bytes = image_io.read()

            return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}
    except Exception as e:
        logger.error(f"Error capturing screen: {e}")
        return None

# --- Gemini Interaction Functions ---
async def send_screen_loop(session, app: web.Application):
    """Periodically captures and sends screen frames to Gemini."""
    logger.info("Starting to send screen frames to Gemini.")
    frame_count = 0
    try:
        while app.get("gemini_streaming_task_running", True):
            frame_data = await asyncio.to_thread(_capture_screen_frame)
            if frame_data:
                try:
                    # frame_data is {"mime_type": "image/jpeg", "data": base64_encoded_string}
                    # The send_realtime_input method expects image data via the 'media' parameter.
                    await session.send_realtime_input(media=frame_data)
                    logger.debug("Sent screen frame to Gemini.")
                    
                    frame_count += 1
                    # Ask for description every 3rd frame (increased frequency)
                    if frame_count % 3 == 0:
                        await session.send_realtime_input(text="Describe what you see on the screen in detail.")
                        logger.info(f"Sent description request at frame {frame_count}")
                        
                except Exception as e:
                    logger.error(f"Error sending frame to Gemini: {e}")
                    # If it's a connection error, stop the loop
                    if "ConnectionClosedError" in str(type(e)) or "timeout" in str(e).lower():
                        logger.error("Connection lost, stopping screen capture loop")
                        app["gemini_streaming_task_running"] = False
                        break
                    # For other errors, log and continue
                    logger.warning("Continuing despite send error...")
                    
            else:
                logger.warning("Failed to capture/send screen frame.")
            await asyncio.sleep(SCREEN_CAPTURE_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Screen sending loop cancelled.")
    except Exception as e:
        logger.error(f"Error in send_screen_loop: {e}")
        traceback.print_exc()
        # Signal to stop the streaming task
        app["gemini_streaming_task_running"] = False
    finally:
        logger.info("Screen sending loop stopped.")

async def receive_gemini_responses_loop(session, app: web.Application):
    """Receives and logs responses from Gemini."""
    logger.info("Starting to listen for Gemini responses.")
    try:
        while app.get("gemini_streaming_task_running", True):
            try:
                async for response in session.receive():
                    if not app.get("gemini_streaming_task_running", True):
                        break
                    
                    # Try to get text from the response
                    response_text = None
                    try:
                        # Check if response has text attribute and it's not empty
                        if hasattr(response, 'text') and response.text:
                            response_text = response.text.strip()
                            logger.info(f"Gemini response (text): {response_text}")
                            
                            # Save description to file if enabled
                            if SAVE_DESCRIPTIONS and response_text:
                                try:
                                    save_description_to_files(response_text)
                                except Exception as e:
                                    logger.error(f"Error writing description to files: {e}")
                        
                        # If no direct text, try to get text from parts
                        elif hasattr(response, 'parts') and response.parts:
                            text_parts = []
                            for part in response.parts:
                                if hasattr(part, 'text') and part.text:
                                    text_parts.append(part.text.strip())
                            if text_parts:
                                response_text = ' '.join(text_parts).strip()
                                logger.info(f"Gemini response (from parts): {response_text}")
                                
                                # Save description to file if enabled
                                if SAVE_DESCRIPTIONS and response_text:
                                    try:
                                        save_description_to_files(response_text)
                                    except Exception as e:
                                        logger.error(f"Error writing description to files: {e}")
                        
                        # Log if we didn't find any text
                        if not response_text:
                            logger.debug(f"Received non-text response from Gemini. Response type: {type(response)}")
                        
                    except Exception as e:
                        logger.warning(f"Error extracting text from Gemini response: {e}")
                    
                    # Handle audio/data responses
                    if hasattr(response, 'data') and response.data:
                        logger.debug("Received audio data from Gemini.")
                
                # If we exit the async for loop, it means the session receive() generator ended
                # This could be normal session completion or an error
                logger.info("Session receive() generator completed, checking if we should continue...")
                
                # Small delay before trying to receive again
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in receive loop iteration: {e}")
                # Don't break immediately, try to continue unless it's a critical error
                if "ConnectionClosedError" in str(type(e)):
                    logger.error("Connection closed, stopping receive loop")
                    break
                await asyncio.sleep(1)  # Wait a bit before retrying
                
    except asyncio.CancelledError:
        logger.info("Gemini response receiving loop cancelled.")
    except Exception as e:
        logger.error(f"Error in receive_gemini_responses_loop: {e}")
        traceback.print_exc()
        # If there is an error with receiving, we might want to stop the streaming
        app["gemini_streaming_task_running"] = False
    finally:
        logger.info("Gemini response receiving loop stopped.")


async def run_gemini_screen_interaction(app: web.Application):
    """Main task to manage screen streaming to Gemini."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set. Screen streaming to Gemini will not start.")
        return

    client = genai.Client(api_key=api_key)
    app["gemini_streaming_task_running"] = True
    logger.info("Attempting to connect to Gemini for screen streaming...")

    try:
        async with client.aio.live.connect(model=GEMINI_MODEL_NAME, config=GEMINI_CONFIG) as session:
            logger.info(f"Successfully connected to Gemini model: {GEMINI_MODEL_NAME}")
            app["gemini_session"] = session

            # Ask Gemini to describe the screen
            initial_prompt = "You are viewing a computer screen. Please describe what you see when I send you screen captures. Transcribe the important text that is changing as the user interacts with the system."
            await session.send_realtime_input(text=initial_prompt)
            logger.info(f"Sent initial prompt to Gemini")
            
            async with asyncio.TaskGroup() as tg:
                tg.create_task(send_screen_loop(session, app))
                tg.create_task(receive_gemini_responses_loop(session, app))
            # TaskGroup will wait for all tasks to complete here
            # This point is reached if both tasks finish (e.g., due to cancellation or natural completion)
            
    except asyncio.CancelledError:
        logger.info("Gemini screen interaction task was cancelled.")
    except Exception as e:
        logger.error(f"Failed to connect or run Gemini screen interaction: {e}")
        traceback.print_exc()
        # Wait a bit before the task ends to avoid rapid restart attempts
        await asyncio.sleep(5)
    finally:
        logger.info("Gemini screen interaction task finished or was terminated.")
        app["gemini_streaming_task_running"] = False # Ensure flag is cleared
        if "gemini_session" in app:
            app.pop("gemini_session", None)  # Remove the session reference


async def start_gemini_streaming_background_task(app: web.Application):
    """aiohttp startup task to launch Gemini streaming."""
    app['gemini_screen_stream_task'] = asyncio.create_task(run_gemini_screen_interaction(app))
    logger.info("Gemini screen streaming background task created.")

async def cleanup_gemini_streaming_background_task(app: web.Application):
    """aiohttp cleanup task to stop Gemini streaming."""
    logger.info("Attempting to cleanup Gemini screen streaming background task.")
    if 'gemini_screen_stream_task' in app:
        if app.get("gemini_streaming_task_running", False): # Check if it was meant to be running
            app["gemini_streaming_task_running"] = False # Signal loops to stop

        task = app['gemini_screen_stream_task']
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("Gemini screen stream background task successfully cancelled.")
            except Exception as e:
                logger.error(f"Error during Gemini task cancellation: {e}")
        else:
            logger.info("Gemini screen stream background task was already done.")
    else:
        logger.info("No Gemini screen streaming task found to cleanup.")

# --- Existing WebRTC Code ---
async def handle_options(request):
    return web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logger.info(f"{pc_id} {msg}", *args)

    log_info("Created for {}", request.remote)

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is {}", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        log_info("Track {} received", track.kind)

        if track.kind == "video":
            # This is where you would typically process the video track
            # For example, save to a file, perform analysis, etc.
            # For this example, we'll just log and relay it (if configured)
            # local_video = relay.subscribe(track) # Example of relaying
            pass # Placeholder for actual video processing

        @track.on("ended")
        async def on_ended():
            log_info("Track {} ended", track.kind)
            # You might want to do cleanup here

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
        headers={
            "Access-Control-Allow-Origin": "*",  # Allows all origins
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

if __name__ == "__main__":
    # Configure Loguru with detailed timestamps
    logger.remove() # Removes the default handler
    
    # Add a new handler with detailed timestamp format
    logger.add(
        sys.stderr, 
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Also add a file logger for persistent logs
    log_filename = f"server_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger.add(
        log_filename,
        level="DEBUG", 
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="7 days",  # Keep logs for 7 days
        compression="zip"  # Compress old logs
    )
    
    logger.info(f"Server starting up at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Logs will be saved to: {log_filename}")

    app = web.Application()
    
    # Add Gemini streaming lifecycle handlers
    app.on_startup.append(start_gemini_streaming_background_task)
    app.on_cleanup.append(cleanup_gemini_streaming_background_task)
    
    app.on_shutdown.append(on_shutdown)
    app.router.add_post("/offer", offer)
    app.router.add_route("OPTIONS", "/offer", handle_options)
    web.run_app(app, access_log=None, host="0.0.0.0", port=8080) 