import math

class GlickoPlayer:
    def __init__(self, rating=1500, rd=350, vol=0.06):
        self.rating = rating
        self.rd = rd
        self.vol = vol
        self._tau = 0.5
        self._scale = 173.7178

    def _g(self, rd):
        return 1.0 / math.sqrt(1 + 3 * rd ** 2 / (math.pi ** 2))

    def _E(self, rating, opponent_rating, opponent_rd):
        # Adicionar proteção contra overflow
        exponent = -self._g(opponent_rd) * (rating - opponent_rating) / self._scale
        # Limitar o valor do expoente para evitar overflow
        exponent = max(min(exponent, 20), -20)
        return 1.0 / (1 + math.exp(exponent))

    def update_rating(self, opponent_rating, opponent_rd, score):
        """
        Atualiza o rating do jogador após uma partida.
        score: 1.0 para vitória, 0.0 para derrota, 0.5 para empate
        """
        g = self._g(opponent_rd)
        E = self._E(self.rating, opponent_rating, opponent_rd)
        
        # Adicionar proteção contra divisão por zero
        if E <= 0 or E >= 1:
            E = 0.5  # Valor neutro para evitar problemas
        
        v = 1.0 / (g ** 2 * E * (1 - E))
        
        # Atualizar rating
        delta = v * g * (score - E)
        
        # Atualizar desvio de rating com proteção contra valores muito pequenos
        new_rd_squared = 1 / (1 / (self.rd ** 2) + 1 / v)
        if new_rd_squared > 0:
            self.rd = min(350, math.sqrt(new_rd_squared))
        else:
            self.rd = 350  # Valor padrão em caso de erro
        
        # Atualizar rating
        self.rating = self.rating + delta
        
        # Atualizar volatilidade (simplificado)
        self.vol = math.sqrt((self.vol ** 2 + delta ** 2) / 2)

        return self.rating, self.rd, self.vol

class GlickoSystem:
    def __init__(self):
        self.players = {}

    def get_player(self, player_id):
        if player_id not in self.players:
            self.players[player_id] = GlickoPlayer()
        return self.players[player_id]

    def update_match(self, winner_id, loser_id):
        """Atualiza os ratings após uma partida"""
        winner = self.get_player(winner_id)
        loser = self.get_player(loser_id)

        # Atualizar ratings
        winner.update_rating(loser.rating, loser.rd, 1.0)
        loser.update_rating(winner.rating, winner.rd, 0.0)

    def get_rating(self, player_id):
        """Retorna o rating atual do jogador"""
        player = self.get_player(player_id)
        return player.rating, player.rd, player.vol 