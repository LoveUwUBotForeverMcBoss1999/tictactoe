const socket = io();
const gameId = window.location.pathname.split('/')[2];
const username = new URLSearchParams(window.location.search).get('username');
let myTurn = false;
let mySymbol = '';
let matchCount = 1;
let rematchRequested = false;

// Join game room
socket.emit('join', { username, game_id: gameId });

// Add click handlers to cells
document.querySelectorAll('.cell').forEach(cell => {
    cell.addEventListener('click', () => {
        if (myTurn && !cell.textContent) {
            const position = parseInt(cell.dataset.index);
            socket.emit('make_move', {
                position: position,
                player: username,
                game_id: gameId
            });
        }
    });
});

// Socket event handlers
socket.on('waiting_for_opponent', () => {
    document.getElementById('status').textContent = 'Waiting for opponent...';
    document.getElementById('turn-text').textContent = 'Waiting for opponent...';
    document.getElementById('turn-indicator').style.display = 'none';
});

socket.on('room_full', () => {
    alert('Room is full!');
    window.location.href = '/';
});

socket.on('game_start', (data) => {
    document.getElementById('player1-name').textContent = data.player1.name;
    document.getElementById('player2-name').textContent = data.player2.name;

    mySymbol = username === data.player1.name ? 'X' : 'O';
    updateTurnStatus(data.current_turn);

    document.querySelector('.match-count').textContent = `Match #${matchCount}`;
});

socket.on('move_made', (data) => {
    const cell = document.querySelector(`[data-index="${data.position}"]`);
    cell.textContent = data.symbol;
    cell.classList.add(data.symbol.toLowerCase());

    if (data.winner) {
        handleGameEnd(data.winner, data.stats);
    } else {
        updateTurnStatus(data.next_turn);
    }
});

socket.on('rematch_requested', (data) => {
    if (username !== data.requestedBy) {
        document.getElementById('status').textContent = 'Opponent requested a rematch';
        document.getElementById('rematch-btn').style.display = 'none';
        document.getElementById('accept-rematch-btn').style.display = 'inline-block';
        document.getElementById('decline-rematch-btn').style.display = 'inline-block';
    } else {
        document.getElementById('status').textContent = 'Waiting for opponent to accept rematch...';
        document.getElementById('rematch-btn').style.display = 'none';
    }
});

socket.on('rematch_declined', () => {
    document.getElementById('status').textContent = 'Rematch declined';
    document.getElementById('rematch-btn').style.display = 'inline-block';
    document.getElementById('accept-rematch-btn').style.display = 'none';
    document.getElementById('decline-rematch-btn').style.display = 'none';
    rematchRequested = false;
});

socket.on('game_reset', (data) => {
    // Clear board
    document.querySelectorAll('.cell').forEach(cell => {
        cell.textContent = '';
        cell.classList.remove('x', 'o');
    });

    // Update match count
    matchCount++;
    document.querySelector('.match-count').textContent = `Match #${matchCount}`;

    // Update scores and last match results
    document.getElementById('player1-score').textContent = `Wins: ${data.p1_wins}`;
    document.getElementById('player2-score').textContent = `Wins: ${data.p2_wins}`;
    document.getElementById('player1-last').textContent = `Last match: ${data.last_result.p1}`;
    document.getElementById('player2-last').textContent = `Last match: ${data.last_result.p2}`;

    // Reset buttons and status
    document.getElementById('rematch-btn').style.display = 'none';
    document.getElementById('accept-rematch-btn').style.display = 'none';
    document.getElementById('decline-rematch-btn').style.display = 'none';

    // Reset game state
    updateTurnStatus(data.current_turn);
    rematchRequested = false;
});

socket.on('game_ended', (data) => {
    window.location.href = `/end-game/${gameId}?stats=${encodeURIComponent(JSON.stringify(data))}`;
});

function updateTurnStatus(currentTurn) {
    myTurn = currentTurn === username;
    const turnText = myTurn ? 'Your turn!' : "Opponent's turn";
    document.getElementById('status').textContent = turnText;
    document.getElementById('turn-text').textContent = turnText;

    const turnIndicator = document.getElementById('turn-indicator');
    turnIndicator.style.display = 'inline';
    turnIndicator.src = `/static/images/${currentTurn === document.getElementById('player1-name').textContent ? 'x.png' : 'o.png'}`;
}

function handleGameEnd(winner, stats) {
    let statusText;

    if (winner === 'draw') {
        statusText = "It's a draw!";
    } else {
        statusText = winner === username ? 'You won!' : 'You lost!';
    }

    document.getElementById('status').textContent = statusText;
    document.getElementById('player1-score').textContent = `Wins: ${stats.p1_wins}`;
    document.getElementById('player2-score').textContent = `Wins: ${stats.p2_wins}`;
    document.getElementById('player1-last').textContent = `Last match: ${stats.last_result.p1}`;
    document.getElementById('player2-last').textContent = `Last match: ${stats.last_result.p2}`;

    document.getElementById('rematch-btn').style.display = 'inline-block';
    document.getElementById('rematch-btn').disabled = false;
    document.getElementById('rematch-btn').textContent = 'Request Rematch';
}

function requestRematch() {
    if (!rematchRequested) {
        socket.emit('request_rematch', { game_id: gameId, player: username });
        document.getElementById('rematch-btn').textContent = 'Waiting for opponent...';
        document.getElementById('rematch-btn').disabled = true;
        rematchRequested = true;
    }
}

function acceptRematch() {
    socket.emit('accept_rematch', { game_id: gameId, player: username });
}

function declineRematch() {
    socket.emit('decline_rematch', { game_id: gameId, player: username });
    document.getElementById('rematch-btn').style.display = 'inline-block';
    document.getElementById('accept-rematch-btn').style.display = 'none';
    document.getElementById('decline-rematch-btn').style.display = 'none';
}

function endGame() {
    socket.emit('end_game', { game_id: gameId, player: username });
}

function downloadStats() {
    window.open(`/stats/${gameId}`, '_blank');
}