import time
import chess
from chess import uci

def lin_ex (n): # Run 1 move in n games sequentially
	for i in range(n):
		eng = uci.popen_engine("/usr/games/stockfish")
		eng.uci()
		eng.ucinewgame()
		board = chess.Board()
		eng.position(board)
		command = eng.go(movetime=1000, async_callback=True)  
		command.result()
		eng.quit()

def par_ex (n): # Run 1 move in n games across n separate processes at the same time
	engs = []
	commands = []
	for i in range(n):
		eng = uci.popen_engine("/usr/games/stockfish")
		eng.uci()
		eng.ucinewgame()
		engs.append(eng)
	for i in range(n):
		board = chess.Board()
		engs[i].position(board)
		commands.append(engs[i].go(movetime=1000, async_callback=True))
	for i in range(n):
		commands[i].result()
		engs[i].quit()

def time_run (func, *args): # Time how long the given function takes to run with the given arguments and print it
	start = time.time()
	func(*args)
	print "Executed in {t} seconds.".format(t=time.time() - start)


# Run with `python -i performance_test.py` to enter interactive mode then run whatever tests you want
