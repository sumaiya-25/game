from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import math
import random

app = Flask(__name__, static_folder='static')
CORS(app)

# Game state
game_state = {
    "piles": [],
    "reserve": 0,
    "player_turn": True,
    "game_over": False,
    "winner": None,
    "move_history": []
}

def display_piles(piles, reserve):
    print("\n============================")
    print(f" Reserve Pool: {reserve} stones left")
    print("============================")
    print("Current piles:")
    for i, pile in enumerate(piles):
        print(f"Pile {i+1}: {pile}")
    print("============================")

def game_over_check(piles):
    return all(p == 0 for p in piles)

def minimax(piles, depth, isMaximizing):
    if game_over_check(piles):
        return -1 if isMaximizing else 1

    if isMaximizing:
        best = -math.inf
        for i in range(len(piles)):
            for remove in range(1, min(3, piles[i]) + 1):
                new_piles = piles.copy()
                new_piles[i] -= remove
                val = minimax(new_piles, depth + 1, False)
                best = max(best, val)
        return best
    else:
        best = math.inf
        for i in range(len(piles)):
            for remove in range(1, min(3, piles[i]) + 1):
                new_piles = piles.copy()
                new_piles[i] -= remove
                val = minimax(new_piles, depth + 1, True)
                best = min(best, val)
        return best

def computer_move(piles):
    if random.random() < 0.5:
        pile_index = random.choice([i for i, p in enumerate(piles) if p > 0])
        remove_count = random.randint(1, min(3, piles[pile_index]))
        piles[pile_index] -= remove_count
        return pile_index, remove_count, "random"

    best_val = -math.inf
    best_move = None
    for i in range(len(piles)):
        for remove in range(1, min(3, piles[i]) + 1):
            new_piles = piles.copy()
            new_piles[i] -= remove
            move_val = minimax(new_piles, 0, False)
            if move_val > best_val:
                best_val = move_val
                best_move = (i, remove)

    pile_index, remove_count = best_move
    piles[pile_index] -= remove_count
    return pile_index, remove_count, "smart"

def add_from_reserve(piles, reserve, pile_index):
    if reserve > 0:
        piles[pile_index] += 1
        reserve -= 1
    return reserve

@app.route('/start', methods=['POST'])
def start_game():
    global game_state
    piles = [random.randint(3, 7) for _ in range(3)]
    reserve = 5
    player_turn = random.choice([True, False])
    
    game_state = {
        "piles": piles,
        "reserve": reserve,
        "player_turn": player_turn,
        "game_over": False,
        "winner": None,
        "move_history": []
    }
    
    return jsonify({
        "piles": game_state["piles"],
        "reserve": game_state["reserve"],
        "player_turn": game_state["player_turn"],
        "game_over": False,
        "winner": None,
        "message": "You start first!" if player_turn else "Computer starts first!"
    })

@app.route('/move', methods=['POST'])
def player_move():
    global game_state
    
    data = request.json
    pile = data.get('pile')
    remove = data.get('remove')
    
    if not game_state["player_turn"]:
        return jsonify({"error": "Not your turn"}), 400
    
    if pile < 0 or pile >= len(game_state["piles"]) or remove < 1 or remove > 3:
        return jsonify({"error": "Invalid move"}), 400
    
    if remove > game_state["piles"][pile]:
        return jsonify({"error": "Not enough stones"}), 400
    
    game_state["piles"][pile] -= remove
    game_state["reserve"] = add_from_reserve(game_state["piles"], game_state["reserve"], pile)
    game_state["move_history"].append({"player": "human", "pile": pile, "remove": remove})
    
    if game_over_check(game_state["piles"]):
        game_state["game_over"] = True
        # Player took last stone = player LOSES (inverse Nim)
        game_state["winner"] = "computer"
        return jsonify({
            "piles": game_state["piles"],
            "reserve": game_state["reserve"],
            "player_turn": False,
            "game_over": True,
            "winner": "computer",
            "message": "Computer wins! You took the last stone."
        })
    
    game_state["player_turn"] = False
    return jsonify({
        "piles": game_state["piles"],
        "reserve": game_state["reserve"],
        "player_turn": False,
        "game_over": False,
        "winner": None,
        "message": "Your move completed!"
    })

@app.route('/computer-move', methods=['POST'])
def computer_move_route():
    global game_state
    
    if game_state["player_turn"]:
        return jsonify({"error": "It's player's turn"}), 400
    
    if game_state["game_over"]:
        return jsonify({"error": "Game is over"}), 400
    
    pile_index, remove_count, move_type = computer_move(game_state["piles"])
    game_state["reserve"] = add_from_reserve(game_state["piles"], game_state["reserve"], pile_index)
    game_state["move_history"].append({"player": "computer", "pile": pile_index, "remove": remove_count, "type": move_type})
    
    if game_over_check(game_state["piles"]):
        game_state["game_over"] = True
        # Computer took last stone = computer LOSES (inverse Nim)
        game_state["winner"] = "player"
        return jsonify({
            "piles": game_state["piles"],
            "reserve": game_state["reserve"],
            "player_turn": True,
            "game_over": True,
            "winner": "player",
            "message": "You win! Computer took the last stone.",
            "computer_move": {"pile": pile_index, "remove": remove_count, "type": move_type}
        })
    
    game_state["player_turn"] = True
    return jsonify({
        "piles": game_state["piles"],
        "reserve": game_state["reserve"],
        "player_turn": True,
        "game_over": False,
        "winner": None,
        "message": "Computer moved!",
        "computer_move": {"pile": pile_index, "remove": remove_count, "type": move_type}
    })

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "piles": game_state["piles"],
        "reserve": game_state["reserve"],
        "player_turn": game_state["player_turn"],
        "game_over": game_state["game_over"],
        "winner": game_state["winner"]
    })

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
