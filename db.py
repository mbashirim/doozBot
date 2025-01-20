import sqlite3
from datetime import datetime
import json
from tron import TronManager
from threading import Lock
from datetime import datetime, timedelta
import requests

class Database:
    def __init__(self, db_name='dev.db'):
        self.db_name = db_name
        self.lock = Lock()
        self.init_db()

    def init_db(self):
        """Initialize database tables if they don't exist"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS User (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    draws INTEGER DEFAULT 0,
                    balance_fr INTEGER DEFAULT 5
                    
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS GameWallet (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE,
                    address TEXT,
                    key TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES User(id)
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS Game (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT UNIQUE,
                    board TEXT,
                    current_player TEXT,
                    game_over BOOLEAN DEFAULT FALSE,
                    player1_id TEXT,
                    player1_message_id TEXT,
                    player2_id TEXT,
                    player2_message_id TEXT,
                    is_bet BOOLEAN DEFAULT FALSE,
                    type_game TEXT CHECK(type_game IN ('bet', 'fr')),
                    bet_amount INTEGER DEFAULT 0,
                    winner_id TEXT,
                    moves INTEGER DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    last_move_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player1_id) REFERENCES User(id),
                    FOREIGN KEY (player2_id) REFERENCES User(id),
                    FOREIGN KEY (winner_id) REFERENCES User(id)
                )
            ''')
            
            conn.commit()
            conn.close()

    def save_user(self, user_id, username):
        """Save or update user in database and create wallet"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            try:
                c = conn.cursor()
                
                c.execute('SELECT id FROM User WHERE id = ?', (user_id,))
                user_exists = c.fetchone()
                
                if not user_exists:
                    c.execute('INSERT INTO User (id, username) VALUES (?, ?)', (user_id, username))
                    
                    tron = TronManager()
                    wallet = tron.create_tron_account()
                    now = datetime.now()
                    c.execute('''
                        INSERT INTO GameWallet (user_id, address, key, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, wallet['address'], wallet['private_key'], now, now))
                else:
                    c.execute('UPDATE User SET username = ? WHERE id = ?', (username, user_id))
                    
                conn.commit()
            finally:
                conn.close()

    def get_user(self, user_id):
        """Get user data if exists"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            c.execute('''
                SELECT u.*, w.address, w.key 
                FROM User u 
                LEFT JOIN GameWallet w ON u.id = w.user_id 
                WHERE u.id = ?
            ''', (user_id,))
            user_data = c.fetchone()
            conn.close()
            if user_data:
                return {
                    'id': user_data[0],
                    'username': user_data[1],
                    'balance': user_data[2],
                    'wins': user_data[3],
                    'losses': user_data[4], 
                    'draws': user_data[5],
                    'balance_fr': user_data[6],
                    'wallet_address': user_data[7],
                    'wallet_key': user_data[8]
                }
            return None

    def create_user_if_not_exists(self, user_id):
        """Create user if doesn't exist"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            
            c.execute('SELECT id FROM User WHERE id = ?', (user_id,))
            if not c.fetchone():
                c.execute('INSERT INTO User (id) VALUES (?)', (user_id,))
                conn.commit()
                
                tron = TronManager()
                wallet = tron.create_tron_account()
                now = datetime.now()
                c.execute('''
                    INSERT INTO GameWallet (user_id, address, key, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, wallet['address'], wallet['private_key'], now, now))
                
            conn.commit()
            conn.close()

    def create_wallet(self, user_id):
        """Create TRON wallet for user and save to database"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            
            c.execute('SELECT * FROM GameWallet WHERE user_id = ?', (user_id,))
            if c.fetchone():
                conn.close()
                return False
                
            tron = TronManager()
            wallet = tron.create_tron_account()
            now = datetime.now()
            c.execute('''
                INSERT INTO GameWallet (user_id, address, key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, wallet['address'], wallet['private_key'], now, now))
            
            conn.commit()
            conn.close()
            return True

    def save_game(self, game_id, game_data):
        """Save or update game in database"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            board_str = json.dumps(game_data.board)
            now = datetime.now()
            
            c.execute('''
                UPDATE Game 
                SET board=?, current_player=?, game_over=?, player1_id=?, player2_id=?,
                    winner_id=?, moves=?, ended_at=?, is_bet=?, bet_amount=?, type_game=?,
                    last_move_at=?
                WHERE game_id=?
            ''', (board_str, game_data.current_player, game_data.game_over, game_data.player1_id, game_data.player2_id, game_data.winner_id,game_data.moves, game_data.ended_at, game_data.is_bet, game_data.bet_amount, game_data.type_game, now, game_id))
            
            if c.rowcount == 0:
                c.execute('''
                    INSERT INTO Game (game_id, board, current_player, game_over,
                                    player1_id, player2_id, winner_id, moves, 
                                    started_at, is_bet, bet_amount, type_game,
                                    last_move_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (game_id, board_str, game_data.current_player, game_data.game_over,game_data.player1_id, game_data.player2_id, game_data.winner_id,game_data.moves, game_data.started_at, game_data.is_bet,game_data.bet_amount, game_data.type_game, now))
                
            conn.commit()
            conn.close()

    def load_game(self, game_id):
        """Load game from database"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            c.execute('SELECT * FROM Game WHERE game_id = ?', (game_id,))
            game_data = c.fetchone()
            conn.close()
            return game_data

    def update_stats(self, winner_id, loser_id=None):
        """Update user stats after game"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            
            if winner_id:
                c.execute('UPDATE User SET wins = wins + 1 WHERE id = ?', (winner_id,))
                if loser_id:
                    c.execute('UPDATE User SET losses = losses + 1 WHERE id = ?', (loser_id,))
            else:
                if loser_id:
                    c.execute('UPDATE User SET draws = draws + 1 WHERE id IN (?,?)', (winner_id, loser_id))
                    
            conn.commit()
            conn.close()

    def get_user_stats(self, user_id):
        """Get user statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            c.execute('SELECT wins, losses, draws FROM User WHERE id = ?', (user_id,))
            stats = c.fetchone()
            conn.close()
            return stats if stats else (0, 0, 0)

    def get_wallet(self, user_id):
        """Get user's wallet balance"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            c.execute('SELECT address FROM GameWallet WHERE user_id = ?', (user_id,))
            wallet = c.fetchone()
            conn.close()
            return wallet[0] if wallet else 0
    
    def add_coins(self, user_id, amount):
        """Add coins to user's balance and transfer TRX to bank wallet"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT address, key FROM GameWallet WHERE user_id = ?', (user_id,))
                wallet_data = c.fetchone()
                if not wallet_data:
                    return False
                    
                user_address = wallet_data[0]
                user_private_key = wallet_data[1]

                with open('config.json') as f:
                    config = json.load(f)
                bank_address = config['bank_wallet']['address']

                tron = TronManager()
                balance = tron.get_trx_balance(user_address)
                if balance < 1.1:
                    return False
                if balance > 1.1:
                    result = tron.send_trx(user_address, user_private_key, bank_address, (balance - 1.1))
                c.execute('UPDATE User SET balance = balance + ? WHERE id = ?', (amount, user_id))
                
                tron = TronManager()
                new_wallet = tron.create_tron_account()
                c.execute('UPDATE GameWallet SET address = ?, key = ? WHERE user_id = ?',(new_wallet['address'], new_wallet['private_key'], user_id))
                
                conn.commit()
                return True

            except Exception as e:
                print(f"Error adding coins: {e}")
                return False
            finally:
                conn.close()

    def start_bet_game(self, game_id, bet_amount):
        """Start a bet game with specified amount"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    UPDATE Game 
                    SET is_bet = TRUE, bet_amount = ?, type_game = 'bet'
                    WHERE game_id = ?
                ''', (bet_amount, game_id))
                conn.commit()
                return True
            except Exception as e:
                print(f"Error starting bet game: {e}")
                return False
            finally:
                conn.close()


    def get_user_by_username(self, username):
        """Retrieve user data by username"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT * FROM User WHERE username = ?', (username,))
                user_data = c.fetchone()
                return user_data
            except Exception as e:
                print(f"Error retrieving user by username: {e}")
                return None
            finally:
                conn.close()
    def remove_coins(self, user_id, amount):
        """Remove specified amount of coins from user's balance"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT balance FROM User WHERE id = ?', (user_id,))
                user_data = c.fetchone()
                if not user_data:
                    return False, "User not found"
                
                current_balance = user_data[0]
                if current_balance < amount:
                    return False, "Insufficient balance"
                
                new_balance = current_balance - amount
                c.execute('UPDATE User SET balance = ? WHERE id = ?', (new_balance, user_id))
                conn.commit()
                return True, "Coins removed successfully"
            except Exception as e:
                print(f"Error removing coins: {e}")
                return False, str(e)
            finally:
                conn.close()
    def add_coins_balance(self, user_id, amount):
        """Add specified amount of coins to user's balance"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT balance FROM User WHERE id = ?', (user_id,))
                user_data = c.fetchone()
                if not user_data:
                    return False, "User not found"
                
                current_balance = user_data[0]
                new_balance = current_balance + amount
                c.execute('UPDATE User SET balance = ? WHERE id = ?', (new_balance, user_id))
                conn.commit()
                return True, "Coins added successfully"
            except Exception as e:
                print(f"Error adding coins: {e}")
                return False, str(e)
            finally:
                conn.close()
    def update_user_balance(self, user_id, new_balance):
        """Update the user's balance to a new value"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('UPDATE User SET balance = ? WHERE user_id = ?', (new_balance, user_id))
                conn.commit()
                return True, "User balance updated successfully"
            except Exception as e:
                print(f"Error updating user balance: {e}")
                return False, str(e)
            finally:
                conn.close()
    def join_player2(self, game_id, user_id):
        """Add a player to the waiting list for player 2"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('UPDATE Game SET player2_id = ? WHERE game_id = ? AND player2_id IS NULL', (user_id, game_id))
                if c.rowcount == 0:
                    return False
                conn.commit()
                return True
            except Exception as e:
                print(f"Error joining game as player 2: {e}")
                return False
            finally:
                conn.close()
    def add_coins_balance_fr(self, user_id, amount):
        """Add specified amount of coins to user's balance_fr"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT balance_fr FROM User WHERE id = ?', (user_id,))
                user_data = c.fetchone()
                if not user_data:
                    return False, "User not found"
                
                c.execute('UPDATE User SET balance_fr = balance_fr + ? WHERE id = ?', (amount, user_id))
                conn.commit()
                return True, "Coins added successfully"
            except Exception as e:
                print(f"Error adding coins to balance_fr: {e}")
                return False, str(e)
            finally:
                conn.close()
            
    def remove_coins_fr(self, user_id, amount):
        """Remove specified amount of coins from user's balance_fr"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT balance_fr FROM User WHERE id = ?', (user_id,))
                current_balance = c.fetchone()
                if not current_balance:
                    return False, "User not found"
                if current_balance[0] < amount:
                    return False, "Insufficient balance"
                
                c.execute('UPDATE User SET balance_fr = balance_fr - ? WHERE id = ?', (amount, user_id))
                conn.commit()
                return True, "Coins removed successfully"
            except Exception as e:
                print(f"Error removing coins: {e}")
                return False, str(e)
            finally:
                conn.close()

    def get_active_games_count(self, user_id):
        """Get count of active games where user is player1 or player2"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT COUNT(*) FROM Game 
                    WHERE (player1_id = ? OR player2_id = ?)
                    AND winner_id IS NULL
                    AND player2_id IS NOT NULL
                    AND game_over = 0
                ''', (user_id, user_id))
                count = c.fetchone()[0]
                return count
            except Exception as e:
                print(f"Error getting active games count: {e}")
                return 0
            finally:
                conn.close()
                
    def get_active_games_json(self, user_id):
        """Get active games for user separated by game type (bet/fr) in JSON format"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT COUNT(*) FROM Game 
                    WHERE (player1_id = ? OR player2_id = ?)
                    AND winner_id IS NULL
                    AND player2_id IS NOT NULL 
                    AND game_over = 0
                    AND type_game = 'bet'
                ''', (user_id, user_id))
                bet_count = c.fetchone()[0]

                c.execute('''
                    SELECT COUNT(*) FROM Game
                    WHERE (player1_id = ? OR player2_id = ?)
                    AND winner_id IS NULL
                    AND player2_id IS NOT NULL
                    AND game_over = 0
                    AND type_game = 'fr'
                ''', (user_id, user_id))
                fr_count = c.fetchone()[0]

                return {
                    'bet': bet_count,
                    'fr': fr_count
                }
            except Exception as e:
                print(f"Error getting active games json: {e}")
                return {'bet': 0, 'fr': 0}
            finally:
                conn.close()
        
    def get_old_games(self):
        """Get games that haven't had a move in over an hour"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                one_hour_ago = datetime.now() - timedelta(minutes=5)
                c.execute('''
                    SELECT * FROM Game 
                    WHERE last_move_at < ?
                    AND winner_id IS NULL
                    AND player2_id IS NOT NULL
                    AND game_over = 0
                ''', (one_hour_ago,))
                old_games = c.fetchall()
                return old_games
            except Exception as e:
                print(f"Error getting old games: {e}")
                return []
            finally:
                conn.close()
                
    def delete_game_by_id(self, game_id):
        """Delete a game from the database by its game_id"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('DELETE FROM Game WHERE id = ?', (game_id,))
                conn.commit()
                return True, "Game deleted successfully"
            except Exception as e:
                print(f"Error deleting game: {e}")
                return False, str(e)
            finally:
                conn.close()
    def get_games_between_players(self, player1_id, player2_id):
        """Get all games between two players and their results"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT game_id, type_game, winner_id 
                    FROM Game 
                    WHERE (player1_id = ? AND player2_id = ?) 
                    OR (player1_id = ? AND player2_id = ?)
                ''', (player1_id, player2_id, player2_id, player1_id))
                games = c.fetchall()
                
                win_counts = {
                    'bet': {player1_id: 0, player2_id: 0},
                    'fr': {player1_id: 0, player2_id: 0}
                }
                
                for game in games:
                    game_id, type_game, winner_id = game
                    if winner_id == player1_id:
                        win_counts[type_game][player1_id] += 1
                    elif winner_id == player2_id:
                        win_counts[type_game][player2_id] += 1
                
                result = {
                    'win': {
                        player1_id: win_counts['bet'][player1_id],
                        player2_id: win_counts['bet'][player2_id]
                    },
                    'fr': {
                        player1_id: win_counts['fr'][player1_id],
                        player2_id: win_counts['fr'][player2_id]
                    }
                }
                (result)
                return result
            except Exception as e:
                return None
            finally:
                conn.close()
    def get_full_game_info(self, user_id):
        """Get full game info for a user including wins, losses, and draws for both 'fr' and 'bet' game types"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT type_game, winner_id, player1_id, player2_id, ended_at
                    FROM Game
                    WHERE player1_id = ? OR player2_id = ?
                ''', (user_id, user_id))
                games = c.fetchall()
                
                game_info = {
                    'fr': {'win': 0, 'lose': 0, 'draw': 0},
                    'bet': {'win': 0, 'lose': 0, 'draw': 0}
                }
                
                for game in games:
                    type_game, winner_id, player1_id, player2_id, ended_at = game
                    if winner_id == user_id:
                        game_info[type_game]['win'] += 1
                    elif winner_id is None and ended_at is not None:
                        game_info[type_game]['draw'] += 1
                    elif winner_id is not None and winner_id != user_id:
                        game_info[type_game]['lose'] += 1
                
                return game_info
            except Exception as e:
                print(f"Error getting full game info: {e}")
                return None
            finally:
                conn.close()


    def save_message_id_for_user(self, game_id, user_id, message_id):
        """Save message ID for a user in the game"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            try:
                c = conn.cursor()
                
                c.execute('SELECT id FROM Game WHERE game_id = ? AND (player1_id = ? OR player2_id = ?)', (game_id, user_id, user_id))
                game_exists = c.fetchone()
                
                if game_exists:
                    c.execute('''
                        UPDATE Game
                        SET player1_message_id = CASE WHEN player1_id = ? THEN ? ELSE player1_message_id END,
                            player2_message_id = CASE WHEN player2_id = ? THEN ? ELSE player2_message_id END
                        WHERE game_id = ?
                    ''', (user_id, message_id, user_id, message_id, game_id))
                    
                    conn.commit()
            except Exception as e:
                print(f"Error saving message ID for user: {e}")
            finally:
                conn.close()

    def get_game_info_by_id(self, game_id):
        """Retrieve all game information by game ID"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            try:
                c = conn.cursor()
                
                c.execute('''SELECT id, game_id, board, current_player, game_over, 
                           player1_id, player1_message_id, player2_id, player2_message_id,
                           is_bet, type_game, bet_amount, winner_id, moves,
                           started_at, ended_at, last_move_at
                           FROM Game WHERE id = ?''', (game_id,))
                game_info = c.fetchone()
                
                if game_info:
                    return {
                        'id': game_info[0],
                        'game_id': game_info[1], 
                        'board': game_info[2],
                        'current_player': game_info[3],
                        'game_over': bool(game_info[4]),
                        'player1_id': game_info[5],
                        'player1_message_id': game_info[6],
                        'player2_id': game_info[7], 
                        'player2_message_id': game_info[8],
                        'is_bet': bool(game_info[9]),
                        'type_game': game_info[10],
                        'bet_amount': game_info[11],
                        'winner_id': game_info[12],
                        'moves': game_info[13],
                        'started_at': game_info[14],
                        'ended_at': game_info[15],
                        'last_move_at': game_info[16]
                    }
                return None
            except Exception as e:
                print(f"Error getting game info by ID: {e}")
                return None
            finally:
                conn.close()
    def get_game_by_game_id(self, game_id):
        """Get game by game_id"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT * FROM Game WHERE game_id = ?', (game_id,))
                game = c.fetchone()
                return game
            except Exception as e:
                print(f"Error getting game by game_id: {e}")
                return None
            finally:
                conn.close()
    def delete_game_by_id(self, game_id):
        """Delete a game by its ID"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            try:
                c = conn.cursor()
                c.execute('DELETE FROM Game WHERE game_id = ?', (game_id,))
                conn.commit()
                return True, "Game deleted successfully"
            except Exception as e:
                print(f"Error deleting game: {e}")
                return False, str(e)
            finally:
                conn.close()


    def get_incomplete_games(self,bot_token):
        """Get games that are incomplete and older than 30 minutes and delete them"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            try:
                c = conn.cursor()
                current_time = datetime.now()
                timeout = current_time - timedelta(minutes=3)
                
                c.execute('''
                    SELECT game_id 
                    FROM Game 
                    WHERE started_at < ? 
                    AND (
                        player1_message_id IS NULL AND
                        player2_id IS NULL AND
                        player2_message_id IS NULL AND
                        winner_id IS NULL
                    )
                    AND ended_at IS NULL
                ''', (timeout,))
                
                old_games = c.fetchall()
                for game in old_games:
                    game_id = game[0]
                    c.execute('SELECT player1_id FROM Game WHERE game_id = ?', (game_id,))
                    player1_data = c.fetchone()
                    if player1_data:
                        player1_id = player1_data[0]
                        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        data = {
                            'chat_id': player1_id,
                            'text': "تایم دعوت برای حریف به پایان رسید💣"
                        }
                        response = requests.post(url, data=data)
                        print(f"Status code for sending message to player1: {response.status_code}")
                print(old_games)
                c.execute('''
                    DELETE FROM Game 
                    WHERE started_at < ? 
                    AND (
                        player1_message_id IS NULL AND
                        player2_id IS NULL AND
                        player2_message_id IS NULL AND
                        winner_id IS NULL
                    )
                    AND ended_at IS NULL
                ''', (timeout,))
                
                conn.commit()
                return old_games
                
            except Exception as e:
                print(f"Error getting/deleting incomplete games: {e}")
                return None
            finally:
                conn.close()
                
    def delete_gameid(self, game_id):
        """Delete a game by its game_id"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('DELETE FROM Game WHERE id = ?', (game_id,))
                conn.commit()
                return True, "Game deleted successfully"
            except Exception as e:
                print(f"Error deleting game: {e}")
                return False, str(e)
            finally:
                conn.close()
        
    def delete_game_by_gameid(self, game_id):
        """Delete a game by its game_id"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('DELETE FROM Game WHERE game_id = ?', (game_id,))
                conn.commit()
                return True, "Game deleted successfully"
            except Exception as e:
                print(f"Error deleting game: {e}")
                return False, str(e)
            finally:
                conn.close()
    def get_invitions_of_player(self, user_id):
        """Get incomplete games for a specific user"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT COUNT(*) FROM Game 
                    WHERE player1_id = ?
                    AND (
                        player1_message_id IS NULL AND
                        player2_id IS NULL AND 
                        player2_message_id IS NULL
                    )
                    AND ended_at IS NULL
                ''', (user_id,))
                count = c.fetchone()[0]
                return count
            except Exception as e:
                print(f"Error getting incomplete games count: {e}")
                return 0
            finally:
                conn.close()

    def add_win_to_user(self, user_id):
        """Add a win to user's statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    UPDATE User 
                    SET wins = wins + 1
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                return True, "Win added successfully"
            except Exception as e:
                print(f"Error adding win: {e}")
                return False, str(e)
            finally:
                conn.close()
    def add_loose_to_user(self, user_id):
        """Add a loss to user's statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    UPDATE User 
                    SET losses = losses + 1
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                return True, "Loss added successfully"
            except Exception as e:
                print(f"Error adding loss: {e}")
                return False, str(e)
            finally:
                conn.close()

    def make_game_win(self, game_id, winner_id):
        """Set game winner and end time"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                now = datetime.now()
                c.execute('''
                    UPDATE Game 
                    SET winner_id = ?,
                        ended_at = ?,
                        game_over = 1
                    WHERE id = ?
                ''', (winner_id, now, game_id))
                conn.commit()
                return True, "Game win recorded successfully"
            except Exception as e:
                print(f"Error recording game win: {e}")
                return False, str(e)
            finally:
                conn.close()
                
    def reset_coins(self, user_id):
        """Reset user's coin balance to 0"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    UPDATE User 
                    SET balance = 0
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                return True, "Coins reset successfully"
            except Exception as e:
                print(f"Error resetting coins: {e}")
                return False, str(e)
            finally:
                conn.close()
                
    def get_all_bet_games(self):
        """Get all games from database where type is bet"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT * FROM Game WHERE type_game = "bet" AND game_over = 1')
                games = c.fetchall()
                return games
            except Exception as e:
                print(f"Error getting games: {e}")
                return []
            finally:
                conn.close()
                
    def get_all_users_with_wallets(self):
        """Get all users and their associated wallet information"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT User.*, GameWallet.address, GameWallet.key 
                    FROM User
                    LEFT JOIN GameWallet ON User.id = GameWallet.user_id
                ''')
                users = c.fetchall()
                return users
            except Exception as e:
                print(f"Error getting users with wallets: {e}")
                return []
            finally:
                conn.close()
                
    def get_all_games(self):
        """Get all games from database"""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            try:
                c.execute('SELECT * FROM Game')
                games = c.fetchall()
                return games
            except Exception as e:
                print(f"Error getting games: {e}")
                return []
            finally:
                conn.close()