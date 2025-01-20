from telethon import Button
import json
from datetime import datetime
from db import Database

class FourInRow:
    def __init__(self, player1_id=None, player2_id=None):
        self.board = [[' ' for _ in range(7)] for _ in range(6)]
        self.current_player = '🔴'  
        self.game_over = False
        self.player1_id = player1_id  
        self.player2_id = player2_id
        self.player1_message_id = None
        self.player2_message_id = None
        self.moves = 0
        self.winner_id = None
        self.started_at = datetime.now()
        self.ended_at = None
        self.is_bet = False
        self.bet_amount = 0
        self.status = "🎮 بازی در حال انجام..."
        self.player1_username = None
        self.player2_username = None
        self.type_game = 'bet' 

        db = Database()
        
        if player1_id:
            user1_data = db.get_user(player1_id)
            if not user1_data:
                db.create_user_if_not_exists(player1_id)
            if not user1_data or not user1_data.get('wallet_address'):
                db.create_wallet(player1_id)
            self.player1_username = user1_data['username'] if user1_data else None
        
        if player2_id:
            user2_data = db.get_user(player2_id)
            if not user2_data:
                db.create_user_if_not_exists(player2_id)
            if not user2_data or not user2_data.get('wallet_address'):
                db.create_wallet(player2_id)
            self.player2_username = user2_data['username'] if user2_data else None

    @classmethod
    def start_game(cls, player1_id, player2_id):
        """Start a new game with two players"""
        game = cls(player1_id=player1_id, player2_id=player2_id)
        return game


    def make_move(self, col):
        if col < 0 or col > 6 or self.game_over:
            return False
        
        for row in range(5, -1, -1):
            if self.board[row][col] == ' ':
                self.board[row][col] = self.current_player
                self.moves += 1
                
                if self.check_win(row, col):
                    self.game_over = True
                    self.winner_id =  self.player1_id if self.current_player == '🔴' else self.player2_id
                    self.ended_at = datetime.now()
                    winner_color = '🔴' if self.winner_id == self.player1_id else '🔵'
                    loser_username = self.player2_username if self.winner_id == self.player1_id else self.player1_username
                    if self.is_bet:
                        db = Database()
                        loser_id = self.player2_id if self.winner_id == self.player1_id else self.player1_id
                        db.update_stats(self.winner_id, loser_id)
                        total_bet = (self.bet_amount * 2) 
                        if self.type_game == 'bet':
                            db.add_coins_balance(self.winner_id, total_bet * 0.95)
                        else:
                            db.add_coins_balance_fr(self.winner_id, total_bet)
                        self.status = f"🎉 بازی تمام شد! {winner_color} برنده شد و {total_bet} سکه برد! 🏆\nحریف: {loser_username}"
                    else:
                        db = Database()
                        loser_id = self.player2_id if self.winner_id == self.player1_id else self.player1_id
                        db.update_stats(self.winner_id, loser_id)
                        if self.type_game == 'bet':
                            db.add_coins_balance(self.winner_id, self.bet_amount* 0.95)
                        else:
                            db.add_coins_balance_fr(self.winner_id, self.bet_amount)
                        self.status = f"🎉 بازی تمام شد! {winner_color} برنده شد! 🏆\nحریف: {loser_username}"
                    return True
                
                if self.moves == 42: 
                    self.game_over = True
                    self.ended_at = datetime.now()
                    if self.is_bet:
                        db = Database()
                        db.update_stats(self.player1_id, self.player2_id)
                        if self.type_game == 'bet':
                            db.add_coins_balance(self.player1_id, self.bet_amount)
                            db.add_coins_balance(self.player2_id, self.bet_amount)
                        else:
                            db.add_coins_balance_fr(self.player1_id, self.bet_amount)
                            db.add_coins_balance_fr(self.player2_id, self.bet_amount)
                        self.status = f"🤝 بازی تمام شد! مساوی! {self.bet_amount} سکه برگشت داده شد!"
                    else:
                        db = Database()
                        db.update_stats(self.player1_id, self.player2_id)
                        self.status = f"🤝 بازی تمام شد! مساوی! {self.bet_amount} سکه برگشت داده شد!"
                    return True
                    
                self.current_player = '🔵' if self.current_player == '🔴' else '🔴'
                opponent_username = self.player1_username if self.current_player == '🔴' else self.player2_username
                if self.is_bet:
                    self.status = f"💰 بازی رقابتی - نوبت: {self.current_player} ({opponent_username})"
                else:
                    self.status = f"نوبت: {self.current_player} ({opponent_username})"
                return True
        return False

    def check_win(self, row, col):
        directions = [(0,1), (1,0), (1,1), (1,-1)]
        for dr, dc in directions:
            count = 1
            r, c = row + dr, col + dc
            while 0 <= r < 6 and 0 <= c < 7 and self.board[r][c] == self.current_player:
                count += 1
                r += dr
                c += dc
            r, c = row - dr, col - dc
            while 0 <= r < 6 and 0 <= c < 7 and self.board[r][c] == self.current_player:
                count += 1
                r -= dr
                c -= dc
            if count >= 4:
                return True
        return False

    def get_board_buttons(self, inline_id=None):
        buttons = []
        
            
        if not self.game_over:
            column_labels = []
            for col in range(7):
                data = f"{inline_id}_top_{col}" if inline_id else f"top_{col}"
                label = f"{col + 1}⬇️"
                if self.is_valid_move(col):
                    label = f"⬇️ {col + 1}"
                column_labels.append(Button.inline(label, data=data))
            buttons.append(column_labels)
        
        for row in range(6):
            row_buttons = []
            for col in range(7):
                cell = self.board[row][col]
                text = ' ' if cell == ' ' else cell
                if self.game_over:
                    with open('config.json') as f:
                        config = json.load(f)
                        bot_username = config['bot_username']
                    row_buttons.append(Button.url(text, url=f"https://t.me/{bot_username}"))
                else:
                    data = f"{inline_id}_{row}_{col}" if inline_id else f"{row}_{col}"
                    row_buttons.append(Button.inline(text, data=data))
            buttons.append(row_buttons)
        player1_info = f"{self.player1_username} (🔴)"
        player2_info = f"{self.player2_username} (🔵)"
        buttons.append([Button.inline(player1_info, data='player1_info'), Button.inline(player2_info, data='player2_info')])

        
        if self.game_over:
            duration = (self.ended_at - self.started_at).seconds
            stats = f"⏱️ مدت بازی: {duration} ثانیه | 🎯 تعداد حرکات: {self.moves}"
            buttons.append([Button.inline(stats, data='stats')])
            
            row_numbers = [Button.inline(f"{i+1} ⬇️", data=f"row_{i}") for i in range(7)]
            buttons.insert(0, row_numbers)
            
            play_again_data = f"play_again_{self.player1_id}_{self.player2_id}_{self.bet_amount}_{self.type_game}"
            buttons.append([Button.inline("🔄 بازی دوباره", data=play_again_data)])
        

            
        return buttons

    def is_valid_move(self, col):
        return 0 <= col < 7 and self.board[0][col] == ' ' and not self.game_over

    def save_to_db(self, game_id):
        db = Database()
        db.save_game(game_id, self)

    def set_message_ids(self, player1_msg_id, player2_msg_id):
        """Set message IDs for both players for live updates"""
        self.player1_message_id = player1_msg_id
        self.player2_message_id = player2_msg_id

    @staticmethod
    def load_from_db(game_id):
        db = Database()
        game_data = db.load_game(game_id)
        
        if game_data:
            game = FourInRow()
            game.board = json.loads(game_data[2])
            game.current_player = game_data[3]
            game.game_over = game_data[4]
            game.player1_id = game_data[5]
            game.player1_message_id = game_data[6] 
            game.player2_id = game_data[7]
            game.player2_message_id = game_data[8] 
            game.is_bet = game_data[9]
            game.type_game = game_data[10]
            game.bet_amount = game_data[11]
            game.winner_id = game_data[12]
            game.moves = game_data[13]
            game.started_at = datetime.fromisoformat(str(game_data[14]))
            game.ended_at = datetime.fromisoformat(str(game_data[15])) if game_data[15] else None
            
            player1_data = db.get_user(game.player1_id)
            player2_data = db.get_user(game.player2_id)
            game.player1_username = player1_data['username'] if player1_data else None
            game.player2_username = player2_data['username'] if player2_data else None
            
            if game.game_over:
                if game.winner_id:
                    winner_color = '🔴' if game.winner_id == game.player1_id else '🔵'
                    loser_username = game.player2_username if game.winner_id == game.player1_id else game.player1_username
                    if game.is_bet:
                        game.status = f"🎉 بازی تمام شد! {winner_color} برنده شد و {game.bet_amount} سکه برد! 🏆\nحریف: {loser_username}"
                    else:
                        game.status = f"🎉 بازی تمام شد! {winner_color} برنده شد! 🏆\nحریف: {loser_username}"
                else:
                    if game.is_bet:
                        game.status = f"🤝 بازی تمام شد! مساوی! {game.bet_amount} سکه برگشت داده شد!"
                    else:
                        game.status = "🤝 بازی تمام شد! مساوی!"
                

            else:
                opponent_username = game.player2_username if game.current_player == '🔴' else game.player1_username
                if game.is_bet:
                    game.status = f"💰 بازی رقابتی - نوبت: {game.current_player} ({opponent_username})"
                else:
                    game.status = f"نوبت: {game.current_player} ({opponent_username})"
                
            return game
        return None
