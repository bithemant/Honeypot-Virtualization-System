// Check Login
const currentUser = sessionStorage.getItem('attacker_user');
const currentAlias = sessionStorage.getItem('attacker_alias') || 'Unknown'; // Default if missing

if (!currentUser) {
    window.location.href = 'login.html';
}

// Initialize Socket.IO
// Connect to the same host that served the page (handles both localhost and cloudflare)
const socket = io({
    query: {
        alias: currentAlias
    }
});
socket.on('connect_error', (err) => {
    console.error('Connection Error:', err);
    term.write(`\r\n\x1b[31m[ERROR] Connection Failed: ${err.message}\x1b[0m\r\n`);
});

const statusSpan = document.getElementById('connection-status');
const logList = document.getElementById('log-list');

// Initialize Xterm.js
const term = new Terminal({
    cursorBlink: true,
    fontFamily: 'Courier New, monospace',
    fontSize: 14,
    theme: {
        background: '#0a0a0a',
        foreground: '#00ff00',
        cursor: '#00ff00'
    }
});

const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.open(document.getElementById('terminal'));
fitAddon.fit();
term.focus();

// Ensure focus on click
document.getElementById('terminal').addEventListener('click', () => {
    term.focus();
});

// Handle resizing
window.addEventListener('resize', () => fitAddon.fit());

// Shell state
let commandBuffer = '';
let prompt = `${currentUser}@ubuntu-server:/# `;
let isConnected = true;

// Writing helper
function writePrompt() {
    term.write('\r\n' + prompt);
}

term.write(`Connecting as ${currentUser}...\r\n`);

// Socket Events
// CTF Events
let currentScore = 0;
let flagsFound = 0;
const MAX_SCORE = 440;
const TOTAL_FLAGS = 10;

function updateScoreBar() {
    const scoreDisplay = document.getElementById('score-display');
    const flagsDisplay = document.getElementById('flags-display');
    const scoreProgress = document.getElementById('score-progress');
    if (scoreDisplay) scoreDisplay.textContent = `SCORE: ${currentScore}`;
    if (flagsDisplay) flagsDisplay.textContent = `FLAGS: ${flagsFound}/${TOTAL_FLAGS}`;
    if (scoreProgress) scoreProgress.style.width = `${Math.min((currentScore / MAX_SCORE) * 100, 100)}%`;
}

socket.on('flag_found', (data) => {
    currentScore = data.total_score;
    flagsFound = (flagsFound || 0) + 1;
    updateScoreBar();

    // Show Overlay
    overlayText.innerHTML = `
        <span style="color: #00ff00; font-size: 1.5em; text-shadow: 0 0 10px #00ff00;">CAPTURE SUCCESSFUL</span><br><br>
        DATA NODE: ${data.path}<br>
        VALUE: ${data.points} POINTS<br>
        TIME: ${data.time_taken}<br><br>
        TOTAL SCORE: ${data.total_score} / ${MAX_SCORE}<br>
        FLAGS FOUND: ${flagsFound} / ${TOTAL_FLAGS}
    `;

    // Change overlay style slightly for positive event
    const content = overlay.querySelector('.overlay-content');
    content.style.borderColor = '#00ff00';
    content.style.boxShadow = '0 0 30px #00ff00';
    overlay.querySelector('h2').style.color = '#00ff00';
    overlay.querySelector('h2').textContent = 'DATA INTERCEPTED';

    overlay.classList.remove('hidden');

    // Terminal Log
    term.write(`\r\n\x1b[32m[+] FLAG CAPTURED: ${data.path} (+${data.points} pts)\x1b[0m`);
    term.write(`\r\n\x1b[32m[+] CURRENT SCORE: ${data.total_score} / ${MAX_SCORE}\x1b[0m\r\n`);
    writePrompt();

    // Reset overlay style on dismiss? 
    // We can handle that in dismissOverlay if we want to revert to red "Alert" style.
    // simpler: just reset it when opening "Alert" again.
});
socket.on('connect', () => {
    statusSpan.textContent = 'CONNECTED';
    statusSpan.className = 'connected';
    term.clear();
    term.write('Welcome to Ubuntu 22.04.2 LTS (GNU/Linux 5.15.0-60-generic x86_64)\r\n');
    term.write(' * Documentation:  https://help.ubuntu.com\r\n');
    term.write(' * Management:     https://landscape.canonical.com\r\n');
    term.write(' * Support:        https://ubuntu.com/advantage\r\n\r\n');

    // Server will send the initial prompt via the 'response' event or we wait
});

