# autogame

Bismuth autogame.

A semi-deterministic game on top of Bismuth Blockchain.  
http://bismuth.cz

## About the game

More info about the game itself, the protocol and how to play https://github.com/hclivess/autogame/blob/master/about.md

## Current leagues

https://github.com/hclivess/autogame/blob/master/leagues.md

# For devs

## Requirements

* Python3.6+
* sqlite3
* Tornado

## Code and files structure

* config.json holds the local config: path to the Bismuth ledger and Bismuth core code.
* classes.py and core.py are python modules
* run.py runs a round of the game, approx every minute, and feeds the db
* web.py is the tournament server front end
* .html files are Tornado templates used by the tournament server front end

## Tutorial

WIP: upcoming tutorial on https://github.com/bismuthfoundation/Hack-with-BIS/tree/master/15-Autogame
