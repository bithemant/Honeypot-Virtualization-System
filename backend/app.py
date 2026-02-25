from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
from simulator import VirtualShell, FLAGS, MAX_SCORE
import datetime

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = 'secret!'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Store sessions for connected users
# session_id -> VirtualShell instance
sessions = {}

# Banned IPs
banned_ips = set()

# Logs store
# List of { timestamp, ip, command, output }
command_logs = []

@app.route('/')
def index():
    # Redirect to login by default, or serve index if logged in (frontend handles auth check)
    return app.send_static_file('login.html')

@app.route('/<path:path>')
def serve_static(path):
    return app.send_static_file(path)

@app.route('/api/logs')
def get_logs():
    return jsonify(command_logs)

@app.route('/api/flags')
def get_flags():
    """Return flag details for admin reference"""
    flag_list = []
    for path, info in FLAGS.items():
        flag_list.append({
            'path': path,
            'points': info['points'],
            'difficulty': info.get('difficulty', 'Unknown'),
            'flag': info['content']
        })
    flag_list.sort(key=lambda x: x['points'])
    return jsonify({'flags': flag_list, 'max_score': MAX_SCORE, 'total_flags': len(FLAGS)})

@app.route('/api/scores')
def get_scores():
    """Return current scores of all active sessions"""
    scores = []
    for sid, session_data in sessions.items():
        shell = session_data['shell']
        scores.append({
            'sid': sid,
            'ip': session_data['ip'],
            'alias': session_data.get('alias', 'Unknown'),
            'score': shell.score,
            'flags_found': len(shell.found_flags),
            'total_flags': len(FLAGS),
            'max_score': MAX_SCORE
        })
    scores.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(scores)

@socketio.on('ping')
def handle_ping():
    emit('pong', {'time': datetime.datetime.now().isoformat()})

@socketio.on('connect')
def handle_connect():
    try:
        sid = request.sid
        client_ip = request.remote_addr
        
        # FOR TESTING: If localhost, generate a random fake IP so we can test banning multiple "users"
        if client_ip == '127.0.0.1':
            import random
            client_ip = f"10.0.0.{random.randint(10, 200)}"
            
        # Get Alias from query args
        alias = request.args.get('alias', 'Unknown')
            
        print(f"Client connected: {sid} from {client_ip} as {alias}")
        
        if client_ip in banned_ips:
            print(f"Banned IP tried to connect: {client_ip}")
            # Emit disconnect immediately
            socketio.emit('server_force_disconnect', {'reason': 'YOU HAVE BEEN BANNED'}, room=sid)
            socketio.sleep(0.5) # Give time for message to reach client
            disconnect(sid)
            return

        # Store shell AND ip AND alias
        sessions[sid] = {
            'shell': VirtualShell(),
            'ip': client_ip,
            'alias': alias
        }
        
        # Notify admin of new session
        socketio.emit('session_update', {
            'sid': sid, 
            'ip': client_ip,
            'alias': alias,
            'status': 'connected' 
        })
        
        emit('response', {'output': '', 'prompt': sessions[sid]['shell'].get_prompt()})
    except Exception as e:
        print(f"ERROR in handle_connect: {e}")
        import traceback
        traceback.print_exc()

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"Client disconnected: {sid}")
    if sid in sessions:
        del sessions[sid]
        # Notify admin
        socketio.emit('session_update', {
            'sid': sid, 
            'status': 'disconnected' 
        })

