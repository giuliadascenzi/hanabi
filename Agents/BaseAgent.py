from game import Player




class BaseAgent(Player):
    """
    Subclass this class once for each AI.
    """
    def __init__(self, name):
        super().__init__(name)
    
    def initialize(self, num_players, players, k, board, hands, discard_pile):
        """
        To be called once before the beginning.
        """
        self.num_players = num_players
        self.k = k  # number of cards per hand
        self.usedNoteTokens = 0
        self.usedStormTokens= 0
        self.players= players

        self.board = board
        self.hands = hands
        self.discard_pile = discard_pile



    
    
    def update(self, board, hands, discardPile, usedNoteTokens, usedStormTokens, turn= 0, last_turn=0 ):
        """
        To be called immediately after every turn.
        """
        self.usedNoteTokens = usedNoteTokens
        self.usedStormTokens = usedStormTokens
        self.turn = turn
        self.last_turn = last_turn

        self.hands = hands
        self.discard_pile = discardPile
        self.board= board
    
    
   
    
    def get_turn_action(self):
        """
        Choose action for this turn.
        """
        raise NotImplementedError



    
