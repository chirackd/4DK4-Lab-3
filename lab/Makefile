CC = gcc
CFLAGS = -O2 -std=gnu17 -Wall -Wextra -Wpedantic
LDLIBS = -lm

all: simulator
simulator: simulator.c ../simlib.c ../simlib.h ../trace.h
	$(CC) $(CFLAGS) -I.. simulator.c ../simlib.c $(LDLIBS) -o $@
clean:
	rm -f simulator simulator-sanitize
.PHONY: all clean
