from __future__ import print_function
from random import random
from math import sqrt
import chess
from neat import nn

_side = chess.WHITE
_piece_values = { # Using Hans Berliner's computed values
  'p': 1.0,
  'n': 3.2,
  'b': 3.33,
  'r': 5.1,
  'q': 8.8,
  'k': 0.0 # Doesn't need to be counted since obviously both sides still have it
}
_max_score = _piece_values['p'] * 8 + _piece_values['n'] * 2 + _piece_values['b'] * 2 \
  + _piece_values['r'] * 2 + _piece_values['q'] + _piece_values['k']


def simple_score (fen):
  board = fen.split(" ")[0]
  white = 0.0
  black = 0.0

  for char in board:
    if char.isupper():
      white += _piece_values.get(char.lower(), 0.0)
    if char.islower():
      black += _piece_values.get(char, 0.0)

  if _side == chess.WHITE:
    return [white, black]
  else:
    return [black, white]



def map_fen_to_input (fen):
  board = chess.Board(fen)
  chunks = fen.split(" ")
  grid = chunks[0]
  active_side = chunks[1]
  castles = chunks[2]
  en_passant = chunks[3]
  halfmove_clock = chunks[4]
  total_moves = chunks[5]
  rand = random()
  score = simple_score(fen)

  rows = grid.split("/")

  n_input = []

  # - 6 for each piece type * 2 sides
  # - 1 for a side holding that square * 2 sides
  # - 1 for a square being occupied or unoccupied
  # - 1 for how many enemies are attacking that square
  _square_depth = 6*2 + 1*2 + 1 + 1

  for row in rows:
    for square in row:
      activations = {
        'p': (0, 12),
        'n': (1, 12),
        'b': (2, 12),
        'r': (3, 12),
        'q': (4, 12),
        'k': (5, 12),
        'P': (6, 13),
        'N': (7, 13),
        'B': (8, 13),
        'R': (9, 13),
        'Q': (10, 13),
        'K': (11, 13)
      }
      indices = activations.get(square, False)

      if not indices:
        for k in range(int(square)):
          to_append = [0 for j in range(_square_depth)]
          to_append[14] = -1 # Signal this square is empty
          n_input.append(to_append)
      else:
        to_append = [0 for j in range(_square_depth)]
        to_append[indices[0]] = 1
        to_append[indices[1]] = 1
        to_append[14] = 1 # Signal this square is occupied
        n_input.append(to_append)

  ordered_squares = [r * 8 + f for r in range(7, -1, -1) for f in range(8)]
  for i in range(64):
    n_input[i][15] = len(board.attackers(not _side, ordered_squares[i]))

  flat_n_input = [n for square in n_input for n in square]
  flat_n_input.extend([ \
    "K" in castles, \
    "Q" in castles, \
    "k" in castles, \
    "q" in castles, \
    _max_score - score[0], \
    _max_score - score[1], \
    score[0] - score[1], \
    1.0 if board.is_check() else 0.0, \
    1.0 if board.can_claim_draw() else 0.0, \
    rand * rand, \
    halfmove_clock, \
    total_moves \
  ])

  return flat_n_input



def map_output_to_move (output, fen):
  board = chess.Board(fen)
  skip = output[128]
  can_skip = not board.is_check() and board.fullmove_number > 1
  draw = output[129]
  can_draw = board.can_claim_draw()
  castles = fen.split(" ")[2]
  king_castle = output[130]
  can_king_castle = board.has_kingside_castling_rights(_side) and ("K" if _side == chess.WHITE else "k") in castles
  queen_castle = output[131]
  can_queen_castle = board.has_queenside_castling_rights(_side) and ("Q" if _side == chess.WHITE else "q") in castles
  
  moves = sorted([(output[move.from_square] * output[move.to_square + 64], move) for move in board.legal_moves], reverse=True)
  
  possible_moves = []

  if len(moves) > 0:
    possible_moves.append(moves[0])
  if can_skip:
    possible_moves.append((skip, "skip"))
  if can_draw:
    possible_moves.append((draw, "draw"))
  #if can_king_castle:
    #possible_moves.append((king_castle, "kc"))
  #if can_queen_castle:
    #possible_moves.append((queen_castle, "qc"))

  if len(possible_moves) > 0:
    best_move = sorted(possible_moves, reverse=True)[0][1]
    if not type(best_move) is str:
      return best_move
    if best_move == "skip":
      return chess.Move.null()
    if best_move == "draw":
      return "draw"
    if best_move == "kc": # Castles will actually probably show up as regularly selected moves too, but I'm not sure how they're encoded so I'm using SAN here
      return "0-0"
    if best_move == "qc":
      return "0-0-0"

  return 0 # If in check(mate) with no possible moves and no ability to draw, the game is over

class ChessNet:
  def __init__ (self, genome):
    self._net = nn.create_feed_forward_phenotype(genome)

  def get_move (self, fen):
    return map_output_to_move(self._net.serial_activate(map_fen_to_input(fen)), fen)