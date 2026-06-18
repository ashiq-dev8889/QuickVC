import os
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
# Enable cross-origin accessibility for deployment
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickVC - Premium Voice Grid</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
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
        header p { color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px; }

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

        /* Discord Style Voice Room UI Elements */
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
        <p>SocketIO Premium Ecosystem</p>
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
                <div class="status-badge"><div class="pulse-dot"></div>Connected</div>
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
        // STUN configurations for clean WebRTC P2P NAT traverse parameters
        const iceServers = { iceServers: [{ urls: ['stun:stun1.l.google.com:19302', 'stun:stun2.l.google.com:19302'] }] };
        const socket = io.connect(location.origin);
        
        let localStream = null;
        let peerConnections = {}; 
        
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
        const currentUserNameDisplay = document.getElementById('currentUserNameDisplay');
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
                // Explicitly prompt microhpone & implicit speaker channel configurations
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            } catch(e) {
                return alert("Microphone hardware authorizations are strictly mandatory.");
            }

            // Bind SocketIO structural parameters 
            socket.emit('join_room', { room: targetRoomCode, username: myUsername });

            lobbyView.classList.remove('active');
            roomView.classList.add('active');
            roomCodeDisplay.innerText = `NODE: ${targetRoomCode}`;
            currentUserNameDisplay.innerText = myUsername;
        };

        // --- SocketIO Intercept Signalling Layer Grid ---
        socket.on('user_list', (data) => {
            renderGrid(data.users);
        });

        socket.on('peer_joined', (data) => {
            // Initiate WebRTC offer pipeline when an external endpoint maps to the room
            initiateWebRTCPairing(data.sid, data.username, true);
        });

        socket.on('signal', async (data) => {
            const senderSid = data.sender_sid;
            
            if (data.sdp) {
                let pc = initiateWebRTCPairing(senderSid, data.sender_name, false);
                await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
                
                if (data.sdp.type === 'offer') {
                    const answer = await pc.createAnswer();
                    await pc.setLocalDescription(answer);
                    socket.emit('signal', { room: targetRoomCode, target_sid: senderSid, sdp: pc.localDescription });
                }
            } else if (data.ice) {
                if (peerConnections[senderSid]) {
                    await peerConnections[senderSid].addIceCandidate(new RTCIceCandidate(data.ice)).catch(e => {});
                }
            }
        });

        socket.on('peer_left', (data) => {
            if (peerConnections[data.sid]) {
                peerConnections[data.sid].close();
                delete peerConnections[data.sid];
            }
            const el = document.getElementById(`speaker-${data.sid}`);
            if(el) el.remove();
        });

        // --- Core WebRTC Audio Mixer Engine ---
        function initiateWebRTCPairing(peerSid, peerName, createOffer) {
            if (peerConnections[peerSid]) return peerConnections[peerSid];

            const pc = new RTCPeerConnection(iceServers);
            peerConnections[peerSid] = pc;

            localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

            pc.onicecandidate = (e) => {
                if (e.candidate) {
                    socket.emit('signal', { room: targetRoomCode, target_sid: peerSid, ice: e.candidate });
                }
            };

            pc.ontrack = (e) => {
                let aud = document.getElementById(`speaker-${peerSid}`);
                if(!aud) {
                    aud = document.createElement('audio');
                    aud.id = `speaker-${peerSid}`;
                    aud.autoplay = true;
                    audioSpeakerEcosystemMixer.appendChild(aud);
                }
                aud.srcObject = e.streams[0];
            };

            if (createOffer) {
                pc.onnegotiationneeded = async () => {
                    let offer = await pc.createOffer();
                    await pc.setLocalDescription(offer);
                    socket.emit('signal', { room: targetRoomCode, target_sid: peerSid, sdp: pc.localDescription });
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
                        <div class="member-avatar">${user.username.substring(0,2).toUpperCase()}</div>
                        <div>
                            <div class="m-name">${user.username} ${user.sid === socket.id ? '(You)' : ''}</div>
                            <div style="font-size:0.75rem; color:var(--text-muted);">Active Node</div>
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
            window.location.reload();
        };
    </script>
</body>
</html>
"""

# Structural in-memory runtime store: { room_code: { session_id: username } }
room_directory = {}

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    username = data['username']
    sid = request.sid

    join_room(room)
    
    if room not in room_directory:
        room_directory[room] = {}
    room_directory[room][sid] = username

    # 1. Alert old members to initiate WebRTC pipeline links with new node identity
    emit('peer_joined', {'sid': sid, 'username': username}, to=room, include_self=False)
    
    # 2. Push full current room roster to everybody for native visual sync structures
    sync_room_manifest(room)

@socketio.on('signal')
def handle_signal_routing(data):
    room = data['room']
    target_sid = data['target_sid']
    sid = request.sid
    
    payload = {
        'sender_sid': sid,
        'sender_name': room_directory.get(room, {}).get(sid, 'Anonymous')
    }
    
    if 'sdp' in data:
        payload['sdp'] = data['sdp']
    if 'ice' in data:
        payload['ice'] = data['ice']

    # Route WebRTC signaling directly to the specific target peer session
    emit('signal', payload, to=target_sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for room, users in list(room_directory.items()):
        if sid in users:
            username = users[sid]
            del users[sid]
            leave_room(room)
            
            emit('peer_left', {'sid': sid, 'username': username}, to=room)
            
            if not users:
                del room_directory[room]
            else:
                sync_room_manifest(room)
            break

def sync_room_manifest(room):
    users_list = [{'sid': sid, 'username': name} for sid, name in room_directory.get(room, {}).items()]
    emit('user_list', {'users': users_list}, to=room)

# Railway automatically sets up and uses a Procfile if present,
# but we retain this block as a secondary safeguard for local tests.
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