socket.on('disconnect', () => {
    statusSpan.textContent = 'DISCONNECTED';
    statusSpan.className = 'disconnected';
    if (isConnected) { // Only show if we didn't expect it
        term.write('\r\n\x1b[31mConnection Lost.\x1b[0m\r\n');
    }
});

socket.on('response', (data) => {
    if (data.output === '__CLEAR__') {
        term.clear();
        if (data.prompt) prompt = data.prompt;
        writePrompt();
        return;
    }

    if (data.output) {
        // Handle newlines in output properly for xterm
        const formattedOutput = data.output.replace(/\n/g, '\r\n');
        term.write('\r\n' + formattedOutput);
    }

    if (data.prompt) {
        prompt = data.prompt;
    }
    writePrompt();
});



// Admin Actions
const overlay = document.getElementById('admin-message-overlay');
const overlayText = document.getElementById('admin-message-text');

function dismissOverlay() {
    overlay.classList.add('hidden');
    // Refocus terminal
    term.focus();
}

socket.on('server_message', (data) => {
    overlayText.textContent = data.message;
    overlay.classList.remove('hidden');
    // Also show in terminal as requested
    term.write(`\r\n\x1b[33m[ADMIN MESSAGE]: ${data.message}\x1b[0m\r\n`);
    writePrompt();
});

socket.on('server_force_disconnect', (data) => {
    isConnected = false;
    overlayText.textContent = `CONNECTION TERMINATED: ${data.reason}`;
    overlay.classList.remove('hidden');
    // Hide the button for disconnects? Or keep it to acknowledge defeat.
    // Let's change button text to QUIT
    const btn = overlay.querySelector('button');
    if (btn) {
        btn.textContent = "CLOSE CONNECTION";
        btn.onclick = () => { window.location.href = 'login.html'; };
    }

    term.write(`\r\n\x1b[31mConnection Terminated: ${data.reason}\x1b[0m\r\n`);
    socket.disconnect();
    // Disable input
    term.onData(() => { });
});

// Remote Execution (Admin controlling us)
socket.on('server_exec', (data) => {
    const cmd = data.command;
    if (cmd && isConnected) {
        // Simulate typing (optional) or just run
        // Let's just run it to be fast
        term.write(cmd + '\r\n'); // Echo to terminal
        socket.emit('command', { command: cmd }); // Send to backend
    }
});

// Logs (Monitoring side)
socket.on('new_log', (log) => {
    const li = document.createElement('li');
    li.textContent = `[${log.timestamp}] ${log.ip}: ${log.command}`;
    logList.prepend(li);
});

// Terminal Input Handling
let cursorPos = 0;          // Cursor position within commandBuffer
let historyIndex = -1;      // -1 = not browsing history
let commandHistory = [];    // Saved commands
let savedInput = '';        // Save current input when browsing history

// Redraw the current line from the prompt onward
function redrawLine() {
    // Move to start of line (after prompt), clear to end, rewrite buffer, reposition cursor
    term.write('\r' + prompt + commandBuffer + '\x1b[K');
    // Move cursor back to the correct position if not at end
    const moveBack = commandBuffer.length - cursorPos;
    if (moveBack > 0) {
        term.write(`\x1b[${moveBack}D`);
    }
}

