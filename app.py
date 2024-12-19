from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import os
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Game state
games = {}


class Game:
    def __init__(self, p1):
        self.board = ['' for _ in range(9)]
        self.player1 = {'name': p1, 'avatar': 'x.png', 'symbol': 'X'}
        self.player2 = None
        self.current_turn = p1
        self.match_history = []
        self.p1_wins = 0
        self.p2_wins = 0
        self.draws = 0
        self.player_count = 1
        self.last_result = {'p1': '-', 'p2': '-'}
        self.rematch_request = None
        self.total_matches = 0
        self.last_winner = None

    def update_last_result(self, winner):
        if winner == 'draw':
            self.last_result = {'p1': 'Draw', 'p2': 'Draw'}
            self.last_winner = 'Draw'
        else:
            self.last_result = {
                'p1': 'Won' if winner == self.player1['name'] else 'Lost',
                'p2': 'Won' if winner == self.player2['name'] else 'Lost'
            }
            self.last_winner = winner

    def add_player2(self, p2):
        self.player2 = {'name': p2, 'avatar': 'o.png', 'symbol': 'O'}
        self.player_count = 2

    def make_move(self, position, player):
        if self.board[position] == '' and player == self.current_turn:
            self.board[position] = 'X' if player == self.player1['name'] else 'O'
            self.current_turn = self.player2['name'] if player == self.player1['name'] else self.player1['name']
            return True
        return False

    def check_winner(self):
        win_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]  # Diagonals
        ]

        for combo in win_combinations:
            if (self.board[combo[0]] != '' and
                    self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]]):
                return self.player1['name'] if self.board[combo[0]] == 'X' else self.player2['name']

        if '' not in self.board:
            return 'draw'
        return None

    def generate_stats_card(self):
        img = Image.new('RGB', (800, 600), color='#1a1a2e')
        d = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype('arial.ttf', 36)
            small_font = ImageFont.truetype('arial.ttf', 24)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Draw stats
        d.text((300, 50), 'Match Statistics', fill='#00ff88', font=font)

        # Player stats
        d.text((50, 100), f"Player X: {self.player1['name']}", fill='white', font=small_font)
        d.text((50, 140), f"Wins: {self.p1_wins}", fill='#00ff88', font=small_font)

        if self.player2:
            d.text((50, 200), f"Player O: {self.player2['name']}", fill='white', font=small_font)
            d.text((50, 240), f"Wins: {self.p2_wins}", fill='#00ff88', font=small_font)

        # Overall stats
        d.text((50, 300), f"Total Matches: {self.total_matches}", fill='white', font=small_font)
        d.text((50, 340), f"Total Draws: {self.draws}", fill='white', font=small_font)

        if self.last_winner:
            d.text((50, 380), f"Last Winner: {self.last_winner}", fill='#00ff88', font=small_font)

        # Match history
        y = 440
        d.text((50, y), "Recent Matches:", fill='white', font=small_font)
        for match in self.match_history[-5:]:
            y += 30
            d.text((50, y), match, fill='#888888', font=small_font)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/game/<game_id>')
def game(game_id):
    return render_template('game.html')


@app.route('/end-game/<game_id>')
def end_game_page(game_id):
    return render_template('end-game.html')


@app.route('/stats/<game_id>')
def get_stats(game_id):
    if game_id in games:
        stats_image = games[game_id].generate_stats_card()
        return send_file(stats_image, mimetype='image/png')
    return 'Game not found', 404


@socketio.on('join')
def on_join(data):
    username = data['username']
    game_id = data['game_id']

    join_room(game_id)

    if game_id not in games:
        games[game_id] = Game(username)
        emit('waiting_for_opponent', {
            'player_count': '1/2',
            'player_name': username,
            'player_symbol': 'X'
        }, room=game_id)
    elif games[game_id].player2 is None:
        games[game_id].add_player2(username)
        emit('game_start', {
            'player1': games[game_id].player1,
            'player2': games[game_id].player2,
            'current_turn': games[game_id].current_turn
        }, room=game_id)
    else:
        emit('room_full', room=request.sid)


@socketio.on('make_move')
def on_move(data):
    game = games[data['game_id']]
    if game.make_move(data['position'], data['player']):
        winner = game.check_winner()

        if winner:
            game.total_matches += 1
            game.update_last_result(winner)
            if winner != 'draw':
                if winner == game.player1['name']:
                    game.p1_wins += 1
                else:
                    game.p2_wins += 1
                game.match_history.append(f"{winner} won at {datetime.now().strftime('%H:%M:%S')}")
            else:
                game.draws += 1
                game.match_history.append(f"Draw at {datetime.now().strftime('%H:%M:%S')}")

        emit('move_made', {
            'position': data['position'],
            'symbol': game.player1['symbol'] if data['player'] == game.player1['name'] else game.player2['symbol'],
            'next_turn': game.current_turn,
            'winner': winner,
            'stats': {
                'p1_wins': game.p1_wins,
                'p2_wins': game.p2_wins,
                'draws': game.draws,
                'last_result': game.last_result
            }
        }, room=data['game_id'])


@socketio.on('request_rematch')
def on_request_rematch(data):
    game = games[data['game_id']]
    game.rematch_request = data['player']
    emit('rematch_requested', {
        'requestedBy': data['player']
    }, room=data['game_id'])


@socketio.on('decline_rematch')
def on_decline_rematch(data):
    game = games[data['game_id']]
    game.rematch_request = None
    emit('rematch_declined', room=data['game_id'])


@socketio.on('accept_rematch')
def on_accept_rematch(data):
    game = games[data['game_id']]
    if game.rematch_request:
        game.board = ['' for _ in range(9)]
        game.current_turn = game.player1['name']
        game.rematch_request = None
        emit('game_reset', {
            'current_turn': game.current_turn,
            'p1_wins': game.p1_wins,
            'p2_wins': game.p2_wins,
            'draws': game.draws,
            'last_result': game.last_result
        }, room=data['game_id'])


@socketio.on('end_game')
def on_end_game(data):
    game = games[data['game_id']]
    emit('game_ended', {
        'player1': game.player1,
        'player2': game.player2,
        'p1_wins': game.p1_wins,
        'p2_wins': game.p2_wins,
        'draws': game.draws,
        'total_matches': game.total_matches,
        'match_history': game.match_history,
        'last_winner': game.last_winner
    }, room=data['game_id'])


if __name__ == '__main__':
    import eventlet
    eventlet.monkey_patch()
    socketio.run(app, debug=True)
