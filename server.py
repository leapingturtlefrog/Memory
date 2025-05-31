import asyncio
import logging
import uuid
import json
from aiohttp import web
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay

# For simplicity, we'll keep track of peer connections in memory.
pcs = set()
relay = MediaRelay() # Used to relay tracks if needed, or can be adapted to save to file

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
        logging.info(pc_id + " " + msg, *args)

    log_info("Created for %s", request.remote)

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)

        if track.kind == "video":
            # This is where you would typically process the video track
            # For example, save to a file, perform analysis, etc.
            # For this example, we'll just log and relay it (if configured)
            # local_video = relay.subscribe(track) # Example of relaying
            pass # Placeholder for actual video processing

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
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
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_post("/offer", offer)
    app.router.add_route("OPTIONS", "/offer", handle_options)
    web.run_app(app, access_log=None, host="0.0.0.0", port=8080) 