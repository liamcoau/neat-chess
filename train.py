import os
import logging
logging.basicConfig()

import chess
from chess import uci
from neat import population, statistics

import net

_processes = 1
_side = net._side

engines = []



for i in range(_processes):
  engines.append(uci.popen_engine("/usr/games/stockfish"))
  engines[i].uci()



def apply_move (move, game):
  print move
  if move == "draw":
    if game.board.can_claim_draw():
      game.set_result(game.board.result(claim_draw=True))
    else:
      game.set_result("Loss")
    return False
  elif move == "0-0" or move == "0-0-0":
    game.board.push_san(move)
    if game.board.is_game_over():
      game.set_result(game.board.result())
      return False
  else:
    game.board.push(move)
    if game.board.is_game_over():
      game.set_result(game.board.result())
      return False
  return True



class Game:
  def __init__ (self, genome):
    self.board   = chess.Board()
    self.net     = net.ChessNet(genome)
    self.genome  = genome
    self.command = False
    self.result  = False

  def set_command (self, command):
    self.command = command

  def get_command (self):
    return self.command.result()

  def set_result (self, result):
    assert result in ["Win", "Loss", "Draw", "1/2-1/2", "1-0", "0-1"], "Invalid game result"
    if result == "1/2-1/2":
      result = "Draw"
    if result == "1-0":
      if _side == chess.WHITE:
        result = "Win"
      else:
        result = "Loss"
    if result == "0-1":
      if _side == chess.WHITE:
        result = "Loss"
      else:
        result = "Win"
    self.result = result



def calc_score (game):
  result = game.result
  piece_score = (lambda r: r[0] - r[1])(net.simple_score(game.board.fen())) # Positive if the net has a piece advantage
  turns = game.board.fullmove_number

  if result == "Draw":
    return -piece_score # Penalize drawing when ahead in pieces

  if result == "Win":
    return 150 + piece_score - turns # Encourage being ahead in pieces, and winning quicker

  if result == "Loss":
    return -150 + turns # Encourage lasting longer before losing



def eval_fitness (genomes):
  available_genomes = range(len(genomes))
  games = [False for x in range(_processes)]

  while True:
    for i in range(_processes):
      if not games[i] and len(available_genomes) > 0: # Start new game if there are any genomes left to be tested
        genome = genomes[available_genomes.pop()]
        game = Game(genome)
        engines[i].ucinewgame()

        if _side == chess.WHITE:
          try:
            if apply_move(game.net.get_move(game.board.fen()), game):
              engines[i].position(game.board)
              game.set_command(engines[i].go(movetime=500, async_callback=True))
          except ValueError as e:
            print "Invalid move was attempted! " + e.message
            game.set_result("Loss")
        else:
          engines[i].position(game.board)
          game.set_command(engines[i].go(movetime=500, async_callback=True))
        
        games[i] = game
      
      elif games[i] and games[i].result: # End game and score the genome
        games[i].genome.fitness = calc_score(games[i])

        print "Finished game on turn {0} - {1} ({2})".format(games[i].board.fullmove_number, games[i].result, games[i].genome.fitness)

        games[i] = False
        engines[i].quit()  
        engines[i] = uci.popen_engine("/usr/games/stockfish")
        engines[i].uci()
        
        if games == [False for x in range(len(games))] and len(available_genomes) == 0:
          return # Finished generation
      
      else: # Play the next turn
        game = games[i]
        if game:
          engine = engines[i]
          move = game.get_command().bestmove
        
          try:
            if not move:
              apply_move(chess.Move.null(), game)
            else:
              apply_move(move, game)

            if not game.result:
              print game.board.fen()
              if apply_move(game.net.get_move(game.board.fen()), game):
                #engine.quit()  
                #engines[i] = uci.popen_engine("/usr/games/stockfish")
                #engines[i].uci()
                #engines[i].ucinewgame()
                engines[i].position(game.board)
                print game.board.fen()
                game.set_command(engines[i].go(movetime=500, async_callback=True))
          except ValueError as e:
            print "Invalid move was attempted! " + e.message
            game.set_result("Loss")



if __name__ == "__main__":
  local_dir = os.path.dirname(__file__)
  config_path = os.path.join(local_dir, "chess_config")

  pop = population.Population(config_path)
  pop.run(eval_fitness, 3)
  for engine in engines:
    engine.quit()

  statistics.save_stats(pop.statistics)
  statistics.save_species_count(pop.statistics)
  statistics.save_species_fitness(pop.statistics)

  winner = pop.statistics.best_genome()

  #print winner