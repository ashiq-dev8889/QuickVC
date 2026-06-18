import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# Operational Memory Storage Matrix: { room_id: { user_id: WebSocket } }
active_rooms = {}

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickVC - Premium Python Voice Ecosystem</title>
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #030704 0%, #0d140f 100%);
            --accent-green: #00ff66;
            --accent-glow: rgba(0, 255, 102, 0.35);
            --glass-bg: rgba(10, 20, 14, 0.7);
            --glass-border: rgba(0, 255, 102, 0.12);
            --text-main: #f1f5f2;
            --text-muted: #788a7e;
            --danger: #ff3b30;
            --surface: rgba(0, 0, 0, 0.5);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
        }

        body {
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 16px;
        }

        header { text-align: center; margin-bottom: 24px; }
        header h1 {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(180deg, #ffffff 0%, #a3ffa3 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 20px var(--accent-glow));
        }
        header p { color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px;}

        .app-container {
            background: var(--glass-bg);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid var(--glass-border);
            border-radius: 28px;
            width: 100%;
            max-width: 420px;
            height: 560px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.8);
        }

        .view { display: none; flex-direction: column; height: 100%; padding: 24px; }
        .view.active { display: flex; }

        .lobby-content { display: flex; flex-direction: column; justify-content: center; height: 100%; gap: 20px; }
        .input-wrapper { display: flex; flex-direction: column; gap: 8px; }
        .input-wrapper label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); }
        
        input {
            width: 100%;
            padding: 16px;
            background: var(--surface);
            border: 1px solid var(--glass-border);
            border-radius: 14px;
            color: #fff;
            font-size: 1rem;
            outline: none;
        }
        input:focus { border-color: var(--accent-green); }
        .room-input { text-align: center; letter-spacing: 2px; font-family: monospace; font-size: 1.2rem; }

        .btn-stack { display: flex; flex-direction: column; gap: 12px; }
        button {
            width: 100%; padding: 16px; border-radius: 14px; border: none; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.2s ease;
        }
        button.primary { background: var(--accent-green); color: #030704; box-shadow: 0 4px 20px rgba(0, 255, 102, 0.25); }
        button.secondary { background: rgba(255, 255, 255, 0.04); color: var(--text-main); border: 1px solid rgba(255, 255, 255, 0.08); }
        button.danger { background: rgba(255, 59, 48, 0.15); color: #ff453a; border: 1px solid rgba(255, 59, 48, 0.2); }
        button:disabled { opacity: 0.35; cursor: not-allowed; }

        /* Voice Chat Screen Styles */
        .room-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
        .status-badge { display: flex; align-items: center; gap: 6px; font-size: 0.75rem; background: rgba(0, 255, 102, 0.1); padding: 6px 12px; border-radius: 20px; color: var(--accent-green); font-weight: 600; }
        .pulse-dot { width: 6px; height: 6px; background: var(--accent-green); border-radius: 50%; }

        .user-feed-stack { flex: 1; overflow-y: auto; margin: 16px 0; display: flex; flex-direction: column; gap: 10px; }
        .native-member-card { display: flex; align-items: center; justify-content: space-between; background: rgba(255, 255, 255, 0.03); padding: 12px 14px; border-radius: 16px; border: 1px solid var(--glass-border); }
        .member-profile { display: flex; align-items: center; gap: 12px; }
        .member-avatar { width: 40px; height: 40px; border-radius: 50%; background: #112217; border: 1.5px solid var(--accent-green); display: flex; align-items: center; justify-content: center; font-weight: 700; color: var(--accent-green); }

        .bottom-dock-controls { display: grid; grid-template-columns: 1.2fr 1fr; gap: 12px; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 16px; }
    </style>
</head>
<body>

    <header>
        <h1>QuickVC 🚂</h1>
        <p>Python Signaled Audio Grid</p>
    </header>

    <div class="app-container">
        <div id="lobbyView" class="view active">
            <div class="lobby-content">
                <div class="input-wrapper">
                    <label>Identity Handle</label>
                    <input type="text" id="usernameInput" placeholder="Your name...">
                </div>
                <div class="input-wrapper">
                    <label>10-Digit Channel Code</label>
                    <input type="text" id="roomCodeInput" class="room-input" placeholder="0000000000" maxlength="10">
                </div>
                <div class="btn-stack">
                    <button id="joinRoomBtn" class="primary" disabled>⚡ Connect to Channel</button>
                    <button id="createRoomBtn" class="secondary">💎 Generate Code</button>
                </div>
            </div>
        </div>

        <div id="roomView" class="view">
            <div class="room-header">
                <div>
                    <h3 id="currentUserNameDisplay">Active Member</h3>
                    <p id="roomCodeDisplay" style="font-family: monospace; color: var(--accent-green); font-size: 0.85rem; margin-top:2px;"></p>
                </div>
                <div class="status-badge"><div class="pulse-dot"></div>Live</div>
            </div>

            <div class="user-feed-stack" id="usersContainer"></div>

            <div class="bottom-dock-controls">
                <button id="selfMuteBtn" class="secondary">🎙️ Mute mic</button>
                <button id="exitRoomBtn" class="danger">🚪 Disconnect</button>
            </div>
        </div>
    </div>

    <div id="audioSpeakerEcosystemMixer" style="display:none;"></div>

    <script>
        const iceServers = { iceServers: [{ urls: ['stun:stun1.l.google.com:19302', 'stun:stun2.l.google.com:19302'] }] };
        let ws = null;
        let localStream = null;
        let peerConnections = {}; 
        
        let myUserId = "usr_" + Math.floor(1000 + Math.random() * 9000);
        let myUsername = "";
        let targetRoomCode = "";
        let isMuted = false;

        const lobbyView = document.getElementById('lobbyView');
        const roomView = document.getElementById('roomView');
        const usernameInput = document.getElementById('usernameInput');
        const roomCodeInput = document.getElementById('roomCodeInput');
        const joinRoomBtn = document.getElementById('joinRoomBtn');
        const createRoomBtn = document.getElementById('createRoomBtn');
        const usersContainer = document.getElementById('usersContainer');
        const roomCodeDisplay = document.getElementById('roomCodeDisplay');
        const selfMuteBtn = document.getElementById('selfMuteBtn');
        const exitRoomBtn = document.getElementById('exitRoomBtn');
        const audioSpeakerEcosystemMixer = document.getElementById('audioSpeakerEcosystemMixer');

        function formUpdate() {
            joinRoomBtn.disabled = !(usernameInput.value.trim().length >= 2 && roomCodeInput.value.length === 10);
        }
        usernameInput.addEventListener('input', formUpdate);
        roomCodeInput.addEventListener('input', () => {
            roomCodeInput.value = roomCodeInput.value.replace(/[^0-9]/g, '');
            formUpdate();
        });

        createRoomBtn.onclick = () => {
            let code = "";
            for(let i=0; i<10; i++) code += Math.floor(Math.random() * 10).toString();
            roomCodeInput.value = code;
            formUpdate();
        };

        joinRoomBtn.onclick = async () => {
            myUsername = usernameInput.value.trim();
            targetRoomCode = roomCodeInput.value.trim();

            try {
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            } catch(e) {
                return alert("Microphone access is mandatory.");
            }

            // Establish real-time signaling backbone websocket pipeline
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/${targetRoomCode}/${myUserId}`);

            ws.onopen = () => {
                lobbyView.classList.remove('active');
                roomView.classList.add('active');
                roomCodeDisplay.innerText = `NODE ID: ${targetRoomCode}`;
                
                // Inform the rest of the node architecture that a new peer has compiled
                ws.send(jsonPackage("join", { name: myUsername }));
            };

            ws.onmessage = async (event) => {
                const packet = JSON.parse(event.data);
                const senderId = packet.sender;

                if (packet.type === "user_list") {
                    renderGrid(packet.data.users);
                }
                else if (packet.type === "peer_joined") {
                    // Initialize peer WebRTC connection and deliver offer description mapping
                    initiateWebRTCPairing(senderId, true);
                }
                else if (packet.type === "offer") {
                    let pc = initiateWebRTCPairing(senderId, false);
                    await pc.setRemoteDescription(new RTCSessionDescription(packet.data));
                    let answer = await pc.createAnswer();
                    await pc.setLocalDescription(answer);
                    ws.send(jsonPackage("answer", answer, senderId));
                }
                else if (packet.type === "answer") {
                    if (peerConnections[senderId]) {
                        await peerConnections[senderId].setRemoteDescription(new RTCSessionDescription(packet.data));
                    }
                }
                else if (packet.type === "ice_candidate") {
                    if (peerConnections[senderId]) {
                        await peerConnections[senderId].addIceCandidate(new RTCIceCandidate(packet.data)).catch(e => {});
                    }
                }
            };
        };

        function jsonPackage(type, data, target = null) {
            return JSON.stringify({ type, data, sender: myUserId, target });
        }

        function initiateWebRTCPairing(peerId, createOffer) {
            if (peerConnections[peerId]) return peerConnections[peerId];

            const pc = new RTCPeerConnection(iceServers);
            peerConnections[peerId] = pc;

            localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

            pc.onicecandidate = (e) => {
                if (e.candidate) ws.send(jsonPackage("ice_candidate", e.candidate, peerId));
            };

            pc.ontrack = (e) => {
                let aud = document.getElementById(`speaker-${peerId}`);
                if(!aud) {
                    aud = document.createElement('audio');
                    aud.id = `speaker-${peerId}`;
                    aud.autoplay = true;
                    audioSpeakerEcosystemMixer.appendChild(aud);
                }
                aud.srcObject = e.streams[0];
            };

            if (createOffer) {
                pc.onnegotiationneeded = async () => {
                    let offer = await pc.createOffer();
                    await pc.setLocalDescription(offer);
                    ws.send(jsonPackage("offer", offer, peerId));
                };
            }

            return pc;
        }

        function renderGrid(users) {
            usersContainer.innerHTML = "";
            users.forEach(user => {
                const card = document.createElement('div');
                card.className = "native-member-card";
                card.innerHTML = `
                    <div class="member-profile">
                        <div class="member-avatar">${user.name.substring(0,2).toUpperCase()}</div>
                        <div>
                            <div class="m-name">${user.name} ${user.id === myUserId ? '(You)' : ''}</div>
                            <div style="font-size:0.75rem; color:var(--text-muted);">Connected</div>
                        </div>
                    </div>
                `;
                usersContainer.appendChild(card);
            });
        }

        selfMuteBtn.onclick = () => {
            isMuted = !isMuted;
            localStream.getAudioTracks()[0].enabled = !isMuted;
            selfMuteBtn.innerText = isMuted ? "🔇 Unmute mic" : "🎙️ Mute mic";
            selfMuteBtn.className = isMuted ? "danger" : "secondary";
        };

        exitRoomBtn.onclick = () => {
            if(ws) ws.close();
            if(localStream) localStream.getTracks().forEach(t => t.stop());
            Object.keys(peerConnections).forEach(k => peerConnections[k].close());
            window.location.reload();
        };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return HTMLResponse(content=HTML_CONTENT)

@app.websocket("/ws/{room_code}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_id: str):
    await websocket.accept()
    
    if room_code not in active_rooms:
        active_rooms[room_code] = {}
        
    # Store peer routing properties parameters
    active_rooms[room_code][user_id] = {
        "socket": websocket,
        "name": "Anonymous"
    }

    try:
        while True:
            raw_payload = await websocket.receive_text()
            packet = json.loads(raw_payload)
            
            # Action event routing matrix handler
            if packet["type"] == "join":
                active_rooms[room_code][user_id]["name"] = packet["data"]["name"]
                await broadcast_room_manifest(room_code)
                await alert_peers_of_arrival(room_code, user_id)
                
            elif packet["type"] in ["offer", "answer", "ice_candidate"]:
                target_peer = packet["target"]
                if target_peer in active_rooms[room_code]:
                    await active_rooms[room_code][target_peer]["socket"].send_text(json.dumps(packet))

    except WebSocketDisconnect:
        # Perform memory cleanup configurations automatically upon hardware dropouts
        if room_code in active_rooms and user_id in active_rooms[room_code]:
            del active_rooms[room_code][user_id]
            if not active_rooms[room_code]:
                del active_rooms[room_code]
            else:
                await broadcast_room_manifest(room_code)

async def broadcast_room_manifest(room_code):
    """Sends list of connected names and IDs within a target node ecosystem."""
    if room_code not in active_rooms: return
    user_list = [{"id": uid, "name": meta["name"]} for uid, meta in active_rooms[room_code].items()]
    
    packet = json.dumps({"type": "user_list", "data": {"users": user_list}, "sender": "server"})
    for client in active_rooms[room_code].values():
        await client["socket"].send_text(packet)

async def alert_peers_of_arrival(room_code, fresh_user_id):
    """Alerts pre-existing room connections to initiate WebRTC setups."""
    packet = json.dumps({"type": "peer_joined", "data": {}, "sender": fresh_user_id})
    for uid, client in active_rooms[room_code].items():
        if uid != fresh_user_id:
            await client["socket"].send_text(packet)

if __name__ == "__main__":
    import uvicorn
    # Bind to environment assigned deployment ports mapped on Railway
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("index.py:app", host="0.0.0.0", port=port, reload=True)