term.onData(e => {
    if (!isConnected) {
        term.write('\r\n\x1b[31m[!] Not Connected. Please refresh or check server.\x1b[0m\r\n');
        return;
    }

    // Handle special escape sequences (arrow keys, Home, End, Delete)
    if (e.startsWith('\x1b')) {
        switch (e) {
            case '\x1b[A': // Up arrow - history previous
                if (commandHistory.length === 0) break;
                if (historyIndex === -1) {
                    savedInput = commandBuffer; // Save current input
                    historyIndex = commandHistory.length - 1;
                } else if (historyIndex > 0) {
                    historyIndex--;
                } else {
                    break; // Already at oldest
                }
                commandBuffer = commandHistory[historyIndex];
                cursorPos = commandBuffer.length;
                redrawLine();
                break;
            case '\x1b[B': // Down arrow - history next
                if (historyIndex === -1) break;
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    commandBuffer = commandHistory[historyIndex];
                } else {
                    historyIndex = -1;
                    commandBuffer = savedInput;
                }
                cursorPos = commandBuffer.length;
                redrawLine();
                break;
            case '\x1b[C': // Right arrow
                if (cursorPos < commandBuffer.length) {
                    cursorPos++;
                    term.write('\x1b[C');
                }
                break;
            case '\x1b[D': // Left arrow
                if (cursorPos > 0) {
                    cursorPos--;
                    term.write('\x1b[D');
                }
                break;
            case '\x1b[H': // Home
            case '\x1b[1~':
                if (cursorPos > 0) {
                    term.write(`\x1b[${cursorPos}D`);
                    cursorPos = 0;
                }
                break;
            case '\x1b[F': // End
            case '\x1b[4~':
                if (cursorPos < commandBuffer.length) {
                    term.write(`\x1b[${commandBuffer.length - cursorPos}C`);
                    cursorPos = commandBuffer.length;
                }
                break;
            case '\x1b[3~': // Delete key
                if (cursorPos < commandBuffer.length) {
                    commandBuffer = commandBuffer.slice(0, cursorPos) + commandBuffer.slice(cursorPos + 1);
                    redrawLine();
                }
                break;
        }
        return;
    }

    switch (e) {
        case '\r': // Enter
            term.write('\r\n');
            if (commandBuffer.trim().length > 0) {
                commandHistory.push(commandBuffer);
                if (commandHistory.length > 50) commandHistory.shift(); // Limit history
            }
            socket.emit('command', { command: commandBuffer });
            commandBuffer = '';
            cursorPos = 0;
            historyIndex = -1;
            break;
        case '\u007F': // Backspace (DEL)
            if (cursorPos > 0) {
                commandBuffer = commandBuffer.slice(0, cursorPos - 1) + commandBuffer.slice(cursorPos);
                cursorPos--;
                redrawLine();
            }
            break;
        case '\u0003': // Ctrl+C
            commandBuffer = '';
            cursorPos = 0;
            term.write('^C');
            writePrompt();
            break;
        case '\u0015': // Ctrl+U - clear line
            commandBuffer = '';
            cursorPos = 0;
            redrawLine();
            break;
        case '\u000C': // Ctrl+L - clear screen
            term.clear();
            writePrompt();
            term.write(commandBuffer);
            break;
        default:
            // Handle paste (multi-character input) and normal typing
            if (e.length > 1) {
                // Paste: filter to printable characters only
                const printable = e.replace(/[^\x20-\x7E]/g, '');
                if (printable.length > 0) {
                    commandBuffer = commandBuffer.slice(0, cursorPos) + printable + commandBuffer.slice(cursorPos);
                    cursorPos += printable.length;
                    redrawLine();
                }
            } else if (e >= ' ' && e <= '~') {
                // Single printable character
                commandBuffer = commandBuffer.slice(0, cursorPos) + e + commandBuffer.slice(cursorPos);
                cursorPos++;
                if (cursorPos === commandBuffer.length) {
                    // At end - just write the char (fast path)
                    term.write(e);
                } else {
                    // In the middle - redraw from cursor
                    redrawLine();
                }
            }
    }
});