@socketio.on('command')
def handle_command(data):
    try:
        sid = request.sid
        cmd = data.get('command')
        print(f"Received command from {sid}: {cmd}")
        
        if sid not in sessions:
            # Re-init if lost (shouldn't happen often)
            sessions[sid] = {
                'shell': VirtualShell(),
                'ip': request.remote_addr,
                'alias': request.args.get('alias', 'Unknown')
            }
        
        shell = sessions[sid]['shell']
        
        # Log the command
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'ip': sessions[sid]['ip'], 
            'session_id': sid,
            'command': cmd,
            'cwd': shell.cwd
        }
        command_logs.append(log_entry)
        
        # Execute
        output = shell.execute_command(cmd)
        print(f"Command output: {output}")
    
        # Special handling for exit/clear from simulator
        if output == "__EXIT__":
            disconnect(sid)
            return
        
        # Check for CTF Flag Discovery
        if shell.last_flag_found:
            flag_data = shell.last_flag_found
            # Calculate time bonus (seconds since start)
            time_taken = (datetime.datetime.now() - shell.start_time).total_seconds()
            
            # Emit to User
            emit('flag_found', {
                'path': flag_data['path'],
                'points': flag_data['points'],
                'total_score': flag_data['total_score'],
                'time_taken': f"{time_taken:.1f}s"
            })
            
            # Notify Admin of score update
            socketio.emit('score_update', {
                'sid': sid,
                'score': shell.score,
                'flags_count': len(shell.found_flags)
            })
            
            # Reset flag found state
            shell.last_flag_found = None
    
        # Check for User-to-Admin Message
        if output and output.startswith("__MSG__"):
            user_msg = output[7:]  # Strip __MSG__ prefix
            socketio.emit('user_message', {
                'sid': sid,
                'ip': sessions[sid]['ip'],
                'alias': sessions[sid].get('alias', 'Unknown'),
                'message': user_msg,
                'timestamp': datetime.datetime.now().isoformat()
            })
            output = "\x1b[32m[✓] Message sent to admin.\x1b[0m"
    
        # Check for Flag Submit signal
        if output and output.startswith("__SUBMIT__"):
            flag_text = output[10:]
            output = f"\x1b[1;32m[✓] FLAG ACCEPTED: {flag_text}\x1b[0m"
    
        # Send response
        emit('response', {
            'output': output,
            'prompt': shell.get_prompt()
        })
        
        # Also broadcast new log to any admin listening
        socketio.emit('new_log', log_entry)

    except Exception as e:
        print(f"ERROR in handle_command: {e}")
        import traceback
        traceback.print_exc()
        # Send error to frontend so it doesn't hang
        emit('response', {'output': f"\n\x1b[31m[SERVER ERROR] {str(e)}\x1b[0m\n", 'prompt': None})

@socketio.on('admin_action')
def handle_admin_action(data):
    # In real app, verify admin token here
    action = data.get('action')
    target_sid = data.get('sid')
    
    if action == 'kick':
        if target_sid in sessions:
            # Emit disconnect signal to that specific client
            socketio.emit('server_force_disconnect', {'reason': 'Kicked by Admin'}, room=target_sid)
            # allow time for client to receive
            socketio.sleep(1) 
            disconnect(target_sid)

    elif action == 'ban':
        if target_sid in sessions:
            target_ip = sessions[target_sid]['ip']
            banned_ips.add(target_ip)
            print(f"Banning IP: {target_ip}")
            socketio.emit('server_force_disconnect', {'reason': 'YOU HAVE BEEN BANNED'}, room=target_sid)
            socketio.sleep(1) 
            disconnect(target_sid)
            
    elif action == 'message':
        msg = data.get('message')
        if target_sid in sessions:
            socketio.emit('server_message', {'message': msg}, room=target_sid)
            
    elif action == 'execute':
        cmd = data.get('command')
        if target_sid in sessions:
             # We want the CLIENT to run this, so they see it in their terminal
             socketio.emit('server_exec', {'command': cmd}, room=target_sid)

    elif action == 'get_banned':
        # Send list of banned IPs back to admin
        # requesting_sid = request.sid # This is the ADMIN's sid
        # We can just emit back to sender
        emit('banned_list', {'ips': list(banned_ips)})

    elif action == 'unban':
        ip_to_unban = data.get('ip')
        if ip_to_unban in banned_ips:
            banned_ips.remove(ip_to_unban)
            print(f"Unbanned IP: {ip_to_unban}")
            emit('banned_list', {'ips': list(banned_ips)}) # Update list

    elif action == 'rename':
        new_name = data.get('name')
        if target_sid in sessions:
            sessions[target_sid]['alias'] = new_name
            # Notify admin to update UI
            # We can re-emit session_update or a specific rename event
            # Re-emitting session_update is easiest if we include everything
            s = sessions[target_sid]
            socketio.emit('session_update', {
                'sid': target_sid,
                'ip': s['ip'],
                'alias': new_name,
                'status': 'connected' # effectively just an update
            })
            # Optionally notify user their name changed?
            socketio.emit('server_message', {'message': f'ADMIN CHANGED YOUR ALIAS TO: {new_name}'}, room=target_sid)



if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
